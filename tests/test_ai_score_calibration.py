import pandas as pd

from src.ai_score_calibration import calibrate_ai_score


def test_calibrate_ai_score_nearest_bin_by_regime(tmp_path):
    bins_path = tmp_path / "bins.csv"
    pd.DataFrame(
        [
            {"regime": "BULL", "avg_pred": 0.2, "actual_rate": 0.25},
            {"regime": "BULL", "avg_pred": 0.8, "actual_rate": 0.7},
            {"regime": "NEUTRAL", "avg_pred": 0.8, "actual_rate": 0.6},
        ]
    ).to_csv(bins_path, index=False)

    calibrated = calibrate_ai_score(0.76, regime="BULL", bins_path=bins_path)
    assert calibrated == 0.7


def test_calibrate_ai_score_fallback_neutral(tmp_path):
    bins_path = tmp_path / "bins.csv"
    pd.DataFrame(
        [
            {"regime": "NEUTRAL", "avg_pred": 0.5, "actual_rate": 0.45},
        ]
    ).to_csv(bins_path, index=False)

    calibrated = calibrate_ai_score(0.52, regime="BEAR", bins_path=bins_path)
    assert calibrated == 0.45


def test_calibrate_ai_score_missing_bins_returns_raw(tmp_path):
    calibrated = calibrate_ai_score(0.61, regime="BULL", bins_path=tmp_path / "missing.csv")
    assert calibrated == 0.61
