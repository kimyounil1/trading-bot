"""Sleeve-level drift rebalance planning (core/tournament trim, cash raise)."""

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


def build_sleeve_rebalance_actions(
    *,
    snapshot: PortfolioSleeveSnapshot,
    positions: list[dict[str, Any]],
    sleeve_position_map: dict[str, str],
    dust_min_usd: float,
    min_cash_raise_usd: float = 50.0,
    min_excess_usd: float = 50.0,
) -> list[SleeveRebalanceAction]:
    if not snapshot.enabled:
        return []

    actions: list[SleeveRebalanceAction] = []

    cash_budget = snapshot.sleeves.get(CASH_SLEEVE_ID)
    if cash_budget is not None and cash_budget.rebalance_needed:
        cash_deficit = cash_budget.target_notional - snapshot.account_cash
        if cash_deficit >= min_cash_raise_usd:
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
        if budget is None or not budget.rebalance_needed:
            continue
        excess = budget.current_notional - budget.target_notional
        if excess < min_excess_usd:
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
