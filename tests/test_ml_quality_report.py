"""Unit tests for fold stability and calibration report generation."""

import json
from pathlib import Path

import pandas as pd
import pytest

from src.ml_quality_report import (
    FOLD_METRICS_COLUMNS,
    build_calibration_report,
    build_fold_stability_report,
    evaluate_ml_quality_promotion_gates,
    evaluate_walk_forward_oos_metrics,
    normalize_fold_metrics_df,
    regenerate_reports_from_fold_metrics_csv,
    write_ml_quality_reports,
)


def _sample_metrics_df() -> pd.DataFrame:
    metrics_df = pd.DataFrame(
        [
            {"regime": "BULL", "fold": 1, "roc_auc": 0.52, "brier_score": 0.22, "test_size": 100},
            {"regime": "BULL", "fold": 2, "roc_auc": 0.53, "brier_score": 0.24, "test_size": 100},
            {"regime": "BEAR", "fold": 1, "roc_auc": 0.51, "brier_score": 0.28, "test_size": 80},
            {"regime": "BEAR", "fold": 2, "roc_auc": 0.52, "brier_score": 0.26, "test_size": 80},
        ]
    )
    metrics_df.attrs["calibration_rows"] = [
        {"regime": "BULL", "fold": 1, "y_true": 1, "y_prob": 0.7},
        {"regime": "BULL", "fold": 1, "y_true": 0, "y_prob": 0.3},
        {"regime": "BEAR", "fold": 1, "y_true": 1, "y_prob": 0.6},
        {"regime": "BEAR", "fold": 1, "y_true": 0, "y_prob": 0.4},
    ]
    return metrics_df


def test_normalize_fold_metrics_schema():
    df = normalize_fold_metrics_df(pd.DataFrame([{"regime": "BULL", "fold": 1, "roc_auc": 0.5}]))
    for col in ("regime", "fold", "roc_auc", "brier_score", "test_size"):
        assert col in df.columns


def test_fold_stability_report_flags_high_variance():
    metrics_df = _sample_metrics_df()
    report = build_fold_stability_report(metrics_df)
    assert report["fold_count"] == 4
    assert report["roc_auc"]["std"] is not None
    assert "BULL" in report["by_regime"]
    assert report["high_variance_warning"] is False


def test_fold_stability_warns_on_wide_roc_auc_spread():
    metrics_df = pd.DataFrame(
        [
            {"regime": "NEUTRAL", "fold": 1, "roc_auc": 0.40, "brier_score": 0.25, "test_size": 50},
            {"regime": "NEUTRAL", "fold": 2, "roc_auc": 0.55, "brier_score": 0.25, "test_size": 50},
        ]
    )
    report = build_fold_stability_report(metrics_df)
    assert report["high_variance_warning"] is True


def test_write_ml_quality_reports(tmp_path: Path):
    paths = write_ml_quality_reports(tmp_path, _sample_metrics_df())
    assert paths["fold_metrics"].is_file()
    stability = json.loads(paths["fold_stability"].read_text(encoding="utf-8"))
    assert stability["fold_count"] == 4
    calibration = json.loads(paths["calibration_report"].read_text(encoding="utf-8"))
    assert calibration["bin_count"] >= 1
    written = pd.read_csv(paths["fold_metrics"])
    assert list(written.columns[: len(FOLD_METRICS_COLUMNS)]) == list(FOLD_METRICS_COLUMNS)
    calibration_rows = pd.read_csv(paths["calibration_rows"])
    assert {"regime", "fold", "y_true", "y_prob"}.issubset(calibration_rows.columns)


def test_regenerate_from_csv_round_trip(tmp_path: Path):
    source = tmp_path / "fold_metrics.csv"
    _sample_metrics_df().to_csv(source, index=False)
    paths = regenerate_reports_from_fold_metrics_csv(source, tmp_path)
    assert paths["fold_stability"].is_file()


def test_calibration_report_empty_without_rows():
    report, bins = build_calibration_report(pd.DataFrame())
    assert report["bin_count"] == 0
    assert bins.empty


def test_ml_quality_promotion_gates_require_auc_brier_and_stability():
    metadata = {"oos_metrics": {"avg_roc_auc": 0.55}}
    stability = {"high_variance_warning": False, "roc_auc": {"std": 0.02}}
    calibration = {"overall_avg_brier_score": 0.22}
    result = evaluate_ml_quality_promotion_gates(metadata, stability, calibration)
    assert result["passed"]

    bad_auc = evaluate_ml_quality_promotion_gates(
        {"oos_metrics": {"avg_roc_auc": 0.48}}, stability, calibration
    )
    assert not bad_auc["passed"]


def test_build_promotion_dual_gate_integration():
    xgboost = pytest.importorskip("xgboost")
    del xgboost
    from src.ml_model import build_promotion_report

    stability = {"high_variance_warning": False, "roc_auc": {"std": 0.01}}
    calibration = {"overall_avg_brier_score": 0.20, "bin_count": 1}
    portfolio = {
        "total_return": 0.10,
        "benchmark_return": 0.08,
        "max_drawdown": -0.10,
        "sharpe_ratio": 1.0,
    }
    report = build_promotion_report(
        {"oos_metrics": {"avg_roc_auc": 0.55}},
        None,
        challenger_portfolio=portfolio,
        fold_stability_report=stability,
        calibration_report=calibration,
        require_portfolio_oos=True,
    )
    assert report["decision"] == "PROMOTE"
    assert report["ml_quality_gate_passed"]
    assert report["portfolio_gate_passed"]


def test_evaluate_walk_forward_oos_metrics_empty_without_data():
    class _StubModel:
        models = {}
        feature_columns = []
        prediction_horizon = 20
        target_return_threshold = 0.0

    metrics_df = evaluate_walk_forward_oos_metrics(
        _StubModel(),
        {},
        test_start=pd.Timestamp("2024-01-01"),
        test_end=pd.Timestamp("2024-07-01"),
    )
    assert metrics_df.empty
