import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.ml_model import (
    archive_current_champion,
    build_model_bundle,
    build_promotion_report,
    find_latest_archived_champion,
    load_model_metadata,
    portfolio_oos_beats_champion,
    restore_archived_champion,
    save_model_bundle,
)
from src.portfolio_backtest_validation import PortfolioBacktestThresholds
from src.model_governance import evaluate_rollback_need as _evaluate_rollback_need


def _good_ml_quality_reports() -> tuple[dict, dict]:
    return (
        {
            "high_variance_warning": False,
            "roc_auc": {"std": 0.01, "mean": 0.52},
            "roc_auc_std_warn_threshold": 0.05,
        },
        {"overall_avg_brier_score": 0.20, "bin_count": 2, "regimes": {}},
    )


def _sample_training_data() -> dict[str, pd.DataFrame]:
    return {
        "AAPL": pd.DataFrame({"date": pd.date_range("2024-01-01", periods=3)}),
        "MSFT": pd.DataFrame({"date": pd.date_range("2024-01-02", periods=3)}),
    }


class ModelGovernanceTest(unittest.TestCase):
    def test_build_model_bundle_embeds_metadata(self) -> None:
        metrics_df = pd.DataFrame(
            [
                {"regime": "BULL", "fold": 1, "roc_auc": 0.61},
                {"regime": "BEAR", "fold": 1, "roc_auc": 0.57},
            ]
        )

        bundle = build_model_bundle(
            trained_models={"BULL": object(), "BEAR": object()},
            metrics_df=metrics_df,
            training_data=_sample_training_data(),
            feature_columns=["feature_a", "feature_b"],
            prediction_horizon=20,
            target_return_threshold=0.0,
        )

        metadata = bundle["metadata"]
        self.assertEqual(metadata["ticker_count"], 2)
        self.assertEqual(metadata["feature_set_version"], "features_v2")
        self.assertEqual(metadata["trained_regimes"], ["BEAR", "BULL"])
        self.assertAlmostEqual(metadata["oos_metrics"]["avg_roc_auc"], 0.59, places=2)
        self.assertEqual(metadata["training_window_start"], "2024-01-01")
        self.assertEqual(metadata["training_window_end"], "2024-01-04")

    def test_build_promotion_report_prefers_stronger_challenger(self) -> None:
        challenger_metadata = {"oos_metrics": {"avg_roc_auc": 0.63}}
        champion_metadata = {"oos_metrics": {"avg_roc_auc": 0.60}}

        report = build_promotion_report(
            challenger_metadata,
            champion_metadata,
            require_portfolio_oos=False,
            require_ml_quality=False,
        )

        self.assertEqual(report["decision"], "PROMOTE")
        self.assertTrue(report["auc_gate_passed"])

    def test_build_promotion_report_requires_portfolio_gates(self) -> None:
        challenger_metadata = {"oos_metrics": {"avg_roc_auc": 0.63}}
        champion_metadata = {"oos_metrics": {"avg_roc_auc": 0.60}}
        weak_portfolio = {
            "total_return": 0.02,
            "benchmark_return": 0.20,
            "max_drawdown": -0.30,
            "sharpe_ratio": -0.2,
        }
        strong_portfolio = {
            "total_return": 0.15,
            "benchmark_return": 0.10,
            "max_drawdown": -0.08,
            "sharpe_ratio": 1.1,
        }

        stability, calibration = _good_ml_quality_reports()
        report = build_promotion_report(
            challenger_metadata,
            champion_metadata,
            challenger_portfolio=weak_portfolio,
            champion_portfolio=strong_portfolio,
            portfolio_thresholds=PortfolioBacktestThresholds(max_drawdown_floor=-0.20),
            fold_stability_report=stability,
            calibration_report=calibration,
        )

        self.assertEqual(report["decision"], "RETAIN_CHAMPION")
        self.assertTrue(report["auc_gate_passed"])
        self.assertTrue(report["ml_quality_gate_passed"])
        self.assertFalse(report["portfolio_gate_passed"])

    def test_build_promotion_report_promotes_on_auc_and_portfolio(self) -> None:
        challenger_metadata = {"oos_metrics": {"avg_roc_auc": 0.63}}
        champion_metadata = {"oos_metrics": {"avg_roc_auc": 0.60}}
        challenger_portfolio = {
            "total_return": 0.12,
            "benchmark_return": 0.10,
            "max_drawdown": -0.08,
            "sharpe_ratio": 1.2,
        }
        champion_portfolio = {
            "total_return": 0.08,
            "benchmark_return": 0.10,
            "max_drawdown": -0.10,
            "sharpe_ratio": 0.9,
        }

        stability, calibration = _good_ml_quality_reports()
        report = build_promotion_report(
            challenger_metadata,
            champion_metadata,
            challenger_portfolio=challenger_portfolio,
            champion_portfolio=champion_portfolio,
            fold_stability_report=stability,
            calibration_report=calibration,
        )

        self.assertEqual(report["decision"], "PROMOTE")
        self.assertTrue(report["ml_quality_gate_passed"])
        self.assertTrue(report["portfolio_gate_passed"])
        self.assertTrue(report["portfolio_vs_champion_passed"])
        self.assertTrue(portfolio_oos_beats_champion(challenger_portfolio, champion_portfolio))

    def test_build_promotion_report_rejects_poor_training_metrics(self) -> None:
        challenger_metadata = {"oos_metrics": {"avg_roc_auc": 0.63}}
        champion_metadata = {"oos_metrics": {"avg_roc_auc": 0.60}}
        stability = {
            "high_variance_warning": True,
            "roc_auc": {"std": 0.12},
            "roc_auc_std_warn_threshold": 0.05,
        }
        calibration = {"overall_avg_brier_score": 0.20, "bin_count": 1}
        challenger_portfolio = {
            "total_return": 0.12,
            "benchmark_return": 0.10,
            "max_drawdown": -0.08,
            "sharpe_ratio": 1.2,
        }

        report = build_promotion_report(
            challenger_metadata,
            champion_metadata,
            challenger_portfolio=challenger_portfolio,
            fold_stability_report=stability,
            calibration_report=calibration,
            require_portfolio_oos=True,
        )

        self.assertEqual(report["decision"], "RETAIN_CHAMPION")
        self.assertFalse(report["ml_quality_gate_passed"])

    def test_save_model_bundle_persists_metadata_json(self) -> None:
        bundle = {
            "models": {"NEUTRAL": "dummy-model"},
            "feature_columns": ["feature_a"],
            "prediction_horizon": 5,
            "target_return_threshold": 0.0,
            "metadata": {"saved_at": "2026-05-27T00:00:00Z", "oos_metrics": {"avg_roc_auc": 0.55}},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir) / "ai_score_model.joblib"
            metadata_path = Path(temp_dir) / "ai_score_model_metadata.json"
            save_model_bundle(bundle, model_path=model_path, metadata_path=metadata_path)
            loaded_metadata = load_model_metadata(metadata_path)
            self.assertTrue(model_path.exists())

        self.assertEqual(loaded_metadata["saved_at"], "2026-05-27T00:00:00Z")
        self.assertAlmostEqual(loaded_metadata["oos_metrics"]["avg_roc_auc"], 0.55, places=2)

    def test_archive_and_restore_champion_round_trip(self) -> None:
        bundle = {
            "models": {"NEUTRAL": "champion-v1"},
            "feature_columns": ["feature_a"],
            "prediction_horizon": 5,
            "target_return_threshold": 0.0,
            "metadata": {"saved_at": "2026-05-27T00:00:00Z", "oos_metrics": {"avg_roc_auc": 0.55}},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            champion_model_path = temp_root / "ai_score_model.joblib"
            champion_metadata_path = temp_root / "ai_score_model_metadata.json"
            archive_dir = temp_root / "archive"
            save_model_bundle(bundle, model_path=champion_model_path, metadata_path=champion_metadata_path)

            archived = archive_current_champion(
                model_path=champion_model_path,
                metadata_path=champion_metadata_path,
                archive_dir=archive_dir,
            )
            self.assertIsNotNone(archived)
            latest_archived = find_latest_archived_champion(archive_dir)
            self.assertEqual(latest_archived, archived)

            champion_model_path.unlink()
            champion_metadata_path.unlink()
            restore_archived_champion(
                archived_model_path=archived[0],
                archived_metadata_path=archived[1],
                model_path=champion_model_path,
                metadata_path=champion_metadata_path,
            )

            self.assertTrue(champion_model_path.exists())
            self.assertEqual(load_model_metadata(champion_metadata_path)["saved_at"], "2026-05-27T00:00:00Z")

    def test_evaluate_rollback_need_flags_breaches(self) -> None:
        decision = _evaluate_rollback_need(
            {
                "source": "logs/validation/oos_validation.csv",
                "total_return": -0.12,
                "max_drawdown": -0.25,
                "win_rate": 0.30,
            }
        )

        self.assertTrue(decision["should_rollback"])
        self.assertIn("total_return", decision["reason"])
        self.assertIn("win_rate", decision["reason"])
        self.assertIn("max_drawdown", decision["reason"])


if __name__ == "__main__":
    unittest.main()
