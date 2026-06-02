from pathlib import Path

import pandas as pd

from src.calibration_experiment import build_calibration_experiment_report


def test_calibration_experiment_reports_missing_rows(tmp_path: Path):
    report = build_calibration_experiment_report(tmp_path / "missing.csv")
    assert report["status"] == "missing_data"
    assert "Run retrain first" in report["recommendation"]


def test_calibration_experiment_scores_candidates(tmp_path: Path):
    rows = []
    for fold in (1, 2, 3):
        for i in range(40):
            y_true = 1 if i >= 20 else 0
            # Deliberately under-confident probabilities; calibration can improve Brier.
            y_prob = 0.55 if y_true else 0.45
            rows.append(
                {
                    "regime": "BULL",
                    "fold": fold,
                    "y_true": y_true,
                    "y_prob": y_prob,
                }
            )
    path = tmp_path / "rows.csv"
    pd.DataFrame(rows).to_csv(path, index=False)

    report = build_calibration_experiment_report(path)

    assert report["status"] == "ok"
    assert report["overall"]["base"]["brier"] is not None
    assert report["overall"]["best_method"] in {"base", "platt", "isotonic"}
    assert "BULL" in report["by_regime"]
