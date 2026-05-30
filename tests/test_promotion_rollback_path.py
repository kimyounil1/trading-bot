"""Promotion reject and rollback decision path tests ([AGY])."""

from pathlib import Path
from unittest.mock import patch

import pytest

from src.portfolio_backtest_validation import PortfolioBacktestThresholds

pytest.importorskip("xgboost")
from src.ml_model import build_promotion_report  # noqa: E402


def _good_ml() -> tuple[dict, dict]:
    return (
        {"high_variance_warning": False, "roc_auc": {"std": 0.01}},
        {"overall_avg_brier_score": 0.20, "bin_count": 1},
    )


def _good_portfolio() -> dict:
    return {
        "total_return": 0.12,
        "benchmark_return": 0.10,
        "max_drawdown": -0.08,
        "sharpe_ratio": 1.1,
    }


class TestChallengerRejection:
    def test_rejects_weaker_auc(self) -> None:
        stability, calibration = _good_ml()
        report = build_promotion_report(
            {"oos_metrics": {"avg_roc_auc": 0.48}},
            {"oos_metrics": {"avg_roc_auc": 0.55}},
            challenger_portfolio=_good_portfolio(),
            fold_stability_report=stability,
            calibration_report=calibration,
            require_portfolio_oos=True,
        )
        assert report["decision"] == "RETAIN_CHAMPION"
        assert not report["auc_gate_passed"]

    def test_rejects_failed_portfolio_gate(self) -> None:
        stability, calibration = _good_ml()
        report = build_promotion_report(
            {"oos_metrics": {"avg_roc_auc": 0.60}},
            {"oos_metrics": {"avg_roc_auc": 0.50}},
            challenger_portfolio={
                "total_return": -0.05,
                "benchmark_return": 0.20,
                "max_drawdown": -0.35,
                "sharpe_ratio": -0.3,
            },
            fold_stability_report=stability,
            calibration_report=calibration,
            portfolio_thresholds=PortfolioBacktestThresholds(max_drawdown_floor=-0.20),
        )
        assert report["decision"] == "RETAIN_CHAMPION"
        assert report["auc_gate_passed"]
        assert not report["portfolio_gate_passed"]

    def test_rejects_high_fold_variance(self) -> None:
        report = build_promotion_report(
            {"oos_metrics": {"avg_roc_auc": 0.60}},
            None,
            challenger_portfolio=_good_portfolio(),
            fold_stability_report={
                "high_variance_warning": True,
                "roc_auc": {"std": 0.12},
            },
            calibration_report={"overall_avg_brier_score": 0.20},
            require_ml_quality=True,
        )
        assert report["decision"] == "RETAIN_CHAMPION"
        assert not report["ml_quality_gate_passed"]
