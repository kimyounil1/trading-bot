"""Portfolio sleeve allocation — core / tournament / cash budgets."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from src.position_dust import dust_position_min_usd, is_dust_position

DEFAULT_SLEEVE_IDS = ("core", "tournament", "cash")
CASH_SLEEVE_ID = "cash"
CORE_SLEEVE_ID = "core"
TOURNAMENT_SLEEVE_ID = "tournament"


@dataclass(frozen=True)
class SleeveDefinition:
    sleeve_id: str
    enabled: bool
    target_weight: float
    profile: str = ""
    strategy: str = ""
    paper_only: bool = False


@dataclass(frozen=True)
class SleeveBudget:
    sleeve_id: str
    strategy: str
    target_weight: float
    target_notional: float
    current_notional: float
    available_cash: float
    order_budget: float
    open_order_reserved: float
    rebalance_needed: bool
    risk_mode: str = "normal"
    paper_only: bool = False


@dataclass
class PortfolioSleeveSnapshot:
    enabled: bool
    portfolio_value: float
    account_cash: float
    buying_power: float
    implicit_cash_weight: float
    sleeves: dict[str, SleeveBudget] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def default_sleeves_config() -> dict[str, dict[str, Any]]:
    return {
        CORE_SLEEVE_ID: {
            "enabled": True,
            "target_weight": 0.50,
            "profile": "paper",
            "strategy": "current_core",
            "paper_only": False,
        },
        TOURNAMENT_SLEEVE_ID: {
            "enabled": True,
            "target_weight": 0.30,
            "profile": "tournament_paper",
            "strategy": "alpha_tournament",
            "paper_only": True,
        },
        CASH_SLEEVE_ID: {
            "enabled": True,
            "target_weight": 0.20,
            "strategy": "cash_reserve",
            "paper_only": False,
        },
    }


def parse_sleeves_config(raw: Any) -> dict[str, SleeveDefinition]:
    if not isinstance(raw, dict) or not raw:
        return {}
    parsed: dict[str, SleeveDefinition] = {}
    for sleeve_id, payload in raw.items():
        if not isinstance(payload, dict):
            raise ValueError(f"sleeves.{sleeve_id}: must be an object")
        parsed[str(sleeve_id).strip().lower()] = SleeveDefinition(
            sleeve_id=str(sleeve_id).strip().lower(),
            enabled=bool(payload.get("enabled", True)),
            target_weight=float(payload.get("target_weight", 0.0)),
            profile=str(payload.get("profile", "") or ""),
            strategy=str(payload.get("strategy", "") or ""),
            paper_only=bool(payload.get("paper_only", False)),
        )
    return parsed


def validate_sleeves_config(
    sleeves: Mapping[str, SleeveDefinition],
    *,
    enabled: bool,
) -> list[str]:
    if not enabled:
        return []
    errors: list[str] = []
    if not sleeves:
        errors.append("portfolio_sleeves_enabled requires non-empty sleeves config")
        return errors

    enabled_sleeves = [s for s in sleeves.values() if s.enabled]
    if not enabled_sleeves:
        errors.append("at least one sleeve must be enabled")
        return errors

    total_weight = sum(max(0.0, s.target_weight) for s in enabled_sleeves)
    if total_weight > 1.0 + 1e-9:
        errors.append(
            f"enabled sleeve target_weight sum {total_weight:.4f} exceeds 1.0"
        )

    for sleeve in enabled_sleeves:
        if sleeve.target_weight < 0:
            errors.append(f"sleeves.{sleeve.sleeve_id}.target_weight must be >= 0")
        if sleeve.sleeve_id == CASH_SLEEVE_ID and sleeve.target_weight <= 0:
            errors.append("cash sleeve must have target_weight > 0 when sleeves enabled")

    core = sleeves.get(CORE_SLEEVE_ID)
    if core is None or not core.enabled:
        errors.append("core sleeve must exist and be enabled when sleeves are enabled")

    return errors


def sleeves_enabled(settings: Any) -> bool:
    return bool(getattr(settings, "portfolio_sleeves_enabled", False))


def load_sleeve_definitions(settings: Any) -> dict[str, SleeveDefinition]:
    if not sleeves_enabled(settings):
        return {}
    raw = getattr(settings, "sleeves", None) or default_sleeves_config()
    return parse_sleeves_config(raw)


def _meaningful_positions(
    positions: list[dict[str, Any]],
    *,
    dust_min_usd: float,
) -> list[dict[str, Any]]:
    return [
        position
        for position in positions
        if not is_dust_position(position, min_usd=dust_min_usd)
    ]


def _position_market_value(positions: list[dict[str, Any]]) -> float:
    total = 0.0
    for position in positions:
        try:
            total += abs(float(position.get("market_value") or 0.0))
        except (TypeError, ValueError):
            continue
    return total


def _open_order_notional(open_orders: list[dict[str, Any]]) -> float:
    reserved = 0.0
    for order in open_orders:
        side = str(order.get("side", "")).upper()
        if side != "BUY":
            continue
        for key in ("notional", "limit_price", "qty"):
            raw = order.get(key)
            if raw in (None, "", "None"):
                continue
            try:
                value = float(raw)
            except (TypeError, ValueError):
                continue
            if key == "notional" and value > 0:
                reserved += value
                break
            if key == "limit_price":
                qty_raw = order.get("qty")
                try:
                    qty = float(qty_raw)
                except (TypeError, ValueError):
                    qty = 0.0
                if value > 0 and qty > 0:
                    reserved += value * qty
                    break
    return max(0.0, reserved)


class PortfolioSleeveAllocator:
    """Split account notional/cash into sleeve budgets."""

    def __init__(
        self,
        settings: Any,
        *,
        account: dict[str, Any],
        positions: list[dict[str, Any]],
        open_orders: Optional[list[dict[str, Any]]] = None,
        sleeve_position_map: Optional[dict[str, str]] = None,
    ) -> None:
        self.settings = settings
        self.account = account
        self.positions = positions or []
        self.open_orders = open_orders or []
        self.sleeve_position_map = {
            str(k).upper(): str(v).lower()
            for k, v in (sleeve_position_map or {}).items()
        }
        self.enabled = sleeves_enabled(settings)
        self.definitions = load_sleeve_definitions(settings) if self.enabled else {}
        self.dust_min_usd = dust_position_min_usd(settings)

    def build_snapshot(self) -> PortfolioSleeveSnapshot:
        portfolio_value = float(self.account.get("portfolio_value") or 0.0)
        account_cash = float(self.account.get("cash") or 0.0)
        buying_power = float(self.account.get("buying_power") or account_cash)
        warnings: list[str] = []

        if not self.enabled:
            invested = _position_market_value(
                _meaningful_positions(self.positions, dust_min_usd=self.dust_min_usd)
            )
            order_budget = max(0.0, min(buying_power, account_cash, portfolio_value - invested))
            core_budget = SleeveBudget(
                sleeve_id=CORE_SLEEVE_ID,
                strategy="current_core",
                target_weight=1.0,
                target_notional=portfolio_value,
                current_notional=invested,
                available_cash=max(0.0, account_cash),
                order_budget=order_budget,
                open_order_reserved=_open_order_notional(self.open_orders),
                rebalance_needed=False,
                risk_mode="disabled",
                paper_only=False,
            )
            return PortfolioSleeveSnapshot(
                enabled=False,
                portfolio_value=portfolio_value,
                account_cash=account_cash,
                buying_power=buying_power,
                implicit_cash_weight=0.0,
                sleeves={CORE_SLEEVE_ID: core_budget},
                warnings=warnings,
            )

        enabled_defs = [d for d in self.definitions.values() if d.enabled]
        total_weight = sum(max(0.0, d.target_weight) for d in enabled_defs)
        implicit_cash_weight = max(0.0, 1.0 - total_weight)

        positions = _meaningful_positions(self.positions, dust_min_usd=self.dust_min_usd)
        invested_by_sleeve: dict[str, float] = {d.sleeve_id: 0.0 for d in enabled_defs}
        unassigned = 0.0
        for position in positions:
            symbol = str(position.get("symbol", "")).upper()
            mv = abs(float(position.get("market_value") or 0.0))
            sleeve_id = self.sleeve_position_map.get(symbol, CORE_SLEEVE_ID)
            if sleeve_id not in invested_by_sleeve:
                unassigned += mv
            else:
                invested_by_sleeve[sleeve_id] += mv
        if unassigned > 0:
            invested_by_sleeve[CORE_SLEEVE_ID] = invested_by_sleeve.get(CORE_SLEEVE_ID, 0.0) + unassigned

        cash_reserve_target = 0.0
        for definition in enabled_defs:
            if definition.sleeve_id == CASH_SLEEVE_ID:
                cash_reserve_target = portfolio_value * definition.target_weight
                break

        open_buy_reserved = _open_order_notional(self.open_orders)
        open_core_reserved = open_buy_reserved

        sleeves: dict[str, SleeveBudget] = {}
        for definition in enabled_defs:
            target_notional = portfolio_value * definition.target_weight
            current_notional = invested_by_sleeve.get(definition.sleeve_id, 0.0)
            if definition.sleeve_id == CASH_SLEEVE_ID:
                available_cash = max(0.0, min(account_cash, target_notional))
                order_budget = 0.0
                rebalance_needed = account_cash < target_notional * 0.95
            else:
                tradable_cash = max(0.0, account_cash - cash_reserve_target)
                sleeve_cash_share = tradable_cash * (
                    definition.target_weight / max(total_weight - self._cash_weight(enabled_defs), 1e-9)
                    if definition.sleeve_id != CASH_SLEEVE_ID
                    else 0.0
                )
                reserved = open_core_reserved if definition.sleeve_id == CORE_SLEEVE_ID else 0.0
                available_cash = max(0.0, sleeve_cash_share - reserved)
                headroom = max(0.0, target_notional - current_notional - reserved)
                order_budget = max(0.0, min(available_cash, headroom, buying_power - cash_reserve_target))
                rebalance_needed = current_notional > target_notional * 1.05

            sleeves[definition.sleeve_id] = SleeveBudget(
                sleeve_id=definition.sleeve_id,
                strategy=definition.strategy,
                target_weight=definition.target_weight,
                target_notional=round(target_notional, 2),
                current_notional=round(current_notional, 2),
                available_cash=round(available_cash, 2),
                order_budget=round(order_budget, 2),
                open_order_reserved=round(
                    open_core_reserved if definition.sleeve_id == CORE_SLEEVE_ID else 0.0,
                    2,
                ),
                rebalance_needed=rebalance_needed,
                risk_mode="paper_only" if definition.paper_only else "normal",
                paper_only=definition.paper_only,
            )

        if open_buy_reserved > buying_power:
            warnings.append("open BUY orders exceed buying_power")

        return PortfolioSleeveSnapshot(
            enabled=True,
            portfolio_value=portfolio_value,
            account_cash=account_cash,
            buying_power=buying_power,
            implicit_cash_weight=implicit_cash_weight,
            sleeves=sleeves,
            warnings=warnings,
        )

    @staticmethod
    def _cash_weight(definitions: list[SleeveDefinition]) -> float:
        for definition in definitions:
            if definition.sleeve_id == CASH_SLEEVE_ID:
                return max(0.0, definition.target_weight)
        return 0.0

    def order_budget_for(self, sleeve_id: str) -> float:
        snapshot = self.build_snapshot()
        budget = snapshot.sleeves.get(str(sleeve_id).lower())
        if budget is None:
            return 0.0
        return float(budget.order_budget)

    def assert_sleeve_execute_allowed(self, sleeve_id: str, *, environment: str) -> None:
        if not self.enabled:
            return
        definition = self.definitions.get(str(sleeve_id).lower())
        if definition is None:
            raise ValueError(f"unknown sleeve_id: {sleeve_id}")
        if environment == "live" and definition.paper_only:
            raise RuntimeError(
                f"sleeve {sleeve_id} is paper_only and cannot execute in live environment"
            )


def cap_order_amount_for_sleeve(
    order_amount: float,
    *,
    sleeve_id: str,
    allocator: PortfolioSleeveAllocator,
) -> float:
    budget = allocator.order_budget_for(sleeve_id)
    if budget <= 0:
        return 0.0
    return min(float(order_amount), budget)


def trim_candidates_to_sleeve_budget(
    candidates: list[dict[str, Any]],
    budget: float,
    *,
    amount_key: str = "order_amount",
    min_amount: float = 0.0,
) -> tuple[list[dict[str, Any]], float]:
    """Keep candidates in order while enforcing a running sleeve budget."""
    remaining = max(0.0, float(budget))
    trimmed: list[dict[str, Any]] = []
    for candidate in candidates:
        raw = float(candidate.get(amount_key) or 0.0)
        amount = min(raw, remaining)
        if amount <= min_amount:
            continue
        updated = dict(candidate)
        updated[amount_key] = amount
        trimmed.append(updated)
        remaining -= amount
    return trimmed, remaining


def validate_sleeve_open_order_budget(
    snapshot: PortfolioSleeveSnapshot,
    open_orders: list[dict[str, Any]],
) -> tuple[bool, str]:
    """Return (ok, reason) when open BUY orders fit sleeve budgets."""
    if not snapshot.enabled:
        return True, ""
    reserved = _open_order_notional(open_orders)
    buying_power = max(0.0, snapshot.buying_power)
    if reserved > buying_power * 1.01:
        return False, f"open BUY reserved ${reserved:.2f} exceeds buying_power ${buying_power:.2f}"
    core = snapshot.sleeves.get(CORE_SLEEVE_ID)
    if core is not None and core.open_order_reserved > core.order_budget + core.current_notional * 0.05:
        return False, (
            f"core sleeve open orders ${core.open_order_reserved:.2f} "
            f"exceed available budget ${core.order_budget:.2f}"
        )
    return True, ""


def sleeve_fields_for_audit(
    snapshot: PortfolioSleeveSnapshot,
    *,
    sleeve_id: str = CORE_SLEEVE_ID,
    budget_before: Optional[float] = None,
    budget_after: Optional[float] = None,
) -> dict[str, Any]:
    budget = snapshot.sleeves.get(str(sleeve_id).lower())
    if budget is None:
        return {
            "sleeve_id": sleeve_id,
            "sleeve_strategy": "",
            "sleeve_target_weight": None,
            "sleeve_budget_before": budget_before,
            "sleeve_budget_after": budget_after,
            "sleeve_risk_mode": "",
        }
    return {
        "sleeve_id": budget.sleeve_id,
        "sleeve_strategy": budget.strategy,
        "sleeve_target_weight": budget.target_weight,
        "sleeve_budget_before": budget_before if budget_before is not None else budget.order_budget,
        "sleeve_budget_after": budget_after,
        "sleeve_risk_mode": budget.risk_mode,
    }
