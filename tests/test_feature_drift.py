import unittest

import pandas as pd

from src.train_ai_model import _build_calibration_report, _compare_feature_stats


class FeatureDriftTest(unittest.TestCase):
    def test_compare_feature_stats_flags_large_mean_shift(self) -> None:
        baseline = {
            "generated_at": "2026-05-26T00:00:00Z",
            "feature_stats": {
                "volatility_20d": {"mean": 0.10, "std": 0.02},
                "volume_change_5d": {"mean": 0.05, "std": 0.10},
            },
        }
        current = {
            "generated_at": "2026-05-27T00:00:00Z",
            "feature_stats": {
                "volatility_20d": {"mean": 0.15, "std": 0.03},
                "volume_change_5d": {"mean": 0.08, "std": 0.10},
            },
        }

        report = _compare_feature_stats(baseline, current, zscore_threshold=1.5)

        self.assertEqual(report["drifted_feature_count"], 1)
        self.assertEqual(report["drifted_features"][0]["feature"], "volatility_20d")
        self.assertAlmostEqual(report["drifted_features"][0]["zscore_shift"], 2.5, places=6)

    def test_compare_feature_stats_ignores_missing_or_zero_std_features(self) -> None:
        baseline = {
            "generated_at": "2026-05-26T00:00:00Z",
            "feature_stats": {
                "vix_level": {"mean": 20.0, "std": 0.0},
            },
        }
        current = {
            "generated_at": "2026-05-27T00:00:00Z",
            "feature_stats": {
                "vix_level": {"mean": 35.0, "std": 5.0},
                "new_feature": {"mean": 1.0, "std": 1.0},
            },
        }

        report = _compare_feature_stats(baseline, current, zscore_threshold=1.0)

        self.assertEqual(report["drifted_feature_count"], 0)
        self.assertEqual(report["drifted_features"], [])

    def test_build_calibration_report_summarizes_brier_and_bins(self) -> None:
        metrics_df = pd.DataFrame(
            [
                {"regime": "BULL", "fold": 1, "roc_auc": 0.62, "brier_score": 0.18},
                {"regime": "BEAR", "fold": 1, "roc_auc": 0.58, "brier_score": 0.22},
            ]
        )
        metrics_df.attrs["calibration_rows"] = [
            {"regime": "BULL", "fold": 1, "y_true": 1, "y_prob": 0.8},
            {"regime": "BULL", "fold": 1, "y_true": 0, "y_prob": 0.3},
            {"regime": "BEAR", "fold": 1, "y_true": 1, "y_prob": 0.6},
        ]

        report, bins_df = _build_calibration_report(metrics_df)

        self.assertAlmostEqual(report["overall_avg_brier_score"], 0.20, places=2)
        self.assertIn("BULL", report["regimes"])
        self.assertGreater(report["bin_count"], 0)
        self.assertFalse(bins_df.empty)
        self.assertIn("actual_rate", bins_df.columns)


if __name__ == "__main__":
    unittest.main()
