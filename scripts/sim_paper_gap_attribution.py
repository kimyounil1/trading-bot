"""Attribute the backtest-sim vs paper-account performance gap.

Over the overlapping observation window (paper equity curve x execution audit),
quantifies where the sim's OOS edge leaks in live paper trading:

  1. Window returns: paper account vs top-bucket sim vs SPY vs equal-weight universe
  2. Exposure: sim runs ~fully invested; paper holds large cash
  3. Guard opportunity cost: forward return (to window end) of buy candidates each
     guard blocked, vs the names actually bought
  4. BUY_ERROR leak: forward return of buys lost to pipeline crashes

Reads logs/execution_audit.csv + logs/portfolio_pnl/equity_curve.csv + price caches.
Retrains the production-config rank model to reproduce the sim (research replica).
Outputs logs/sim_paper_gap/attribution_summary.json, appends to history.jsonl, and
evaluates a PRE-REGISTERED decision rule in trend_summary.json:

  budget_leak_flag (per run): blocked-by-budget buys (cash_exhausted + sleeve_budget)
  have n>=20 and mean forward return >= 50% of the mean forward return of executed
  buys (which must be positive, n>=5). If 8 CONSECUTIVE weekly runs flag, the trend
  recommendation switches to "start a core-sleeve budget +15% A/B". Rule fixed
  2026-07-06 to avoid post-hoc rationalization; don't tweak it mid-collection.

Usage:
  .venv/bin/python -m scripts.sim_paper_gap_attribution
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from src.data_loader import load_price_data_batch
from src.features import build_features
from src.macro_loader import load_macro_data
from src.rank_label_experiment import (
    RankExperimentConfig,
    _score_oos,
    _simulate_top_bucket_portfolio,
    _train_rank_models,
)
from src.retrain_holdout import portfolio_holdout_window
from src.settings import load_settings

OUTPUT_DIR = Path("logs/sim_paper_gap")
AUDIT_PATH = Path("logs/execution_audit.csv")
EQUITY_PATH = Path("logs/portfolio_pnl/equity_curve.csv")

GUARD_BUCKETS = [
    "crowding_guard",
    "sector_guard",
    "max_positions",
    "sleeve_budget",
    "daily_order_limit",
    "cash_exhausted",
    "correlation_guard",
    "llm_block",
]


def _bucket(reason: str) -> str:
    r = str(reason).lower()
    if "crowding" in r:
        return "crowding_guard"
    if "sector concentration" in r:
        return "sector_guard"
    if "max total positions" in r:
        return "max_positions"
    if "sleeve" in r and ("budget" in r or "open orders" in r):
        return "sleeve_budget"
    if "daily order amount" in r:
        return "daily_order_limit"
    if "cash is zero" in r:
        return "cash_exhausted"
    if "correlation" in r:
        return "correlation_guard"
    if "llm" in r:
        return "llm_block"
    if "rank" in r:
        return "rank_gate"
    return "other"


def _close_series(loaded: dict, ticker: str) -> pd.Series | None:
    df = loaded.get(ticker)
    if df is None or df.empty:
        return None
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"])
    return out.set_index("date")["close"]


def _fwd_to_end(series: pd.Series | None, start: pd.Timestamp, end: pd.Timestamp) -> float:
    if series is None:
        return np.nan
    after = series[series.index >= start]
    upto = series[series.index <= end]
    if after.empty or upto.empty or after.iloc[0] <= 0:
        return np.nan
    return float(upto.iloc[-1] / after.iloc[0] - 1.0)


def _window_return(series: pd.Series, start: pd.Timestamp, end: pd.Timestamp) -> float:
    series = series.dropna()
    w = series[(series.index >= start) & (series.index <= end)]
    if len(w) < 2:
        return np.nan
    return float(w.iloc[-1] / w.iloc[0] - 1.0)


def _build_dataset(
    ticker_data: dict[str, pd.DataFrame],
    *,
    prediction_horizon: int,
    vix_df: pd.DataFrame | None,
    spy_df: pd.DataFrame | None,
    macro_df: pd.DataFrame | None,
) -> pd.DataFrame:
    """rank_label_experiment._build_rank_dataset replica. build_features drops rows
    without a forward label, so the last `prediction_horizon` days vanish; passing
    prediction_horizon=1 keeps all but the final day scoreable (features don't depend
    on the horizon) — used for the trading replica, while training uses the real one."""
    frames: list[pd.DataFrame] = []
    for ticker, df in ticker_data.items():
        try:
            features = build_features(
                df,
                prediction_horizon=prediction_horizon,
                target_return_threshold=0.0,
                vix_df=vix_df,
                spy_df=spy_df,
                macro_df=macro_df,
            )
        except ValueError:
            continue
        features = features.copy()
        features["ticker"] = ticker
        frames.append(features)
    if not frames:
        raise ValueError("No feature frames available")
    dataset = pd.concat(frames, ignore_index=True)
    dataset["date"] = pd.to_datetime(dataset["date"], errors="coerce")
    dataset = dataset.dropna(subset=["date"]).copy()
    dataset["future_return_percentile"] = dataset.groupby("date")["future_return"].rank(
        pct=True,
        method="average",
    )
    return dataset.sort_values(["date", "ticker"]).reset_index(drop=True)


BUDGET_LEAK_MIN_BLOCKED = 20
BUDGET_LEAK_MIN_BUYS = 5
BUDGET_LEAK_RATIO = 0.5
BUDGET_LEAK_CONSECUTIVE_RUNS = 8


def _budget_leak_flag(report: dict) -> bool | None:
    """Pre-registered rule (2026-07-06); returns None when sample too small."""
    buys = report.get("buys_submitted", {})
    guards = report.get("guard_blocked_fwd_returns", {})
    blocked_n = 0
    blocked_weighted = 0.0
    for key in ("cash_exhausted", "sleeve_budget"):
        g = guards.get(key) or {}
        n = int(g.get("n") or 0)
        mean = g.get("mean_fwd_to_end")
        if n and mean is not None:
            blocked_n += n
            blocked_weighted += n * float(mean)
    buys_n = int(buys.get("n") or 0)
    buys_mean = buys.get("mean_fwd_to_end")
    if blocked_n < BUDGET_LEAK_MIN_BLOCKED or buys_n < BUDGET_LEAK_MIN_BUYS or buys_mean is None:
        return None
    if float(buys_mean) <= 0:
        return False
    return (blocked_weighted / blocked_n) >= BUDGET_LEAK_RATIO * float(buys_mean)


def _update_history_and_trend(report: dict) -> dict:
    history_path = OUTPUT_DIR / "history.jsonl"
    record = {
        "generated_at": report["generated_at"],
        "window": report["window"],
        "window_returns": report["window_returns"],
        "buys_submitted": report["buys_submitted"],
        "guard_blocked_fwd_returns": report["guard_blocked_fwd_returns"],
        "budget_leak_flag": _budget_leak_flag(report),
    }
    with history_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")

    records = [
        json.loads(line)
        for line in history_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    consecutive = 0
    for rec in reversed(records):
        if rec.get("budget_leak_flag") is True:
            consecutive += 1
        else:
            break
    triggered = consecutive >= BUDGET_LEAK_CONSECUTIVE_RUNS
    trend = {
        "generated_at": report["generated_at"],
        "runs": len(records),
        "budget_leak_consecutive_flags": consecutive,
        "budget_leak_rule": (
            f"blocked(cash_exhausted+sleeve_budget, n>={BUDGET_LEAK_MIN_BLOCKED}) mean fwd >= "
            f"{BUDGET_LEAK_RATIO} x buys mean fwd (buys n>={BUDGET_LEAK_MIN_BUYS}, mean>0); "
            f"act after {BUDGET_LEAK_CONSECUTIVE_RUNS} consecutive weekly flags"
        ),
        "action_triggered": triggered,
        "recommendation": (
            "Budget-leak rule satisfied for 8 consecutive runs: start a core-sleeve "
            "budget +15% paper A/B (controlled, report-only first)"
            if triggered
            else "Keep collecting weekly evidence; no config change yet"
        ),
        "recent_flags": [
            {"generated_at": r["generated_at"], "budget_leak_flag": r.get("budget_leak_flag")}
            for r in records[-10:]
        ],
    }
    (OUTPUT_DIR / "trend_summary.json").write_text(
        json.dumps(trend, indent=2), encoding="utf-8"
    )
    return trend


def main() -> None:
    settings = load_settings()
    cfg = RankExperimentConfig(
        prediction_horizon=20,
        top_bucket_pct=0.15,
        min_score_quantile=0.85,
        period="5y",
    )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    equity = pd.read_csv(EQUITY_PATH)
    equity["date"] = pd.to_datetime(equity["date"])
    win_start = equity["date"].min()
    win_end = equity["date"].max() - pd.Timedelta(days=1)  # drop possibly-partial last day
    paper_eq = equity.set_index("date")["equity"]
    paper_return = _window_return(paper_eq, win_start, win_end)
    print(f"Window {win_start.date()} .. {win_end.date()}  paper return {paper_return:+.2%}\n")

    tickers = list(dict.fromkeys([str(t).strip().upper() for t in settings.tickers] + ["^VIX", "SPY"]))
    loaded = load_price_data_batch(tickers, period=cfg.period)
    ticker_data = {t: loaded[t] for t in settings.tickers if t in loaded}
    spy = _close_series(loaded, "SPY")
    spy_return = _window_return(spy, win_start, win_end)

    # equal-weight universe benchmark over the window
    ew_returns = [
        r for t in ticker_data if not np.isnan(r := _window_return(_close_series(loaded, t), win_start, win_end))
    ]
    ew_return = float(np.mean(ew_returns))

    # --- sim replica (production config), sliced to the window ---
    try:
        macro_df = load_macro_data()
    except Exception:
        macro_df = None
    labeled = _build_dataset(
        ticker_data,
        prediction_horizon=cfg.prediction_horizon,
        vix_df=loaded.get("^VIX"),
        spy_df=loaded.get("SPY"),
        macro_df=macro_df,
    )
    scoreable = _build_dataset(
        ticker_data,
        prediction_horizon=1,
        vix_df=loaded.get("^VIX"),
        spy_df=loaded.get("SPY"),
        macro_df=macro_df,
    )
    holdout_start, holdout_end = portfolio_holdout_window(ticker_data)
    train_df = labeled[labeled["date"] < holdout_start].copy()
    test_df = scoreable[
        (scoreable["date"] >= holdout_start) & (scoreable["date"] <= holdout_end)
    ].copy()
    print("Training sim replica...")
    clf, reg = _train_rank_models(train_df, cfg.top_bucket_pct)
    scored = _score_oos(test_df, classifier=clf, regressor=reg, top_bucket_pct=cfg.top_bucket_pct)
    _, sim_equity_df, _ = _simulate_top_bucket_portfolio(scored, ticker_data, cfg)
    sim_equity_df["date"] = pd.to_datetime(sim_equity_df["date"])
    sim_equity_df.to_csv(OUTPUT_DIR / "sim_equity_curve.csv", index=False)
    sim_eq = sim_equity_df.set_index("date")["equity"]
    # keep windows identical: sim (horizon=1 labeling) may end a day earlier than paper
    win_end = min(win_end, sim_eq.dropna().index.max())
    paper_return = _window_return(paper_eq, win_start, win_end)
    spy_return = _window_return(spy, win_start, win_end)
    sim_return = _window_return(sim_eq, win_start, win_end)
    sim_w = sim_equity_df[(sim_equity_df["date"] >= win_start) & (sim_equity_df["date"] <= win_end)]
    sim_exposure = float((sim_w["positions_value"] / sim_w["equity"]).mean())

    # --- audit-based guard opportunity cost ---
    audit = pd.read_csv(AUDIT_PATH)
    audit["date"] = pd.to_datetime(audit["timestamp"]).dt.normalize()
    audit = audit[(audit["date"] >= win_start) & (audit["date"] <= win_end)]

    def fwd_stats(frame: pd.DataFrame) -> dict:
        frame = frame.drop_duplicates(["date", "ticker"]).copy()
        frame["fwd"] = [
            _fwd_to_end(_close_series(loaded, t), d, win_end)
            for t, d in zip(frame["ticker"], frame["date"])
        ]
        valid = frame["fwd"].dropna()
        if valid.empty:
            return {"n": 0}
        return {
            "n": int(len(valid)),
            "mean_fwd_to_end": round(float(valid.mean()), 4),
            "median_fwd_to_end": round(float(valid.median()), 4),
        }

    buys = fwd_stats(audit[audit["event_type"] == "BUY_SUBMITTED"])
    buy_errors = fwd_stats(audit[audit["event_type"] == "BUY_ERROR"])

    skips = audit[audit["event_type"] == "SKIP_BUY"].copy()
    skips["bucket"] = skips["reason"].map(_bucket)
    guards = {
        b: fwd_stats(skips[skips["bucket"] == b])
        for b in GUARD_BUCKETS
        if not skips[skips["bucket"] == b].empty
    }

    error_reasons = (
        audit[audit["event_type"] == "BUY_ERROR"]["reason"].str[:60].value_counts().head(8).to_dict()
    )

    report = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window": {"start": str(win_start.date()), "end": str(win_end.date())},
        "window_returns": {
            "paper_account": round(paper_return, 4),
            "sim_top_bucket": round(sim_return, 4),
            "spy": round(spy_return, 4),
            "equal_weight_universe": round(ew_return, 4),
        },
        "exposure": {
            "sim_avg_invested_frac": round(sim_exposure, 4),
            "note": "paper invested fraction: see logs/portfolio_pnl/latest_summary.json (invested_value/total_equity)",
        },
        "buys_submitted": buys,
        "buy_errors": {**buy_errors, "reasons_full_audit": error_reasons},
        "guard_blocked_fwd_returns": guards,
        "methodology": (
            "fwd_to_end = close(window end)/close(first close on/after event date) - 1; "
            "horizons vary by event date, so compare buckets against buys_submitted and spy, "
            "not against each other in absolute terms"
        ),
    }
    out = OUTPUT_DIR / "attribution_summary.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    trend = _update_history_and_trend(report)

    print(f"paper {paper_return:+.2%} | sim {sim_return:+.2%} (exposure {sim_exposure:.0%}) | "
          f"SPY {spy_return:+.2%} | EW-universe {ew_return:+.2%}")
    print(f"buys n={buys.get('n')} mean {buys.get('mean_fwd_to_end', float('nan')):+.2%} | "
          f"buy_errors n={buy_errors.get('n')} mean {buy_errors.get('mean_fwd_to_end', float('nan')):+.2%}")
    for b, s in sorted(guards.items(), key=lambda kv: -kv[1].get("n", 0)):
        print(f"  {b:<18} n={s['n']:>5} mean {s.get('mean_fwd_to_end', float('nan')):+.2%}")
    print(
        f"Trend: runs={trend['runs']} budget_leak_consecutive={trend['budget_leak_consecutive_flags']} "
        f"-> {trend['recommendation']}"
    )
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
