"""Model promotion rollback helpers (no ML training deps)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

OOS_VALIDATION_PATH = Path("logs/validation/oos_validation.csv")
BASELINE_SUMMARY_PATH = Path("logs/baselines/current_strategy/portfolio_summary.csv")

ROLLBACK_MIN_TOTAL_RETURN = -0.05
ROLLBACK_MIN_WIN_RATE = 0.35
ROLLBACK_MAX_DRAWDOWN = -0.20


def _restore_archived_champion(
    archived_model_path: Path,
    archived_metadata_path: Path,
) -> tuple[Path, Path]:
    from src.ml_model import restore_archived_champion

    return restore_archived_champion(archived_model_path, archived_metadata_path)


def load_recent_performance_snapshot() -> dict | None:
    if OOS_VALIDATION_PATH.exists():
        df = pd.read_csv(OOS_VALIDATION_PATH)
        if not df.empty:
            row = df.iloc[-1]
            return {
                "source": str(OOS_VALIDATION_PATH),
                "total_return": float(row.get("total_return", 0.0)),
                "max_drawdown": float(row.get("max_drawdown", 0.0)),
                "win_rate": float(row.get("win_rate", 0.0)),
            }

    if BASELINE_SUMMARY_PATH.exists():
        df = pd.read_csv(BASELINE_SUMMARY_PATH)
        if not df.empty:
            row = df.iloc[-1]
            return {
                "source": str(BASELINE_SUMMARY_PATH),
                "total_return": float(row.get("total_return", 0.0)),
                "max_drawdown": float(row.get("max_drawdown", 0.0)),
                "win_rate": float(row.get("win_rate", 0.0)),
            }

    return None


def evaluate_rollback_need(performance: dict | None) -> dict:
    if performance is None:
        return {
            "should_rollback": False,
            "reason": "no recent performance snapshot available",
        }

    breaches = []
    if performance["total_return"] <= ROLLBACK_MIN_TOTAL_RETURN:
        breaches.append(
            f"total_return={performance['total_return']:.4f} <= {ROLLBACK_MIN_TOTAL_RETURN:.4f}"
        )
    if performance["win_rate"] <= ROLLBACK_MIN_WIN_RATE:
        breaches.append(
            f"win_rate={performance['win_rate']:.4f} <= {ROLLBACK_MIN_WIN_RATE:.4f}"
        )
    if performance["max_drawdown"] <= ROLLBACK_MAX_DRAWDOWN:
        breaches.append(
            f"max_drawdown={performance['max_drawdown']:.4f} <= {ROLLBACK_MAX_DRAWDOWN:.4f}"
        )

    return {
        "should_rollback": bool(breaches),
        "reason": "; ".join(breaches) if breaches else "performance within thresholds",
        "performance": performance,
        "thresholds": {
            "min_total_return": ROLLBACK_MIN_TOTAL_RETURN,
            "min_win_rate": ROLLBACK_MIN_WIN_RATE,
            "max_drawdown": ROLLBACK_MAX_DRAWDOWN,
        },
    }


def resolve_rollback_decision(
    promotion_decision: str,
    performance: dict | None,
    archived_champion: tuple[Path, Path] | None,
    *,
    restore: bool = True,
) -> dict:
    """Build rollback report payload from promotion outcome and live performance snapshot."""
    rollback_report: dict = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "promotion_decision": promotion_decision,
    }
    if promotion_decision == "PROMOTE":
        rollback_report["decision"] = "SKIP_ROLLBACK_AFTER_PROMOTION"
        rollback_report["reason"] = (
            "new challenger promoted; wait for fresh performance before rollback evaluation"
        )
        return rollback_report

    rollback_eval = evaluate_rollback_need(performance)
    rollback_report.update(rollback_eval)
    if not rollback_eval["should_rollback"]:
        rollback_report["decision"] = "NO_ROLLBACK_NEEDED"
        return rollback_report

    if archived_champion is None:
        rollback_report["decision"] = "NO_ROLLBACK_AVAILABLE"
        rollback_report["reason"] = f"{rollback_eval['reason']}; no archived champion available"
        return rollback_report

    if restore:
        _restore_archived_champion(*archived_champion)
    rollback_report["decision"] = "ROLLBACK_TO_ARCHIVED_CHAMPION"
    rollback_report["restored_model_path"] = str(archived_champion[0])
    rollback_report["restored_metadata_path"] = str(archived_champion[1])
    return rollback_report
