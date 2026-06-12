"""Report-only regularization sweep to reduce fold ROC-AUC variance."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.ml_model import _build_regime_feature_dataset, _collect_regime_cv_metrics
from src.ml_quality_report import ROC_AUC_STD_WARN_THRESHOLD

DEFAULT_OUTPUT_DIR = Path("logs/ml")
FOLD_STD_GATE = ROC_AUC_STD_WARN_THRESHOLD

REGULARIZATION_GRID: list[dict[str, Any]] = [
    {"name": "baseline", "lgbm": {}, "xgb": {}},
    {"name": "lgbm_l1_0.1", "lgbm": {"reg_alpha": 0.1, "reg_lambda": 0.0}, "xgb": {}},
    {"name": "lgbm_l2_0.5", "lgbm": {"reg_alpha": 0.0, "reg_lambda": 0.5}, "xgb": {}},
    {"name": "lgbm_elastic_1.0", "lgbm": {"reg_alpha": 0.5, "reg_lambda": 0.5}, "xgb": {}},
    {"name": "xgb_reg_0.5", "lgbm": {}, "xgb": {"reg_alpha": 0.5, "reg_lambda": 1.0}},
    {"name": "combo_tight", "lgbm": {"reg_alpha": 0.3, "reg_lambda": 0.3}, "xgb": {"reg_alpha": 0.3, "reg_lambda": 0.8}},
]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _metrics_summary(metrics: list[dict[str, Any]]) -> dict[str, Any]:
    if not metrics:
        return {"folds": 0, "roc_auc_mean": None, "roc_auc_std": None, "passes_gate": False}
    aucs = pd.Series([row["roc_auc"] for row in metrics], dtype=float)
    std_auc = float(aucs.std(ddof=0)) if len(aucs) > 1 else 0.0
    return {
        "folds": int(len(metrics)),
        "roc_auc_mean": float(aucs.mean()),
        "roc_auc_std": std_auc,
        "passes_gate": std_auc < FOLD_STD_GATE,
    }


def build_fold_stability_experiment_report(
    *,
    training_data: dict[str, pd.DataFrame],
    prediction_horizon: int = 20,
    target_return_threshold: float = 0.0,
    vix_df: pd.DataFrame | None = None,
    spy_df: pd.DataFrame | None = None,
    macro_df: pd.DataFrame | None = None,
    focus_regimes: tuple[str, ...] = ("BEAR", "BULL", "NEUTRAL"),
) -> dict[str, Any]:
    dataset = _build_regime_feature_dataset(
        training_data,
        prediction_horizon=prediction_horizon,
        target_return_threshold=target_return_threshold,
        vix_df=vix_df,
        spy_df=spy_df,
        macro_df=macro_df,
    )
    if dataset.empty:
        return {
            "generated_at": _utc_now_iso(),
            "status": "missing_training_data",
            "fold_std_gate": FOLD_STD_GATE,
            "grid": [row["name"] for row in REGULARIZATION_GRID],
            "results": {},
            "recommendation": "Training features could not be built.",
        }

    results: dict[str, Any] = {}
    best_overall: dict[str, Any] | None = None
    for regime in focus_regimes:
        regime_data = dataset[dataset["regime"].astype(str).str.upper() == regime]
        if len(regime_data) < 100:
            continue
        regime_rows: list[dict[str, Any]] = []
        for candidate in REGULARIZATION_GRID:
            metrics, _ = _collect_regime_cv_metrics(
                regime,
                regime_data,
                lgbm_params=candidate.get("lgbm"),
                xgb_params=candidate.get("xgb"),
            )
            summary = _metrics_summary(metrics)
            row = {"candidate": candidate["name"], **summary}
            regime_rows.append(row)
            if summary["roc_auc_std"] is not None and (
                best_overall is None
                or summary["roc_auc_std"] < best_overall["roc_auc_std"]
            ):
                best_overall = {"regime": regime, **row}

        results[regime] = regime_rows

    any_pass = any(
        row.get("passes_gate")
        for rows in results.values()
        for row in rows
    )
    recommendation = (
        f"Candidate {best_overall['candidate']} on {best_overall['regime']} has lowest fold std "
        f"({best_overall['roc_auc_std']:.4f}); evaluate in a label challenger before promotion."
        if best_overall and best_overall.get("roc_auc_std") is not None
        else "No regularization candidate improved fold stability."
    )
    if not any_pass:
        recommendation += " None cleared the fold-std gate yet."

    return {
        "generated_at": _utc_now_iso(),
        "status": "ok",
        "fold_std_gate": FOLD_STD_GATE,
        "grid": [row["name"] for row in REGULARIZATION_GRID],
        "results": results,
        "best_overall": best_overall,
        "any_passes_gate": any_pass,
        "recommendation": recommendation,
    }


def write_fold_stability_experiment_report(
    report: dict[str, Any],
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "fold_stability_experiment_report.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return path


def main() -> None:
    from src.data_loader import load_price_data_batch
    from src.macro_loader import load_macro_data
    from src.retrain_holdout import exclude_holdout_from_ticker_data, portfolio_holdout_window
    from src.settings import load_settings

    parser = argparse.ArgumentParser(description="Fold stability regularization sweep (report-only)")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--period", default="5y")
    args = parser.parse_args()

    settings = load_settings()
    training_data = load_price_data_batch(settings.tickers, period=args.period)
    context = load_price_data_batch(["^VIX"] + ([] if "SPY" in training_data else ["SPY"]), period=args.period)
    vix_df = context.get("^VIX")
    spy_df = training_data.get("SPY")
    if spy_df is None:
        spy_df = context.get("SPY")
    macro_df = load_macro_data(period=args.period)
    if macro_df.empty:
        macro_df = None

    holdout_start, _ = portfolio_holdout_window(training_data)
    training_fit = exclude_holdout_from_ticker_data(training_data, holdout_start)

    report = build_fold_stability_experiment_report(
        training_data=training_fit,
        vix_df=vix_df,
        spy_df=spy_df,
        macro_df=macro_df,
    )
    path = write_fold_stability_experiment_report(report, args.output_dir)
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
