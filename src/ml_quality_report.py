"""Fold-level ROC-AUC stability and calibration report generation."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.metrics import brier_score_loss, roc_auc_score

from src.features import FEATURE_COLUMNS, build_features
from src.market_regime import compute_daily_regime

FOLD_METRICS_COLUMNS: tuple[str, ...] = (
    "regime",
    "fold",
    "roc_auc",
    "brier_score",
    "test_size",
    "walk_forward_fold",
    "walk_forward_period",
)

DEFAULT_ML_OUTPUT_DIR = Path("logs/ml")
DEFAULT_VALIDATION_OUTPUT_DIR = Path("logs/validation")

FOLD_METRICS_FILENAME = "fold_metrics.csv"
FOLD_STABILITY_REPORT_FILENAME = "fold_stability_report.json"
CALIBRATION_REPORT_FILENAME = "model_calibration_report.json"
CALIBRATION_BINS_FILENAME = "model_calibration_bins.csv"
CALIBRATION_ROWS_FILENAME = "model_calibration_rows.csv"

# Flag when cross-fold / cross-regime ROC-AUC spread is large (see logs/ml/ai_model_metrics.csv history).
ROC_AUC_STD_WARN_THRESHOLD = 0.05

PROMOTION_MIN_AVG_ROC_AUC = 0.51
PROMOTION_MAX_OVERALL_BRIER = 0.25

CALIBRATION_REPORT_KEYS: tuple[str, ...] = (
    "generated_at",
    "overall_avg_brier_score",
    "regimes",
    "bin_count",
)

CALIBRATION_BINS_COLUMNS: tuple[str, ...] = (
    "regime",
    "prob_bin",
    "count",
    "avg_pred",
    "actual_rate",
)

FOLD_STABILITY_REPORT_KEYS: tuple[str, ...] = (
    "generated_at",
    "fold_count",
    "roc_auc",
    "by_regime",
    "high_variance_warning",
    "roc_auc_std_warn_threshold",
)


@dataclass
class MlQualityPromotionCriteria:
    min_avg_roc_auc: float = PROMOTION_MIN_AVG_ROC_AUC
    max_overall_brier: float = PROMOTION_MAX_OVERALL_BRIER
    reject_high_fold_variance: bool = True


def evaluate_ml_quality_promotion_gates(
    challenger_metadata: dict[str, Any],
    fold_stability_report: dict[str, Any] | None,
    calibration_report: dict[str, Any] | None,
    criteria: MlQualityPromotionCriteria | None = None,
) -> dict[str, Any]:
    """Training-time CV metrics + calibration must pass before champion promotion."""
    criteria = criteria or MlQualityPromotionCriteria()
    failures: list[str] = []

    avg_auc = float(challenger_metadata.get("oos_metrics", {}).get("avg_roc_auc", 0.0))
    if avg_auc < criteria.min_avg_roc_auc:
        failures.append(
            f"avg_roc_auc={avg_auc:.4f} < min {criteria.min_avg_roc_auc:.4f}"
        )

    if calibration_report is None:
        failures.append("missing calibration report")
    else:
        brier = float(calibration_report.get("overall_avg_brier_score", 0.0))
        if brier > criteria.max_overall_brier:
            failures.append(
                f"overall_avg_brier_score={brier:.4f} > max {criteria.max_overall_brier:.4f}"
            )

    if fold_stability_report is None:
        failures.append("missing fold stability report")
    elif criteria.reject_high_fold_variance and fold_stability_report.get(
        "high_variance_warning"
    ):
        roc = fold_stability_report.get("roc_auc", {})
        failures.append(
            f"high fold ROC-AUC variance (std={roc.get('std')}, "
            f"threshold={fold_stability_report.get('roc_auc_std_warn_threshold')})"
        )

    return {
        "passed": not failures,
        "failures": failures,
        "avg_roc_auc": avg_auc,
        "criteria": {
            "min_avg_roc_auc": criteria.min_avg_roc_auc,
            "max_overall_brier": criteria.max_overall_brier,
            "reject_high_fold_variance": criteria.reject_high_fold_variance,
        },
    }


def validate_fold_metrics_csv(path: str | Path) -> pd.DataFrame:
    """Load fold_metrics.csv and enforce column schema ([AGY] regression helper)."""
    frame = normalize_fold_metrics_df(pd.read_csv(path))
    missing = [c for c in FOLD_METRICS_COLUMNS if c not in frame.columns]
    if missing:
        raise ValueError(f"fold_metrics missing columns: {missing}")
    return frame


def validate_calibration_artifacts(
    report_path: str | Path,
    bins_path: str | Path,
) -> tuple[dict[str, Any], pd.DataFrame]:
    """Validate calibration JSON keys and bins CSV schema."""
    report_path = Path(report_path)
    bins_path = Path(bins_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    missing_keys = [k for k in CALIBRATION_REPORT_KEYS if k not in report]
    if missing_keys:
        raise ValueError(f"calibration report missing keys: {missing_keys}")

    if not bins_path.is_file():
        return report, pd.DataFrame(columns=list(CALIBRATION_BINS_COLUMNS))

    bins_df = pd.read_csv(bins_path)
    missing_cols = [c for c in CALIBRATION_BINS_COLUMNS if c not in bins_df.columns]
    if missing_cols:
        raise ValueError(f"calibration bins missing columns: {missing_cols}")
    return report, bins_df


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _filter_ticker_df_by_date(
    df: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp | None = None,
) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    frame = df.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame = frame[frame["date"] >= pd.Timestamp(start)]
    if end is not None:
        frame = frame[frame["date"] < pd.Timestamp(end)]
    return frame.reset_index(drop=True)


def evaluate_walk_forward_oos_metrics(
    model,
    ticker_data: dict[str, pd.DataFrame],
    *,
    test_start: pd.Timestamp,
    test_end: pd.Timestamp,
    vix_df: pd.DataFrame | None = None,
    spy_df: pd.DataFrame | None = None,
    macro_df: pd.DataFrame | None = None,
    lookback_days: int = 400,
) -> pd.DataFrame:
    """ROC-AUC / Brier on the outer walk-forward test window (not inner training CV)."""
    lookback_start = test_start - pd.DateOffset(days=lookback_days)
    frames: list[pd.DataFrame] = []

    for ticker, df in ticker_data.items():
        window = _filter_ticker_df_by_date(df, lookback_start, test_end)
        if len(window) < 50:
            continue
        try:
            feature_df = build_features(
                window,
                prediction_horizon=model.prediction_horizon,
                target_return_threshold=model.target_return_threshold,
                vix_df=vix_df,
                spy_df=spy_df,
                macro_df=macro_df,
            )
        except ValueError:
            continue
        feature_df["ticker"] = ticker
        frames.append(feature_df)

    if not frames:
        return pd.DataFrame(columns=list(FOLD_METRICS_COLUMNS))

    dataset = pd.concat(frames, ignore_index=True).sort_values("date").reset_index(drop=True)
    if spy_df is not None and vix_df is not None:
        regime_series = compute_daily_regime(spy_df, vix_df)
        dataset = dataset.merge(
            regime_series.rename("regime"), left_on="date", right_index=True, how="left"
        )
        dataset["regime"] = dataset["regime"].fillna("NEUTRAL")
    else:
        dataset["regime"] = "NEUTRAL"

    dataset["date"] = pd.to_datetime(dataset["date"], errors="coerce")
    oos = dataset[
        (dataset["date"] >= pd.Timestamp(test_start))
        & (dataset["date"] < pd.Timestamp(test_end))
    ]
    if oos.empty:
        return pd.DataFrame(columns=list(FOLD_METRICS_COLUMNS))

    metrics: list[dict[str, Any]] = []
    calibration_rows: list[dict[str, Any]] = []
    for regime in ("BULL", "BEAR", "NEUTRAL"):
        regime_model = model.models.get(regime)
        if regime_model is None:
            continue
        regime_oos = oos[oos["regime"] == regime]
        if len(regime_oos) < 30:
            continue
        available_cols = [c for c in model.feature_columns if c in regime_oos.columns]
        x_test = regime_oos[available_cols]
        y_test = regime_oos["target"]
        proba = regime_model.predict_proba(x_test)[:, 1]
        try:
            auc = float(roc_auc_score(y_test, proba))
        except ValueError:
            auc = 0.5
        brier = float(brier_score_loss(y_test, proba))
        metrics.append(
            {
                "regime": regime,
                "fold": 1,
                "roc_auc": auc,
                "brier_score": brier,
                "test_size": int(len(regime_oos)),
            }
        )
        calibration_rows.extend(
            {
                "regime": regime,
                "fold": 1,
                "y_true": int(y_true),
                "y_prob": float(y_prob),
            }
            for y_true, y_prob in zip(y_test.tolist(), proba.tolist())
        )

    metrics_df = pd.DataFrame(metrics)
    metrics_df.attrs["calibration_rows"] = calibration_rows
    return metrics_df


def normalize_fold_metrics_df(metrics_df: pd.DataFrame) -> pd.DataFrame:
    """Ensure fold metrics CSV schema (missing optional columns filled with NA)."""
    if metrics_df is None or metrics_df.empty:
        return pd.DataFrame(columns=list(FOLD_METRICS_COLUMNS))

    frame = metrics_df.copy()
    for column in FOLD_METRICS_COLUMNS:
        if column not in frame.columns:
            frame[column] = pd.NA

    ordered = [c for c in FOLD_METRICS_COLUMNS if c in frame.columns]
    extra = [c for c in frame.columns if c not in FOLD_METRICS_COLUMNS]
    return frame[ordered + extra]


def _roc_auc_summary(series: pd.Series) -> dict[str, Any]:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return {
            "count": 0,
            "mean": None,
            "std": None,
            "min": None,
            "max": None,
            "range": None,
        }
    mean = float(values.mean())
    std = float(values.std(ddof=0)) if len(values) > 1 else 0.0
    min_v = float(values.min())
    max_v = float(values.max())
    return {
        "count": int(len(values)),
        "mean": mean,
        "std": std,
        "min": min_v,
        "max": max_v,
        "range": max_v - min_v,
        "coefficient_of_variation": (std / mean) if mean else None,
    }


def build_fold_stability_report(metrics_df: pd.DataFrame) -> dict[str, Any]:
    """Summarize ROC-AUC dispersion across CV / walk-forward folds."""
    frame = normalize_fold_metrics_df(metrics_df)
    if frame.empty or "roc_auc" not in frame.columns:
        return {
            "generated_at": _utc_now_iso(),
            "fold_count": 0,
            "roc_auc": _roc_auc_summary(pd.Series(dtype=float)),
            "by_regime": {},
            "high_variance_warning": False,
            "message": "no fold metrics available",
        }

    overall = _roc_auc_summary(frame["roc_auc"])
    by_regime: dict[str, Any] = {}
    if "regime" in frame.columns:
        for regime, regime_df in frame.groupby("regime", dropna=False):
            by_regime[str(regime)] = _roc_auc_summary(regime_df["roc_auc"])

    std = overall.get("std")
    high_var = std is not None and std >= ROC_AUC_STD_WARN_THRESHOLD

    walk_forward_summary = None
    if "walk_forward_fold" in frame.columns and frame["walk_forward_fold"].notna().any():
        wf = frame.dropna(subset=["walk_forward_fold"])
        walk_forward_summary = _roc_auc_summary(wf["roc_auc"])

    return {
        "generated_at": _utc_now_iso(),
        "fold_count": int(len(frame)),
        "roc_auc": overall,
        "by_regime": by_regime,
        "walk_forward_roc_auc": walk_forward_summary,
        "high_variance_warning": high_var,
        "roc_auc_std_warn_threshold": ROC_AUC_STD_WARN_THRESHOLD,
    }


def build_calibration_report(metrics_df: pd.DataFrame) -> tuple[dict[str, Any], pd.DataFrame]:
    calibration_rows = metrics_df.attrs.get("calibration_rows", []) if metrics_df is not None else []
    calibration_df = pd.DataFrame(calibration_rows)
    if calibration_df.empty:
        return {
            "generated_at": _utc_now_iso(),
            "overall_avg_brier_score": 0.0,
            "regimes": {},
            "bin_count": 0,
        }, pd.DataFrame()

    regime_brier: dict[str, Any] = {}
    if "brier_score" in metrics_df.columns and "regime" in metrics_df.columns:
        for regime, regime_df in metrics_df.groupby("regime"):
            regime_brier[str(regime)] = {
                "avg_brier_score": float(regime_df["brier_score"].mean()),
                "folds": int(len(regime_df)),
            }

    calibration_df["prob_bin"] = pd.cut(
        calibration_df["y_prob"],
        bins=[i / 10 for i in range(11)],
        include_lowest=True,
        duplicates="drop",
    )
    bin_rows = (
        calibration_df.groupby(["regime", "prob_bin"], observed=False)
        .agg(
            count=("y_true", "size"),
            avg_pred=("y_prob", "mean"),
            actual_rate=("y_true", "mean"),
        )
        .reset_index()
    )
    bin_rows["prob_bin"] = bin_rows["prob_bin"].astype(str)

    report = {
        "generated_at": _utc_now_iso(),
        "overall_avg_brier_score": (
            float(metrics_df["brier_score"].mean()) if "brier_score" in metrics_df.columns else 0.0
        ),
        "regimes": regime_brier,
        "bin_count": int(len(bin_rows)),
    }
    return report, bin_rows


def write_ml_quality_reports(
    output_dir: str | Path,
    metrics_df: pd.DataFrame,
    *,
    file_prefix: str = "",
) -> dict[str, Path]:
    """Write fold metrics, stability JSON, and calibration artifacts."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    prefix = f"{file_prefix}_" if file_prefix else ""
    fold_metrics_path = output_dir / f"{prefix}{FOLD_METRICS_FILENAME}"
    stability_path = output_dir / f"{prefix}{FOLD_STABILITY_REPORT_FILENAME}"
    calibration_path = output_dir / f"{prefix}{CALIBRATION_REPORT_FILENAME}"
    bins_path = output_dir / f"{prefix}{CALIBRATION_BINS_FILENAME}"
    rows_path = output_dir / f"{prefix}{CALIBRATION_ROWS_FILENAME}"

    fold_df = normalize_fold_metrics_df(metrics_df)
    fold_df.to_csv(fold_metrics_path, index=False)

    stability = build_fold_stability_report(metrics_df)
    stability_path.write_text(
        json.dumps(stability, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    calibration_report, bins_df = build_calibration_report(metrics_df)
    calibration_path.write_text(
        json.dumps(calibration_report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    if not bins_df.empty:
        bins_df.to_csv(bins_path, index=False)
    elif bins_path.exists():
        bins_path.unlink()

    calibration_rows = metrics_df.attrs.get("calibration_rows", []) if metrics_df is not None else []
    if calibration_rows:
        pd.DataFrame(calibration_rows).to_csv(rows_path, index=False)
    # Preserve existing per-row calibration data when regenerating from fold_metrics.csv only.

    return {
        "fold_metrics": fold_metrics_path,
        "fold_stability": stability_path,
        "calibration_report": calibration_path,
        "calibration_bins": bins_path,
        "calibration_rows": rows_path,
    }


def load_fold_metrics_csv(path: str | Path) -> pd.DataFrame:
    return normalize_fold_metrics_df(pd.read_csv(path))


def regenerate_reports_from_fold_metrics_csv(
    metrics_path: str | Path,
    output_dir: str | Path | None = None,
    *,
    file_prefix: str = "",
) -> dict[str, Path]:
    """Rebuild stability (and empty calibration) from saved fold_metrics.csv only."""
    metrics_path = Path(metrics_path)
    output_dir = Path(output_dir or metrics_path.parent)
    metrics_df = load_fold_metrics_csv(metrics_path)
    return write_ml_quality_reports(output_dir, metrics_df, file_prefix=file_prefix)


def rebuild_calibration_artifacts_from_training(
    output_dir: str | Path = DEFAULT_ML_OUTPUT_DIR,
    *,
    period: str = "5y",
    prediction_horizon: int = 20,
    target_return_threshold: float = 0.0,
) -> dict[str, Path]:
    """Re-run regime CV to populate model_calibration_rows.csv (no champion retrain)."""
    from src.data_loader import load_price_data_batch
    from src.macro_loader import load_macro_data
    from src.ml_model import collect_regime_cv_metrics_df
    from src.retrain_holdout import exclude_holdout_from_ticker_data, portfolio_holdout_window
    from src.settings import load_settings

    settings = load_settings()
    training_data = load_price_data_batch(settings.tickers, period=period)

    context_tickers = ["^VIX"]
    if "SPY" not in training_data:
        context_tickers.append("SPY")
    context_data = load_price_data_batch(context_tickers, period=period)
    vix_df = context_data.get("^VIX")
    spy_df = training_data.get("SPY") if "SPY" in training_data else context_data.get("SPY")

    macro_df = load_macro_data(period=period)
    if macro_df.empty:
        macro_df = None

    holdout_start, _holdout_end = portfolio_holdout_window(training_data)
    training_data_fit = exclude_holdout_from_ticker_data(training_data, holdout_start)

    metrics_df = collect_regime_cv_metrics_df(
        training_data_fit,
        prediction_horizon=prediction_horizon,
        target_return_threshold=target_return_threshold,
        vix_df=vix_df,
        spy_df=spy_df,
        macro_df=macro_df,
    )
    if metrics_df.empty:
        raise ValueError("CV metrics collection produced no rows; check training data.")

    return write_ml_quality_reports(output_dir, metrics_df)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate fold stability and calibration reports from fold metrics"
    )
    parser.add_argument(
        "--metrics",
        type=Path,
        default=DEFAULT_ML_OUTPUT_DIR / "ai_model_metrics.csv",
        help="Source metrics CSV (retrain legacy path) or fold_metrics.csv",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: parent of --metrics)",
    )
    parser.add_argument(
        "--file-prefix",
        default="",
        help="Optional filename prefix (e.g. walk_forward)",
    )
    parser.add_argument(
        "--rebuild-calibration-rows",
        action="store_true",
        help="Re-run regime CV to write model_calibration_rows.csv (no full retrain)",
    )
    parser.add_argument(
        "--period",
        default="5y",
        help="Price history period for --rebuild-calibration-rows",
    )
    args = parser.parse_args()

    if args.rebuild_calibration_rows:
        output_dir = args.output_dir or DEFAULT_ML_OUTPUT_DIR
        paths = rebuild_calibration_artifacts_from_training(
            output_dir,
            period=args.period,
        )
        print(f"Wrote calibration rows: {paths['calibration_rows']}")
        print(f"Wrote calibration report: {paths['calibration_report']}")
        if paths["calibration_bins"].is_file():
            print(f"Wrote calibration bins: {paths['calibration_bins']}")
        return

    output_dir = args.output_dir or args.metrics.parent
    paths = regenerate_reports_from_fold_metrics_csv(
        args.metrics,
        output_dir,
        file_prefix=args.file_prefix,
    )
    stability = json.loads(paths["fold_stability"].read_text(encoding="utf-8"))
    print(f"Wrote fold metrics: {paths['fold_metrics']}")
    print(f"Wrote fold stability: {paths['fold_stability']}")
    print(f"Wrote calibration report: {paths['calibration_report']}")
    if paths["calibration_bins"].is_file():
        print(f"Wrote calibration bins: {paths['calibration_bins']}")
    if stability.get("high_variance_warning"):
        print(
            f"WARNING: ROC-AUC std {stability['roc_auc']['std']:.4f} "
            f">= threshold {ROC_AUC_STD_WARN_THRESHOLD}"
        )


if __name__ == "__main__":
    main()
