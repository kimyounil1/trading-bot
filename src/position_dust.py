"""Detect and handle negligible (dust) open positions."""

from __future__ import annotations

import os
from typing import Any


def dust_position_min_usd(settings: Any | None = None) -> float:
    if settings is not None:
        configured = getattr(settings, "dust_position_min_usd", None)
        if configured is not None:
            return max(0.0, float(configured))
    env = os.getenv("DUST_POSITION_MIN_USD", "5.0").strip()
    try:
        return max(0.0, float(env))
    except ValueError:
        return 5.0


def is_dust_position(position: dict[str, Any] | None, *, min_usd: float = 5.0) -> bool:
    if not position:
        return False
    try:
        market_value = abs(float(position.get("market_value", 0.0)))
    except (TypeError, ValueError):
        return False
    return market_value < min_usd


def effective_position(
    position: dict[str, Any] | None,
    *,
    min_usd: float = 5.0,
) -> dict[str, Any] | None:
    """None when position is dust — treat as flat for buys and guards."""
    if position is None or is_dust_position(position, min_usd=min_usd):
        return None
    return position


def count_meaningful_positions(
    positions: list[dict[str, Any]],
    *,
    min_usd: float = 5.0,
) -> int:
    return sum(1 for position in positions if not is_dust_position(position, min_usd=min_usd))


def meaningful_open_symbols(
    positions: list[dict[str, Any]],
    *,
    min_usd: float = 5.0,
) -> set[str]:
    """Open symbols excluding dust — for buy guards and correlation checks."""
    return {
        str(position["symbol"]).upper()
        for position in positions
        if not is_dust_position(position, min_usd=min_usd)
    }


def meaningful_gross_exposure(
    positions: list[dict[str, Any]],
    *,
    min_usd: float = 5.0,
) -> float:
    return sum(
        float(position.get("market_value", 0.0))
        for position in positions
        if not is_dust_position(position, min_usd=min_usd)
    )
