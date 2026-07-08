"""Offline sweep: does a fixed cash floor (e.g. the 20% cash sleeve) cost returns?

Replicates the production rank-gate sim (h20, top15%, q85) and re-runs the same
scored OOS window under different cash floors — buys are skipped whenever they
would push invested value above (1 - floor) x equity. floor=0.0 is the
unconstrained sim; floor=0.20 mirrors the paper cash-sleeve target.

Runs BOTH a 6-month and a 12-month holdout (lesson from the regime-gate card:
single-window verdicts flip). Report-only; paper config untouched. Caveat: the
sim has no guards/LLM veto, so it deploys far more than paper does — this
measures the *ceiling* cost of the floor, not the live cost.

Usage:
  .venv/bin/python -m scripts.cash_floor_sweep
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.data_loader import load_price_data_batch
from src.macro_loader import load_macro_data
from src.rank_label_experiment import (
    RankExperimentConfig,
    _build_rank_dataset,
    _exit_reason,
    _score_oos,
    _train_rank_models,
)
from src.retrain_holdout import portfolio_holdout_window
from src.settings import load_settings

OUTPUT_DIR = Path("logs/cash_floor_sweep")
CASH_FLOORS = [0.0, 0.10, 0.20, 0.30]
HOLDOUT_MONTHS = [6, 12]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _simulate_with_cash_floor(
    scored_df: pd.DataFrame,
    cfg: RankExperimentConfig,
    *,
    cash_floor: float,
) -> dict[str, Any]:
    """rank_label_experiment._simulate_top_bucket_portfolio with an invested cap.

    Buys are clipped so cash never drops below cash_floor x equity."""
    cash = cfg.initial_cash
    positions: dict[str, dict[str, Any]] = {}
    trades: list[dict[str, Any]] = []
    equity_rows: list[dict[str, Any]] = []

    dates = sorted(scored_df["date"].dropna().unique())
    for current_date in dates:
        day_df = scored_df[scored_df["date"] == current_date]
        prices = {row["ticker"]: float(row["close"]) for _, row in day_df.iterrows()}

        for ticker in list(positions.keys()):
            if ticker not in prices:
                continue
            pos = positions[ticker]
            price = prices[ticker]
            reason = _exit_reason(pos, price, cfg)
            if reason is None:
                pos["last_price"] = price
                continue
            cash += pos["qty"] * price * (1.0 - cfg.transaction_cost_pct)
            trades.append({"return_pct": price / pos["entry_price"] - 1.0})
            del positions[ticker]

        positions_value = sum(
            pos["qty"] * prices.get(ticker, pos["last_price"])
            for ticker, pos in positions.items()
        )
        equity = cash + positions_value

        allowed = day_df[
            (day_df["predicted_score_percentile"] >= cfg.min_score_quantile)
            & (~day_df["ticker"].isin(positions.keys()))
        ].sort_values("rank_score", ascending=False)
        slots_left = max(cfg.max_positions - len(positions), 0)

        for _, row in allowed.head(slots_left).iterrows():
            price = float(row["close"])
            if price <= 0 or cash <= 0:
                continue
            reserve = cash_floor * equity
            deployable = max(0.0, cash - reserve)
            available = min(deployable, equity * cfg.target_position_pct)
            if available < 10.0:
                continue
            qty = available * (1.0 - cfg.transaction_cost_pct) / price
            cash -= available
            positions[str(row["ticker"])] = {
                "qty": qty,
                "entry_price": price,
                "entry_date": current_date,
                "last_price": price,
                "highest_price": price,
            }

        for ticker, pos in positions.items():
            if ticker in prices:
                pos["last_price"] = prices[ticker]
        positions_value = sum(pos["qty"] * pos["last_price"] for pos in positions.values())
        equity_rows.append(
            {"equity": cash + positions_value, "invested": positions_value}
        )

    eq = pd.DataFrame(equity_rows)
    eq["daily_return"] = eq["equity"].pct_change().fillna(0.0)
    eq["drawdown"] = eq["equity"] / eq["equity"].cummax() - 1.0
    daily_std = float(eq["daily_return"].std())
    trades_df = pd.DataFrame(trades)
    return {
        "cash_floor": cash_floor,
        "total_return": round(float(eq["equity"].iloc[-1] / cfg.initial_cash - 1.0), 4),
        "sharpe_ratio": round(
            float(eq["daily_return"].mean() / daily_std * (252**0.5)) if daily_std > 1e-10 else 0.0,
            4,
        ),
        "max_drawdown": round(float(eq["drawdown"].min()), 4),
        "avg_invested_frac": round(float((eq["invested"] / eq["equity"]).mean()), 4),
        "trades": int(len(trades_df)),
        "win_rate": round(float((trades_df["return_pct"] > 0).mean()), 4) if len(trades_df) else None,
    }


def main() -> None:
    settings = load_settings()
    cfg = RankExperimentConfig(
        prediction_horizon=20,
        top_bucket_pct=0.15,
        min_score_quantile=0.85,
        period="5y",
    )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    tickers = list(dict.fromkeys([str(t).strip().upper() for t in settings.tickers] + ["^VIX", "SPY"]))
    print(f"Loading {len(tickers)} tickers ({cfg.period})...")
    loaded = load_price_data_batch(tickers, period=cfg.period)
    ticker_data = {t: loaded[t] for t in settings.tickers if t in loaded}
    try:
        macro_df = load_macro_data()
    except Exception:
        macro_df = None

    dataset = _build_rank_dataset(
        ticker_data,
        prediction_horizon=cfg.prediction_horizon,
        vix_df=loaded.get("^VIX"),
        spy_df=loaded.get("SPY"),
        macro_df=macro_df,
    )

    windows: dict[str, Any] = {}
    for months in HOLDOUT_MONTHS:
        holdout_start, holdout_end = portfolio_holdout_window(ticker_data, months=months)
        train_df = dataset[dataset["date"] < holdout_start].copy()
        test_df = dataset[
            (dataset["date"] >= holdout_start) & (dataset["date"] <= holdout_end)
        ].copy()
        print(f"\n[{months}m holdout {holdout_start.date()}..{holdout_end.date()}] "
              f"train={len(train_df):,} test={len(test_df):,}")
        clf, reg = _train_rank_models(train_df, cfg.top_bucket_pct)
        scored = _score_oos(test_df, classifier=clf, regressor=reg, top_bucket_pct=cfg.top_bucket_pct)

        results = [
            _simulate_with_cash_floor(scored, cfg, cash_floor=floor)
            for floor in CASH_FLOORS
        ]
        windows[f"{months}m"] = {
            "holdout": {"start": str(holdout_start.date()), "end": str(holdout_end.date())},
            "results": results,
        }
        print(f"{'floor':>6} {'return':>8} {'sharpe':>7} {'mdd':>8} {'invested':>9} {'trades':>7}")
        for r in results:
            print(
                f"{r['cash_floor']:>6.0%} {r['total_return']:>8.2%} {r['sharpe_ratio']:>7.2f} "
                f"{r['max_drawdown']:>8.2%} {r['avg_invested_frac']:>9.1%} {r['trades']:>7}"
            )

    report = {
        "generated_at": _utc_now(),
        "config": asdict(cfg),
        "cash_floors": CASH_FLOORS,
        "windows": windows,
        "caveat": (
            "Frictionless sim (no guards/LLM veto) deploys ~100%; paper holds far more cash "
            "for gate reasons. This bounds the CEILING cost of a fixed cash floor."
        ),
    }
    out = OUTPUT_DIR / "latest_summary.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()
