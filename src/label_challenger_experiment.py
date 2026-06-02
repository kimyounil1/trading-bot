"""Train and evaluate a label/horizon challenger without promoting it."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from src.data_loader import load_price_data_batch
from src.macro_loader import load_macro_data
from src.ml_model import (
    FEATURE_COLUMNS,
    build_model_bundle,
    build_promotion_report,
    bundle_to_model_wrapper,
    load_model_metadata,
    train_ai_score_model,
)
from src.ml_quality_report import (
    evaluate_ml_quality_promotion_gates,
    write_ml_quality_reports,
)
from src.promotion_thresholds import promotion_portfolio_thresholds
from src.retrain_holdout import (
    exclude_holdout_from_ticker_data,
    portfolio_holdout_window,
)
from src.settings import load_settings
from src.train_ai_model import (
    VIX_TICKER,
    _load_champion_model_wrapper,
    _run_retrain_oos_portfolio,
)


DEFAULT_OUTPUT_DIR = Path("logs/ml/label_challenger")

LABEL_CHALLENGER_REPORT_KEYS = (
    "generated_at",
    "label_candidate",
    "metrics",
    "ml_quality_gate",
    "challenger_portfolio_oos",
    "champion_portfolio_oos",
    "promotion_report",
    "decision",
    "recommendation",
    "artifacts",
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _round(value: Any, digits: int = 4) -> float | None:
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return None


def _portfolio_gap(snapshot: dict[str, Any] | None) -> float | None:
    if not snapshot:
        return None
    return _round(
        float(snapshot.get("total_return", 0.0))
        - float(snapshot.get("benchmark_return", 0.0))
    )


def build_label_challenger_experiment(
    *,
    prediction_horizon: int,
    target_return_threshold: float,
    period: str = "5y",
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    settings = load_settings()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    training_data = load_price_data_batch(settings.tickers, period=period)
    context_tickers = [VIX_TICKER]
    if "SPY" not in training_data:
        context_tickers.append("SPY")
    context_data = load_price_data_batch(context_tickers, period=period)
    vix_df = context_data.get(VIX_TICKER)
    spy_df = training_data.get("SPY") if "SPY" in training_data else context_data.get("SPY")
    macro_df = load_macro_data(period=period)
    if macro_df.empty:
        macro_df = None

    holdout_start, holdout_end = portfolio_holdout_window(training_data)
    training_data_fit = exclude_holdout_from_ticker_data(training_data, holdout_start)

    model, metrics_df = train_ai_score_model(
        training_data=training_data_fit,
        prediction_horizon=prediction_horizon,
        target_return_threshold=target_return_threshold,
        vix_df=vix_df,
        spy_df=spy_df,
        macro_df=macro_df,
    )

    quality_paths = write_ml_quality_reports(output_dir, metrics_df)
    calibration_report = json.loads(
        quality_paths["calibration_report"].read_text(encoding="utf-8")
    )
    stability_report = json.loads(
        quality_paths["fold_stability"].read_text(encoding="utf-8")
    )

    bundle = build_model_bundle(
        trained_models=model.models,
        metrics_df=metrics_df,
        training_data=training_data_fit,
        feature_columns=FEATURE_COLUMNS,
        prediction_horizon=model.prediction_horizon,
        target_return_threshold=model.target_return_threshold,
    )
    bundle_path = output_dir / "challenger_bundle.joblib"
    metadata_path = output_dir / "challenger_metadata.json"
    joblib.dump(bundle, bundle_path)
    metadata_path.write_text(
        json.dumps(bundle["metadata"], indent=2, sort_keys=True),
        encoding="utf-8",
    )

    challenger_wrapper = bundle_to_model_wrapper(bundle)
    challenger_portfolio = _run_retrain_oos_portfolio(
        settings=settings,
        ticker_data=training_data,
        vix_df=vix_df,
        macro_df=macro_df,
        model_wrapper=challenger_wrapper,
        eval_start=holdout_start,
        eval_end=holdout_end,
    )
    challenger_portfolio["holdout_excluded_from_training"] = True

    champion_portfolio = None
    champion_wrapper = _load_champion_model_wrapper()
    if champion_wrapper is not None:
        champion_portfolio = _run_retrain_oos_portfolio(
            settings=settings,
            ticker_data=training_data,
            vix_df=vix_df,
            macro_df=macro_df,
            model_wrapper=champion_wrapper,
            eval_start=holdout_start,
            eval_end=holdout_end,
        )
        champion_portfolio["holdout_excluded_from_training"] = True

    ml_quality_gate = evaluate_ml_quality_promotion_gates(
        bundle["metadata"],
        stability_report,
        calibration_report,
    )
    promotion_report = build_promotion_report(
        challenger_metadata=bundle["metadata"],
        champion_metadata=load_model_metadata(),
        challenger_portfolio=challenger_portfolio,
        champion_portfolio=champion_portfolio,
        portfolio_thresholds=promotion_portfolio_thresholds(),
        require_portfolio_oos=bool(settings.use_ai_score),
        fold_stability_report=stability_report,
        calibration_report=calibration_report,
        require_ml_quality=True,
    )

    challenger_gap = _portfolio_gap(challenger_portfolio)
    champion_gap = _portfolio_gap(champion_portfolio)
    decision = "retain_champion"
    recommendation = (
        "Do not promote this label candidate unless ML quality and OOS portfolio gates pass."
    )
    if promotion_report.get("decision") == "PROMOTE":
        decision = "candidate_passed_promotion_gates"
        recommendation = "Candidate passed gates in experiment; review before manual promotion."
    elif challenger_gap is not None and challenger_gap >= 0:
        recommendation = (
            "Candidate beats benchmark but still failed another gate; inspect ML quality failures."
        )

    report = {
        "generated_at": _utc_now_iso(),
        "label_candidate": {
            "prediction_horizon": int(prediction_horizon),
            "target_return_threshold": float(target_return_threshold),
        },
        "metrics": {
            "avg_roc_auc": _round(metrics_df["roc_auc"].mean()),
            "avg_brier_score": _round(metrics_df["brier_score"].mean()),
            "roc_auc_std": _round(metrics_df["roc_auc"].std(ddof=0)),
            "trained_regimes": sorted(model.models.keys()),
        },
        "ml_quality_gate": ml_quality_gate,
        "challenger_portfolio_oos": challenger_portfolio,
        "champion_portfolio_oos": champion_portfolio,
        "promotion_report": promotion_report,
        "decision": decision,
        "recommendation": recommendation,
        "artifacts": {
            "bundle": str(bundle_path),
            "metadata": str(metadata_path),
            "fold_metrics": str(quality_paths["fold_metrics"]),
            "fold_stability": str(quality_paths["fold_stability"]),
            "calibration_report": str(quality_paths["calibration_report"]),
            "calibration_bins": str(quality_paths["calibration_bins"]),
            "calibration_rows": str(quality_paths["calibration_rows"]),
        },
    }
    validate_label_challenger_report(report)
    return report


def validate_label_challenger_report(report: dict[str, Any]) -> dict[str, Any]:
    missing = [key for key in LABEL_CHALLENGER_REPORT_KEYS if key not in report]
    if missing:
        raise ValueError(f"Missing label challenger report keys: {missing}")
    return report


def write_label_challenger_report(
    report: dict[str, Any],
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "latest_summary.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Train label/horizon challenger experiment")
    parser.add_argument("--prediction-horizon", type=int, default=20)
    parser.add_argument("--target-return-threshold", type=float, default=0.02)
    parser.add_argument("--period", default="5y")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    report = build_label_challenger_experiment(
        prediction_horizon=args.prediction_horizon,
        target_return_threshold=args.target_return_threshold,
        period=args.period,
        output_dir=args.output_dir,
    )
    path = write_label_challenger_report(report, args.output_dir)
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
