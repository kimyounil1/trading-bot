"""Partial take-profit guards scaled to portfolio slot sizing."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PARTIAL_EXIT_STATE_PATH = Path("data/partial_exit_taken.json")

# Fraction of a full target slot (portfolio * max_position_pct) required before
# partial TP is meaningful — not hardcoded USD floors.
MIN_POSITION_SLOT_FRAC = 0.30
MIN_SELL_SLOT_FRAC = 0.20


@dataclass(frozen=True)
class PartialExitThresholds:
    target_slot_notional: float
    min_position_market_value: float
    min_sell_notional: float


def compute_partial_exit_thresholds(
    *,
    portfolio_value: float,
    settings: Any,
    dust_min_usd: float,
) -> PartialExitThresholds:
    """Derive partial-exit floors from the same slot sizing as buys."""
    max_position_pct = float(getattr(settings, "max_position_pct", 0.15))
    partial_ratio = float(getattr(settings, "partial_exit_ratio", 0.5))
    target_slot = max(0.0, portfolio_value * max_position_pct)

    min_position_mv = max(
        dust_min_usd * 2.0,
        target_slot * MIN_POSITION_SLOT_FRAC,
    )
    typical_partial_sell = target_slot * partial_ratio
    min_sell_notional = max(
        dust_min_usd,
        typical_partial_sell * MIN_SELL_SLOT_FRAC,
    )
    return PartialExitThresholds(
        target_slot_notional=target_slot,
        min_position_market_value=min_position_mv,
        min_sell_notional=min_sell_notional,
    )


def evaluate_partial_exit(
    *,
    position_market_value: float,
    sell_notional: float,
    thresholds: PartialExitThresholds,
    already_taken: bool,
) -> tuple[bool, str]:
    """Return (allowed, skip_reason). allowed=False when partial TP should not run."""
    if already_taken:
        return False, "partial take profit already taken for this position"

    if position_market_value < thresholds.min_position_market_value:
        return False, (
            "position too small for partial TP "
            f"(${position_market_value:.2f} < "
            f"${thresholds.min_position_market_value:.2f}, "
            f"target_slot=${thresholds.target_slot_notional:.2f})"
        )

    if sell_notional < thresholds.min_sell_notional:
        return False, (
            "partial sell notional too small "
            f"(${sell_notional:.2f} < ${thresholds.min_sell_notional:.2f})"
        )

    return True, ""


def _quarantine_corrupt_state_file(path: Path) -> None:
    corrupt_path = path.with_suffix(f"{path.suffix}.corrupt")
    try:
        if corrupt_path.exists():
            corrupt_path.unlink()
        path.replace(corrupt_path)
        print(f"Warning: moved corrupt partial-exit state to {corrupt_path}")
    except OSError as exc:
        print(f"Warning: failed to quarantine partial-exit state {path}: {exc}")


def normalize_partial_exit_state(payload: object) -> dict[str, bool]:
    if not isinstance(payload, dict):
        raise ValueError("partial exit state must be a JSON object")

    normalized: dict[str, bool] = {}
    for ticker, value in payload.items():
        if ticker is None:
            continue
        key = str(ticker).strip().upper()
        if isinstance(value, bool):
            normalized[key] = value
        elif value in (0, 1):
            normalized[key] = bool(value)
        else:
            raise ValueError(f"invalid partial-exit flag for {ticker!r}: {value!r}")
    return normalized


def sync_partial_exit_state(
    state: dict[str, bool],
    open_symbols: set[str],
) -> dict[str, bool]:
    """Drop flags for symbols that are no longer held (new holding = fresh partial)."""
    open_upper = {str(symbol).upper() for symbol in open_symbols}
    return {
        ticker: taken
        for ticker, taken in state.items()
        if ticker in open_upper and taken
    }


def load_partial_exit_state(*, open_symbols: set[str] | None = None) -> dict[str, bool]:
    if not PARTIAL_EXIT_STATE_PATH.exists():
        return {}

    try:
        payload = json.loads(PARTIAL_EXIT_STATE_PATH.read_text(encoding="utf-8"))
        state = normalize_partial_exit_state(payload)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"Warning: failed to load partial-exit state: {exc}")
        _quarantine_corrupt_state_file(PARTIAL_EXIT_STATE_PATH)
        return {}

    if open_symbols is None:
        return state
    return sync_partial_exit_state(state, open_symbols)


def save_partial_exit_state(state: dict[str, bool]) -> None:
    PARTIAL_EXIT_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    normalized = normalize_partial_exit_state(state)
    temp_path = PARTIAL_EXIT_STATE_PATH.with_suffix(
        f"{PARTIAL_EXIT_STATE_PATH.suffix}.tmp"
    )
    serialized = json.dumps(normalized, indent=2, sort_keys=True)
    temp_path.write_text(serialized, encoding="utf-8")
    with temp_path.open("r+", encoding="utf-8") as handle:
        handle.flush()
        os.fsync(handle.fileno())
    temp_path.replace(PARTIAL_EXIT_STATE_PATH)
