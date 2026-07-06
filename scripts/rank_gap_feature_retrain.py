"""Offline rank-model retrain: baseline vs baseline+gap_vol_20d challenger.

Matches production rank gate config (h20, top15%, q85). Does NOT touch paper config.
Outputs comparison report to logs/ml/rank_gap_feature_retrain/.

Usage:
  .venv/bin/python -m scripts.rank_gap_feature_retrain
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier, LGBMRegressor
from sklearn.metrics import brier_score_loss, mean_squared_error, roc_auc_score

from src.data_loader import load_price_data_batch
from src.features import (
    FEATURE_COLUMNS,
    FEATURE_COLUMNS_WITH_GAP_VOL,
    build_features,
)
from src.macro_loader import load_macro_data
from src.portfolio_backtester import _build_equal_weight_benchmark_values
from src.rank_label_experiment import (
    RankExperimentConfig,
    _build_rank_dataset,
    _simulate_top_bucket_portfolio,
)
from src.retrain_holdout import portfolio_holdout_window
from src.settings import load_settings

OUTPUT_DIR = Path("logs/ml/rank_gap_feature_retrain")
PRODUCTION_MODEL = Path("logs/ml/rank_label_experiment_h20_top15_q85/rank_models.joblib")
PRODUCTION_SUMMARY = Path("logs/ml/rank_label_experiment_h20_top15_q85/latest_summary.json")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _train_models(train_df: pd.DataFrame, feature_cols: list[str], top_bucket_pct: float):
    train_df = train_df.copy()
    cutoff = 1.0 - top_bucket_pct
    train_df["top_bucket_label"] = (
        train_df["future_return_percentile"] >= cutoff
    ).astype(int)
    clf = LGBMClassifier(
        n_estimators=250,
        learning_rate=0.04,
        max_depth=5,
        num_leaves=31,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=42,
        n_jobs=-1,
        verbose=-1,
    )
    reg = LGBMRegressor(
        n_estimators=250,
        learning_rate=0.04,
        max_depth=5,
        num_leaves=31,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=42,
        n_jobs=-1,
        verbose=-1,
    )
    x = train_df[feature_cols]
    clf.fit(x, train_df["top_bucket_label"])
    reg.fit(x, train_df["future_return_percentile"])
    return clf, reg


def _score_oos(
    test_df: pd.DataFrame,
    *,
    classifier,
    regressor,
    feature_cols: list[str],
    top_bucket_pct: float,
) -> pd.DataFrame:
    out = test_df.copy()
    x = out[feature_cols]
    cutoff = 1.0 - top_bucket_pct
    out["top_bucket_label"] = (out["future_return_percentile"] >= cutoff).astype(int)
    out["rank_clf_score"] = classifier.predict_proba(x)[:, 1]
    out["rank_reg_score"] = regressor.predict(x).clip(0.0, 1.0)
    out["rank_score"] = (out["rank_clf_score"] + out["rank_reg_score"]) / 2.0
    out["predicted_score_percentile"] = out.groupby("date")["rank_score"].rank(
        pct=True,
        method="average",
    )
    return out


def _mean_cs_ic(scored: pd.DataFrame) -> tuple[float, int]:
    """Cross-sectional Spearman IC: rank_score vs future_return_percentile per day."""
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


def _evaluate(
    scored: pd.DataFrame,
    ticker_data: dict,
    cfg: RankExperimentConfig,
    *,
    label: str,
) -> dict:
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
        "top_bucket_auc": round(auc, 4) if auc is not None else None,
        "brier": round(brier, 4),
        "rank_percentile_rmse": round(rmse, 4),
        "mean_cs_ic": round(mean_ic, 4),
        "ic_days": ic_days,
        "test_rows": int(len(scored)),
        "portfolio_oos": {k: round(v, 4) if isinstance(v, float) else v for k, v in portfolio.items()},
    }


def _gate(baseline: dict, challenger: dict) -> dict:
    b = baseline
    c = challenger
    auc_delta = None
    if b.get("top_bucket_auc") is not None and c.get("top_bucket_auc") is not None:
        auc_delta = c["top_bucket_auc"] - b["top_bucket_auc"]
    ic_delta = c["mean_cs_ic"] - b["mean_cs_ic"]
    gap_delta = (
        c["portfolio_oos"]["gap_pct"] - b["portfolio_oos"]["gap_pct"]
    )
    brier_delta = b["brier"] - c["brier"]  # lower brier is better
    passed = (
        (auc_delta is not None and auc_delta >= 0.005)
        or ic_delta >= 0.003
    ) and gap_delta >= -2.0 and brier_delta >= -0.005
    return {
        "auc_delta": round(auc_delta, 4) if auc_delta is not None else None,
        "ic_delta": round(ic_delta, 4),
        "gap_pct_delta": round(gap_delta, 2),
        "brier_improvement": round(brier_delta, 4),
        "passed": passed,
        "recommendation": (
            "Promote challenger to paper A/B (swap model path after review)"
            if passed
            else "Keep production baseline; challenger does not clear promotion gate"
        ),
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

    tickers = list(dict.fromkeys(list(settings.tickers) + ["^VIX", "SPY"]))
    print(f"Loading {len(tickers)} tickers ({cfg.period})...")
    loaded = load_price_data_batch(tickers, period=cfg.period)
    ticker_data = {t: loaded[t] for t in settings.tickers if t in loaded}
    vix_df = loaded.get("^VIX")
    spy_df = loaded.get("SPY")
    try:
        macro_df = load_macro_data()
    except Exception:
        macro_df = None

    full_dataset = _build_rank_dataset(
        ticker_data,
        prediction_horizon=cfg.prediction_horizon,
        vix_df=vix_df,
        spy_df=spy_df,
        macro_df=macro_df,
    )
    holdout_start, holdout_end = portfolio_holdout_window(ticker_data)
    train_df = full_dataset[full_dataset["date"] < holdout_start].copy()
    test_df = full_dataset[
        (full_dataset["date"] >= holdout_start) & (full_dataset["date"] <= holdout_end)
    ].copy()
    print(f"Train rows={len(train_df):,}  Test rows={len(test_df):,}")
    print(f"Holdout {holdout_start.date()} .. {holdout_end.date()}\n")

    # --- baseline (same feature set as production) ---
    print("Training baseline (FEATURE_COLUMNS)...")
    b_clf, b_reg = _train_models(train_df, list(FEATURE_COLUMNS), cfg.top_bucket_pct)
    b_scored = _score_oos(
        test_df, classifier=b_clf, regressor=b_reg,
        feature_cols=list(FEATURE_COLUMNS), top_bucket_pct=cfg.top_bucket_pct,
    )
    baseline = _evaluate(b_scored, ticker_data, cfg, label="baseline_retrain")

    # --- challenger (+ gap_vol_20d) ---
    print("Training challenger (FEATURE_COLUMNS + gap_vol_20d)...")
    c_clf, c_reg = _train_models(
        train_df, list(FEATURE_COLUMNS_WITH_GAP_VOL), cfg.top_bucket_pct,
    )
    c_scored = _score_oos(
        test_df, classifier=c_clf, regressor=c_reg,
        feature_cols=list(FEATURE_COLUMNS_WITH_GAP_VOL), top_bucket_pct=cfg.top_bucket_pct,
    )
    challenger = _evaluate(c_scored, ticker_data, cfg, label="challenger_gap_vol")

    gate = _gate(baseline, challenger)

    # save challenger artifacts (not production path)
    model_path = OUTPUT_DIR / "rank_models_gap_vol.joblib"
    joblib.dump(
        {
            "classifier": c_clf,
            "regressor": c_reg,
            "config": {**asdict(cfg), "feature_columns": list(FEATURE_COLUMNS_WITH_GAP_VOL)},
        },
        model_path,
    )

    prod_ref = {}
    if PRODUCTION_SUMMARY.is_file():
        prod_ref = json.loads(PRODUCTION_SUMMARY.read_text(encoding="utf-8")).get("metrics", {})

    report = {
        "generated_at": _utc_now(),
        "holdout": {"start": str(holdout_start.date()), "end": str(holdout_end.date())},
        "config": asdict(cfg),
        "production_metrics_jun2026": prod_ref,
        "baseline_retrain": baseline,
        "challenger_gap_vol": challenger,
        "gate": gate,
        "artifacts": {"challenger_model": str(model_path)},
    }
    summary_path = OUTPUT_DIR / "comparison_summary.json"
    summary_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("=== OOS comparison (same holdout, fresh retrain) ===")
    for key in ("baseline_retrain", "challenger_gap_vol"):
        m = report[key]
        p = m["portfolio_oos"]
        print(
            f"{m['label']:<22} AUC={m['top_bucket_auc']}  Brier={m['brier']}  "
            f"RMSE={m['rank_percentile_rmse']}  IC={m['mean_cs_ic']}  "
            f"gap={p['gap_pct']}%  Sharpe={p['sharpe_ratio']}  MDD={p['max_drawdown']}"
        )
    print(f"\nGate: {gate}")
    print(f"Saved: {summary_path}")
    print(f"Challenger model: {model_path} (NOT wired to paper config)")


if __name__ == "__main__":
    main()
