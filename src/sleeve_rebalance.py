"""Sleeve-level drift and allocation rebalance planning."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.portfolio_sleeves import (
    CASH_SLEEVE_ID,
    CORE_SLEEVE_ID,
    TOURNAMENT_SLEEVE_ID,
    PortfolioSleeveSnapshot,
)
from src.position_dust import is_dust_position


@dataclass(frozen=True)
class SleeveRebalanceAction:
    ticker: str
    sleeve_id: str
    sell_qty: float
    reason: str


@dataclass(frozen=True)
class SleeveRetagAction:
    ticker: str
    from_sleeve_id: str
    to_sleeve_id: str
    notional: float
    reason: str


@dataclass(frozen=True)
class SleeveAllocationRebalancePlan:
    retag_actions: tuple[SleeveRetagAction, ...]
    sell_actions: tuple[SleeveRebalanceAction, ...]
    trigger_reason: str = ""


def _positions_for_sleeve(
    positions: list[dict[str, Any]],
    sleeve_id: str,
    sleeve_position_map: dict[str, str],
    *,
    dust_min_usd: float,
) -> list[dict[str, Any]]:
    target = str(sleeve_id).lower()
    rows: list[dict[str, Any]] = []
    for position in positions:
        if is_dust_position(position, min_usd=dust_min_usd):
            continue
        symbol = str(position.get("symbol", "")).upper()
        mapped = sleeve_position_map.get(symbol, CORE_SLEEVE_ID)
        if mapped == target:
            rows.append(position)
    rows.sort(key=lambda row: abs(float(row.get("market_value") or 0.0)))
    return rows


def _plan_trim_from_sleeve(
    *,
    positions: list[dict[str, Any]],
    sleeve_id: str,
    sleeve_position_map: dict[str, str],
    excess_notional: float,
    dust_min_usd: float,
    reason_prefix: str,
) -> list[SleeveRebalanceAction]:
    actions: list[SleeveRebalanceAction] = []
    remaining = max(0.0, float(excess_notional))
    if remaining < 25.0:
        return actions

    for position in _positions_for_sleeve(
        positions,
        sleeve_id,
        sleeve_position_map,
        dust_min_usd=dust_min_usd,
    ):
        if remaining <= 0:
            break
        symbol = str(position.get("symbol", "")).upper()
        price = float(position.get("current_price") or 0.0)
        qty = float(position.get("qty") or 0.0)
        market_value = abs(float(position.get("market_value") or 0.0))
        if price <= 0 or qty <= 0 or market_value <= 0:
            continue
        sell_value = min(remaining, market_value)
        sell_qty = round(min(qty, sell_value / price), 4)
        if sell_qty <= 0:
            continue
        actions.append(
            SleeveRebalanceAction(
                ticker=symbol,
                sleeve_id=sleeve_id,
                sell_qty=sell_qty,
                reason=f"{reason_prefix} (excess=${remaining:.2f})",
            )
        )
        remaining -= sell_qty * price
    return actions


def build_sleeve_retag_actions(
    *,
    snapshot: PortfolioSleeveSnapshot,
    positions: list[dict[str, Any]],
    sleeve_position_map: dict[str, str],
    dust_min_usd: float,
    min_retag_usd: float = 25.0,
) -> list[SleeveRetagAction]:
    """Move whole positions from core to tournament to match investable-book weights."""
    if not snapshot.enabled:
        return []

    core_budget = snapshot.sleeves.get(CORE_SLEEVE_ID)
    tour_budget = snapshot.sleeves.get(TOURNAMENT_SLEEVE_ID)
    if core_budget is None or tour_budget is None or tour_budget.target_weight <= 0:
        return []

    investable_weight = core_budget.target_weight + tour_budget.target_weight
    if investable_weight <= 0:
        return []

    core_positions = _positions_for_sleeve(
        positions,
        CORE_SLEEVE_ID,
        sleeve_position_map,
        dust_min_usd=dust_min_usd,
    )
    tour_positions = _positions_for_sleeve(
        positions,
        TOURNAMENT_SLEEVE_ID,
        sleeve_position_map,
        dust_min_usd=dust_min_usd,
    )
    core_mv = sum(abs(float(row.get("market_value") or 0.0)) for row in core_positions)
    tour_mv = sum(abs(float(row.get("market_value") or 0.0)) for row in tour_positions)
    total_book = core_mv + tour_mv
    if total_book < min_retag_usd:
        return []

    ideal_core_mv = total_book * (core_budget.target_weight / investable_weight)
    ideal_tour_mv = total_book * (tour_budget.target_weight / investable_weight)
    retag_needed = ideal_tour_mv - tour_mv
    max_movable = max(0.0, core_mv - ideal_core_mv)
    retag_needed = min(retag_needed, max_movable)
    if retag_needed < min_retag_usd:
        return []

    actions: list[SleeveRetagAction] = []
    remaining = retag_needed
    for position in core_positions:
        if remaining < min_retag_usd:
            break
        symbol = str(position.get("symbol", "")).upper()
        market_value = abs(float(position.get("market_value") or 0.0))
        if market_value <= 0:
            continue
        actions.append(
            SleeveRetagAction(
                ticker=symbol,
                from_sleeve_id=CORE_SLEEVE_ID,
                to_sleeve_id=TOURNAMENT_SLEEVE_ID,
                notional=market_value,
                reason=(
                    f"sleeve allocation retag core→tournament "
                    f"(book_target=${ideal_tour_mv:.2f}, remaining=${remaining:.2f})"
                ),
            )
        )
        remaining -= market_value
    return actions


def build_sleeve_rebalance_actions(
    *,
    snapshot: PortfolioSleeveSnapshot,
    positions: list[dict[str, Any]],
    sleeve_position_map: dict[str, str],
    dust_min_usd: float,
    min_cash_raise_usd: float = 50.0,
    min_excess_usd: float = 50.0,
    allocation_mode: bool = False,
) -> list[SleeveRebalanceAction]:
    if not snapshot.enabled:
        return []

    actions: list[SleeveRebalanceAction] = []
    cash_min = min_cash_raise_usd if not allocation_mode else max(25.0, min_cash_raise_usd * 0.5)
    excess_min = min_excess_usd if not allocation_mode else max(25.0, min_excess_usd * 0.5)

    cash_budget = snapshot.sleeves.get(CASH_SLEEVE_ID)
    cash_deficit = 0.0
    if cash_budget is not None:
        cash_deficit = cash_budget.target_notional - snapshot.account_cash
    cash_raise_needed = cash_budget is not None and (
        cash_budget.rebalance_needed if not allocation_mode else cash_deficit >= cash_min
    )
    if cash_raise_needed and cash_deficit >= cash_min:
        actions.extend(
            _plan_trim_from_sleeve(
                positions=positions,
                sleeve_id=CORE_SLEEVE_ID,
                sleeve_position_map=sleeve_position_map,
                excess_notional=cash_deficit,
                dust_min_usd=dust_min_usd,
                reason_prefix="sleeve cash raise",
            )
        )

    for sleeve_id in (CORE_SLEEVE_ID, TOURNAMENT_SLEEVE_ID):
        budget = snapshot.sleeves.get(sleeve_id)
        if budget is None:
            continue
        excess = budget.current_notional - budget.target_notional
        if allocation_mode:
            if excess < excess_min:
                continue
        elif not budget.rebalance_needed or excess < excess_min:
            continue
        actions.extend(
            _plan_trim_from_sleeve(
                positions=positions,
                sleeve_id=sleeve_id,
                sleeve_position_map=sleeve_position_map,
                excess_notional=excess,
                dust_min_usd=dust_min_usd,
                reason_prefix=f"sleeve {sleeve_id} overweight trim",
            )
        )

    return actions


def build_sleeve_allocation_rebalance_plan(
    *,
    snapshot: PortfolioSleeveSnapshot,
    positions: list[dict[str, Any]],
    sleeve_position_map: dict[str, str],
    dust_min_usd: float,
    trigger_reason: str = "",
) -> SleeveAllocationRebalancePlan:
    retag_actions = build_sleeve_retag_actions(
        snapshot=snapshot,
        positions=positions,
        sleeve_position_map=sleeve_position_map,
        dust_min_usd=dust_min_usd,
    )
    working_map = dict(sleeve_position_map)
    for action in retag_actions:
        working_map[action.ticker] = action.to_sleeve_id

    sell_actions = build_sleeve_rebalance_actions(
        snapshot=snapshot,
        positions=positions,
        sleeve_position_map=working_map,
        dust_min_usd=dust_min_usd,
        allocation_mode=True,
    )
    return SleeveAllocationRebalancePlan(
        retag_actions=tuple(retag_actions),
        sell_actions=tuple(sell_actions),
        trigger_reason=trigger_reason,
    )
