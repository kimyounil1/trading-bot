"""Fold variance report schema ([AGY])."""

from pathlib import Path

import pandas as pd

from src.fold_variance_report import (
    FOLD_VARIANCE_REPORT_KEYS,
    build_fold_variance_report,
    validate_fold_variance_report,
)

FIXTURE = Path(__file__).resolve().parents[1] / "logs" / "ml" / "ai_model_metrics.csv"


def test_build_fold_variance_report_from_metrics(tmp_path):
    if FIXTURE.is_file():
        metrics = FIXTURE
    else:
        metrics = tmp_path / "metrics.csv"
        pd.DataFrame(
            {
                "fold": [1, 2, 3, 4, 5],
                "roc_auc": [0.53, 0.50, 0.55, 0.44, 0.52],
                "test_positive_rate": [0.52, 0.64, 0.59, 0.58, 0.54],
                "prediction_positive_rate": [0.48, 0.29, 0.78, 0.50, 0.49],
            }
        ).to_csv(metrics, index=False)

    report = build_fold_variance_report(metrics)
    validate_fold_variance_report(report)
    for key in FOLD_VARIANCE_REPORT_KEYS:
        assert key in report
    assert report["stability"]["fold_count"] >= 1
    assert any(d["type"] == "worst_fold" for d in report["drivers"])
