"""Offline universe-size A/B for the rank model: paper 110 vs master 259 tickers.

Answers "does a wider scan universe improve returns?" without touching paper config.
Three arms, all matching the production rank gate config (h20, top15%, q85):

  paper_110          : train + trade on the current paper universe (production replica)
  master_259         : train + trade on the full master universe (config/universe_master.csv)
  master_train_paper : train on master 259, trade only the paper 110 subset
                       (isolates training-breadth effect from tradable-breadth effect)

Outputs comparison report to logs/ml/rank_universe_ab/.

Usage:
  .venv/bin/python -m scripts.rank_universe_ab
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, mean_squared_error, roc_auc_score

from src.data_loader import load_price_data_batch
from src.macro_loader import load_macro_data
from src.rank_label_experiment import (
    RankExperimentConfig,
    _build_rank_dataset,
    _score_oos,
    _simulate_top_bucket_portfolio,
    _train_rank_models,
)
from src.retrain_holdout import portfolio_holdout_window
from src.settings import load_settings
from src.universe_loader import load_master_tickers

OUTPUT_DIR = Path("logs/ml/rank_universe_ab")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _mean_cs_ic(scored: pd.DataFrame) -> tuple[float, int]:
    ics = []
    for _, g in scored.groupby("date"):
        sub = g[["rank_score", "future_return_percentile"]].dropna()
        if len(sub) < 20:
            continue
        ic = sub["rank_score"].corr(sub["future_return_percentile"], method="spearman")
        if pd.notna(ic):
            ics.append(ic)
    if not ics:
        return 0.0, 0
    return float(np.mean(ics)), len(ics)


def _rerank_percentiles(scored: pd.DataFrame) -> pd.DataFrame:
    """Recompute cross-sectional percentiles after restricting the universe."""
    out = scored.copy()
    out["predicted_score_percentile"] = out.groupby("date")["rank_score"].rank(
        pct=True,
        method="average",
    )
    out["future_return_percentile"] = out.groupby("date")["future_return"].rank(
        pct=True,
        method="average",
    )
    return out


def _evaluate(
    scored: pd.DataFrame,
    ticker_data: dict[str, pd.DataFrame],
    cfg: RankExperimentConfig,
    *,
    label: str,
) -> dict:
    cutoff = 1.0 - cfg.top_bucket_pct
    scored = scored.copy()
    scored["top_bucket_label"] = (scored["future_return_percentile"] >= cutoff).astype(int)
    try:
        auc = float(roc_auc_score(scored["top_bucket_label"], scored["rank_clf_score"]))
    except ValueError:
        auc = None
    brier = float(brier_score_loss(scored["top_bucket_label"], scored["rank_clf_score"]))
    rmse = float(
        mean_squared_error(scored["future_return_percentile"], scored["rank_reg_score"]) ** 0.5
    )
    mean_ic, ic_days = _mean_cs_ic(scored)
    portfolio, _, _ = _simulate_top_bucket_portfolio(scored, ticker_data, cfg)
    return {
        "label": label,
        "universe_size": int(scored["ticker"].nunique()),
        "top_bucket_auc": round(auc, 4) if auc is not None else None,
        "brier": round(brier, 4),
        "rank_percentile_rmse": round(rmse, 4),
        "mean_cs_ic": round(mean_ic, 4),
        "ic_days": ic_days,
        "test_rows": int(len(scored)),
        "portfolio_oos": {
            k: round(v, 4) if isinstance(v, float) else v for k, v in portfolio.items()
        },
    }


def _filter_by_coverage(
    ticker_data: dict[str, pd.DataFrame],
    holdout_start: pd.Timestamp,
    holdout_end: pd.Timestamp,
    *,
    min_rows: int = 250,
) -> dict[str, pd.DataFrame]:
    """Drop tickers that cannot span the holdout window (delisted/renamed/short history).

    The equal-weight benchmark needs every ticker priced across the whole window, so we
    require actual positive closes there — delisted tickers cache all-NaN rows."""
    out: dict[str, pd.DataFrame] = {}
    window_days = int(np.busday_count(holdout_start.date(), holdout_end.date()))
    min_valid = int(window_days * 0.9)
    for ticker, df in ticker_data.items():
        if df is None or df.empty or "date" not in df.columns or len(df) < min_rows:
            continue
        d = df.copy()
        d["date"] = pd.to_datetime(d["date"], errors="coerce")
        d = d.dropna(subset=["date"])
        if d.empty or d["date"].min() > holdout_start:
            continue
        price_col = "adj_close" if "adj_close" in d.columns else "close"
        window = d[(d["date"] >= holdout_start) & (d["date"] <= holdout_end)]
        valid_closes = int((pd.to_numeric(window[price_col], errors="coerce") > 0).sum())
        if valid_closes >= min_valid:
            out[ticker] = df
    return out


def _spy_reference_return(
    spy_df: pd.DataFrame | None,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> float | None:
    if spy_df is None or spy_df.empty or "date" not in spy_df.columns:
        return None
    df = spy_df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    window = df[(df["date"] >= start) & (df["date"] <= end)].sort_values("date")
    if len(window) < 2:
        return None
    return float(window["close"].iloc[-1] / window["close"].iloc[0] - 1.0)


def _verdict(paper: dict, master: dict, master_paper: dict) -> dict:
    p = paper["portfolio_oos"]
    m = master["portfolio_oos"]
    mp = master_paper["portfolio_oos"]
    return_delta = m["total_return"] - p["total_return"]
    sharpe_delta = m["sharpe_ratio"] - p["sharpe_ratio"]
    mdd_delta = m["max_drawdown"] - p["max_drawdown"]  # positive = shallower drawdown
    train_breadth_return_delta = mp["total_return"] - p["total_return"]
    expand_pass = return_delta >= 0.02 and sharpe_delta >= -0.2 and mdd_delta >= -0.05
    if expand_pass:
        recommendation = (
            "Master universe beats paper on OOS return without degrading risk; "
            "consider a paper A/B with the expanded universe (retrain required)"
        )
    elif train_breadth_return_delta >= 0.02:
        recommendation = (
            "Wider training universe helps even when trading the paper 110 only; "
            "consider retraining the rank model on master 259 while keeping the paper scan list"
        )
    else:
        recommendation = "Keep the paper 110 universe; expansion does not clear the gate"
    return {
        "return_delta_master_vs_paper": round(return_delta, 4),
        "sharpe_delta_master_vs_paper": round(sharpe_delta, 4),
        "mdd_delta_master_vs_paper": round(mdd_delta, 4),
        "return_delta_master_train_paper_trade": round(train_breadth_return_delta, 4),
        "expansion_passed": expand_pass,
        "recommendation": recommendation,
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

    paper_tickers = [str(t).strip().upper() for t in settings.tickers]
    master_tickers = load_master_tickers()
    all_tickers = list(dict.fromkeys([*master_tickers, *paper_tickers, "^VIX", "SPY"]))
    print(f"Loading {len(all_tickers)} tickers ({cfg.period})...")
    loaded = load_price_data_batch(all_tickers, period=cfg.period)
    vix_df = loaded.get("^VIX")
    spy_df = loaded.get("SPY")
    try:
        macro_df = load_macro_data()
    except Exception:
        macro_df = None

    paper_data = {t: loaded[t] for t in paper_tickers if t in loaded}
    master_data = {t: loaded[t] for t in master_tickers if t in loaded}
    print(f"Paper universe loaded: {len(paper_data)}  Master universe loaded: {len(master_data)}")

    # Same holdout window for every arm (derived from the superset).
    holdout_start, holdout_end = portfolio_holdout_window(master_data)
    print(f"Holdout {holdout_start.date()} .. {holdout_end.date()}")

    paper_data = _filter_by_coverage(paper_data, holdout_start, holdout_end)
    master_data = _filter_by_coverage(master_data, holdout_start, holdout_end)
    print(
        f"After coverage filter: paper={len(paper_data)}  master={len(master_data)}\n"
    )

    datasets: dict[str, pd.DataFrame] = {}
    for name, data in (("paper", paper_data), ("master", master_data)):
        datasets[name] = _build_rank_dataset(
            data,
            prediction_horizon=cfg.prediction_horizon,
            vix_df=vix_df,
            spy_df=spy_df,
            macro_df=macro_df,
        )

    models: dict[str, tuple] = {}
    scored_oos: dict[str, pd.DataFrame] = {}
    for name, dataset in datasets.items():
        train_df = dataset[dataset["date"] < holdout_start].copy()
        test_df = dataset[
            (dataset["date"] >= holdout_start) & (dataset["date"] <= holdout_end)
        ].copy()
        print(f"[{name}] train rows={len(train_df):,}  test rows={len(test_df):,}")
        clf, reg = _train_rank_models(train_df, cfg.top_bucket_pct)
        models[name] = (clf, reg)
        scored_oos[name] = _score_oos(
            test_df, classifier=clf, regressor=reg, top_bucket_pct=cfg.top_bucket_pct,
        )

    paper_arm = _evaluate(scored_oos["paper"], paper_data, cfg, label="paper_110")
    master_arm = _evaluate(scored_oos["master"], master_data, cfg, label="master_259")

    # Arm 3: master-trained model, trading restricted to the paper universe.
    paper_set = set(paper_data.keys())
    cross = scored_oos["master"][scored_oos["master"]["ticker"].isin(paper_set)].copy()
    cross = _rerank_percentiles(cross)
    master_paper_arm = _evaluate(cross, paper_data, cfg, label="master_train_paper_trade")

    verdict = _verdict(paper_arm, master_arm, master_paper_arm)
    spy_return = _spy_reference_return(spy_df, holdout_start, holdout_end)

    report = {
        "generated_at": _utc_now(),
        "holdout": {"start": str(holdout_start.date()), "end": str(holdout_end.date())},
        "config": asdict(cfg),
        "spy_reference_return": round(spy_return, 4) if spy_return is not None else None,
        "paper_110": paper_arm,
        "master_259": master_arm,
        "master_train_paper_trade": master_paper_arm,
        "verdict": verdict,
    }
    summary_path = OUTPUT_DIR / "comparison_summary.json"
    summary_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\n=== OOS comparison (same holdout, fresh retrains) ===")
    for arm in (paper_arm, master_arm, master_paper_arm):
        p = arm["portfolio_oos"]
        print(
            f"{arm['label']:<26} n={arm['universe_size']:<4} AUC={arm['top_bucket_auc']}  "
            f"IC={arm['mean_cs_ic']}  ret={p['total_return']:.2%}  "
            f"bench={p['benchmark_return']:.2%}  Sharpe={p['sharpe_ratio']:.2f}  "
            f"MDD={p['max_drawdown']:.2%}  trades={p['trades']}"
        )
    if spy_return is not None:
        print(f"SPY buy&hold over holdout: {spy_return:.2%}")
    print(f"\nVerdict: {verdict}")
    print(f"Saved: {summary_path}")


if __name__ == "__main__":
    main()
