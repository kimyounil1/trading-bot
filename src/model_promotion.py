"""Champion promotion apply logic (governance contract for retrain)."""

from __future__ import annotations

from typing import Any, Callable


def should_update_champion(decision: str) -> bool:
    return str(decision).upper() == "PROMOTE"


def apply_champion_promotion_if_needed(
    decision: str,
    promote_champion: Callable[[], Any],
) -> dict[str, Any]:
    """Update champion artifacts only when promotion decision is PROMOTE."""
    if not should_update_champion(decision):
        return {"champion_updated": False, "decision": decision}
    promote_champion()
    return {"champion_updated": True, "decision": decision}
