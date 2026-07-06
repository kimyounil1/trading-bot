"""Offline rank-model retrain: baseline vs baseline + earnings features challenger.

The three earnings features that cleared the IC screen (scripts/earnings_feature_research):
days_to_earnings, surprise_streak, last_surprise_pct. They are merged onto the rank
dataset by (ticker, date) — production feature pipeline is untouched.

Matches production rank gate config (h20, top15%, q85). Does NOT touch paper config.
Reuses the promotion gate from scripts/rank_gap_feature_retrain. Outputs comparison
report to logs/ml/earnings_feature_retrain/.

Usage:
  .venv/bin/python -m scripts.earnings_feature_retrain [--features surprise_streak,last_surprise_pct]
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd

from scripts.earnings_feature_research import (
    build_earnings_features,
    fetch_earnings_history,
    load_daily,
)
from scripts.rank_gap_feature_retrain import (
    _evaluate,
    _gate,
    _score_oos,
    _train_models,
)
from src.data_loader import load_price_data_batch
from src.features import FEATURE_COLUMNS
from src.macro_loader import load_macro_data
from src.rank_label_experiment import RankExperimentConfig, _build_rank_dataset
from src.retrain_holdout import portfolio_holdout_window
from src.settings import load_settings

OUTPUT_DIR = Path("logs/ml/earnings_feature_retrain")
EARNINGS_FEATURES = ["days_to_earnings", "surprise_streak", "last_surprise_pct"]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_earnings_panel(tickers: list[str]) -> pd.DataFrame:
    frames = []
    for t in tickers:
        price_df = load_daily(t)
        if price_df is None:
            continue
        reports = fetch_earnings_history(t)
        if reports is None or reports.empty:
            continue
        f = build_earnings_features(price_df, reports)
        if f.empty:
            continue
        f["ticker"] = t
        frames.append(f[["date", "ticker"] + EARNINGS_FEATURES])
    if not frames:
        raise ValueError("No earnings feature frames available")
    return pd.concat(frames, ignore_index=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--features",
        default=",".join(EARNINGS_FEATURES),
        help="comma-separated subset of " + ",".join(EARNINGS_FEATURES),
    )
    args = parser.parse_args()
    selected = [f.strip() for f in args.features.split(",") if f.strip()]
    unknown = set(selected) - set(EARNINGS_FEATURES)
    if unknown:
        raise SystemExit(f"Unknown earnings features: {sorted(unknown)}")

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
    vix_df = loaded.get("^VIX")
    spy_df = loaded.get("SPY")
    try:
        macro_df = load_macro_data()
    except Exception:
        macro_df = None

    dataset = _build_rank_dataset(
        ticker_data,
        prediction_horizon=cfg.prediction_horizon,
        vix_df=vix_df,
        spy_df=spy_df,
        macro_df=macro_df,
    )
    print("Building earnings feature panel...")
    earnings_panel = _build_earnings_panel(list(ticker_data.keys()))
    dataset["date"] = pd.to_datetime(dataset["date"])
    earnings_panel["date"] = pd.to_datetime(earnings_panel["date"])
    dataset = dataset.merge(earnings_panel, on=["date", "ticker"], how="left")
    coverage = dataset[EARNINGS_FEATURES].notna().mean()
    print(f"Earnings feature coverage:\n{coverage.round(3).to_string()}\n")

    holdout_start, holdout_end = portfolio_holdout_window(ticker_data)
    train_df = dataset[dataset["date"] < holdout_start].copy()
    test_df = dataset[
        (dataset["date"] >= holdout_start) & (dataset["date"] <= holdout_end)
    ].copy()
    print(f"Train rows={len(train_df):,}  Test rows={len(test_df):,}")
    print(f"Holdout {holdout_start.date()} .. {holdout_end.date()}\n")

    print("Training baseline (FEATURE_COLUMNS)...")
    b_clf, b_reg = _train_models(train_df, list(FEATURE_COLUMNS), cfg.top_bucket_pct)
    b_scored = _score_oos(
        test_df, classifier=b_clf, regressor=b_reg,
        feature_cols=list(FEATURE_COLUMNS), top_bucket_pct=cfg.top_bucket_pct,
    )
    baseline = _evaluate(b_scored, ticker_data, cfg, label="baseline_retrain")

    challenger_cols = list(FEATURE_COLUMNS) + selected
    print("Training challenger (FEATURE_COLUMNS + earnings features)...")
    c_clf, c_reg = _train_models(train_df, challenger_cols, cfg.top_bucket_pct)
    c_scored = _score_oos(
        test_df, classifier=c_clf, regressor=c_reg,
        feature_cols=challenger_cols, top_bucket_pct=cfg.top_bucket_pct,
    )
    challenger = _evaluate(c_scored, ticker_data, cfg, label="challenger_earnings")

    gate = _gate(baseline, challenger)

    variant = "_".join(selected) if selected != EARNINGS_FEATURES else "earnings"
    model_path = OUTPUT_DIR / f"rank_models_{variant}.joblib"
    joblib.dump(
        {
            "classifier": c_clf,
            "regressor": c_reg,
            "config": {**asdict(cfg), "feature_columns": challenger_cols},
        },
        model_path,
    )

    report = {
        "generated_at": _utc_now(),
        "holdout": {"start": str(holdout_start.date()), "end": str(holdout_end.date())},
        "config": asdict(cfg),
        "earnings_features": selected,
        "feature_coverage": {k: round(float(v), 4) for k, v in coverage.items()},
        "baseline_retrain": baseline,
        "challenger_earnings": challenger,
        "gate": gate,
        "artifacts": {"challenger_model": str(model_path)},
    }
    summary_path = OUTPUT_DIR / f"comparison_summary_{variant}.json"
    summary_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("=== OOS comparison (same holdout, fresh retrain) ===")
    for key in ("baseline_retrain", "challenger_earnings"):
        m = report[key]
        p = m["portfolio_oos"]
        print(
            f"{m['label']:<22} AUC={m['top_bucket_auc']}  Brier={m['brier']}  "
            f"IC={m['mean_cs_ic']}  gap={p['gap_pct']}%  Sharpe={p['sharpe_ratio']}  "
            f"MDD={p['max_drawdown']}"
        )
    print(f"\nGate: {gate}")
    print(f"Saved: {summary_path}")
    print(f"Challenger model: {model_path} (NOT wired to paper config)")


if __name__ == "__main__":
    main()
