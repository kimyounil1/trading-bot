"""Rollback decision path tests without xgboost ([AGY])."""

from pathlib import Path
from unittest.mock import patch

from src.model_governance import (
    ROLLBACK_MAX_DRAWDOWN,
    ROLLBACK_MIN_TOTAL_RETURN,
    ROLLBACK_MIN_WIN_RATE,
    evaluate_rollback_need,
    resolve_rollback_decision,
)


def test_skip_rollback_after_promotion() -> None:
    report = resolve_rollback_decision("PROMOTE", None, None, restore=False)
    assert report["decision"] == "SKIP_ROLLBACK_AFTER_PROMOTION"


def test_no_rollback_when_performance_ok() -> None:
    report = resolve_rollback_decision(
        "RETAIN_CHAMPION",
        {"total_return": 0.10, "max_drawdown": -0.05, "win_rate": 0.55},
        None,
        restore=False,
    )
    assert report["decision"] == "NO_ROLLBACK_NEEDED"


def test_rollback_restores_archived_champion() -> None:
    archived = (Path("/tmp/model.joblib"), Path("/tmp/meta.json"))
    with patch("src.model_governance._restore_archived_champion") as restore:
        report = resolve_rollback_decision(
            "RETAIN_CHAMPION",
            {
                "total_return": ROLLBACK_MIN_TOTAL_RETURN - 0.01,
                "max_drawdown": -0.05,
                "win_rate": 0.55,
            },
            archived,
            restore=True,
        )
    assert report["decision"] == "ROLLBACK_TO_ARCHIVED_CHAMPION"
    restore.assert_called_once()


def test_no_rollback_available_without_archive() -> None:
    report = resolve_rollback_decision(
        "RETAIN_CHAMPION",
        {
            "total_return": -0.20,
            "max_drawdown": ROLLBACK_MAX_DRAWDOWN - 0.01,
            "win_rate": ROLLBACK_MIN_WIN_RATE - 0.01,
        },
        None,
        restore=False,
    )
    assert report["decision"] == "NO_ROLLBACK_AVAILABLE"


def test_evaluate_rollback_need_flags_breaches() -> None:
    decision = evaluate_rollback_need(
        {"total_return": -0.12, "max_drawdown": -0.25, "win_rate": 0.30}
    )
    assert decision["should_rollback"]
