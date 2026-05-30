"""Schema regression for ML quality artifacts ([AGY])."""

import json
from pathlib import Path

import pandas as pd
import pytest

from src.ml_quality_report import (
    CALIBRATION_BINS_COLUMNS,
    CALIBRATION_REPORT_KEYS,
    FOLD_METRICS_COLUMNS,
    FOLD_STABILITY_REPORT_KEYS,
    validate_calibration_artifacts,
    validate_fold_metrics_csv,
    write_ml_quality_reports,
)
from tests.test_ml_quality_report import _sample_metrics_df

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "ml_quality"


@pytest.fixture(scope="module", autouse=True)
def build_fixtures_once(tmp_path_factory):
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    paths = write_ml_quality_reports(FIXTURE_DIR, _sample_metrics_df(), file_prefix="golden")
    yield paths


def test_fold_metrics_csv_schema():
    frame = validate_fold_metrics_csv(FIXTURE_DIR / "golden_fold_metrics.csv")
    assert list(frame.columns[: len(FOLD_METRICS_COLUMNS)]) == list(FOLD_METRICS_COLUMNS)
    assert frame["roc_auc"].between(0, 1).all()
    assert frame["brier_score"].between(0, 1).all()


def test_fold_stability_report_schema():
    report = json.loads(
        (FIXTURE_DIR / "golden_fold_stability_report.json").read_text(encoding="utf-8")
    )
    for key in FOLD_STABILITY_REPORT_KEYS:
        assert key in report
    assert "mean" in report["roc_auc"]


def test_calibration_report_and_bins_schema():
    report, bins_df = validate_calibration_artifacts(
        FIXTURE_DIR / "golden_model_calibration_report.json",
        FIXTURE_DIR / "golden_model_calibration_bins.csv",
    )
    for key in CALIBRATION_REPORT_KEYS:
        assert key in report
    assert list(bins_df.columns) == list(CALIBRATION_BINS_COLUMNS)
    assert (bins_df["count"] > 0).any()


def test_calibration_bins_required_columns_only():
    bins_df = pd.read_csv(FIXTURE_DIR / "golden_model_calibration_bins.csv")
    assert set(CALIBRATION_BINS_COLUMNS).issubset(bins_df.columns)
