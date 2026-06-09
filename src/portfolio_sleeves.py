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
            "paper_only": False,
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


def _order_notional(order: dict[str, Any]) -> float:
    for key in ("notional", "limit_price", "qty"):
        raw = order.get(key)
        if raw in (None, "", "None"):
            continue
        try:
            value = float(raw)
        except (TypeError, ValueError):
            continue
        if key == "notional" and value > 0:
            return value
        if key == "limit_price":
            qty_raw = order.get("qty")
            try:
                qty = float(qty_raw)
            except (TypeError, ValueError):
                qty = 0.0
            if value > 0 and qty > 0:
                return value * qty
    return 0.0


def _infer_order_sleeve_id(order: dict[str, Any]) -> str:
    client_order_id = str(
        order.get("client_order_id")
        or order.get("client_orderId")
        or order.get("id")
        or ""
    ).lower()
    if client_order_id.startswith("tour_"):
        return TOURNAMENT_SLEEVE_ID
    return CORE_SLEEVE_ID


def _open_order_notional(open_orders: list[dict[str, Any]]) -> float:
    return sum(
        _order_notional(order)
        for order in open_orders
        if str(order.get("side", "")).upper() == "BUY"
    )


def _open_order_notional_by_sleeve(
    open_orders: list[dict[str, Any]],
) -> dict[str, float]:
    totals = {CORE_SLEEVE_ID: 0.0, TOURNAMENT_SLEEVE_ID: 0.0}
    for order in open_orders:
        if str(order.get("side", "")).upper() != "BUY":
            continue
        sleeve_id = _infer_order_sleeve_id(order)
        amount = _order_notional(order)
        if sleeve_id == TOURNAMENT_SLEEVE_ID:
            totals[TOURNAMENT_SLEEVE_ID] += amount
        else:
            totals[CORE_SLEEVE_ID] += amount
    return totals


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
        reserved_by_sleeve = _open_order_notional_by_sleeve(self.open_orders)
        open_core_reserved = reserved_by_sleeve.get(CORE_SLEEVE_ID, 0.0)
        open_tournament_reserved = reserved_by_sleeve.get(TOURNAMENT_SLEEVE_ID, 0.0)

        sleeves: dict[str, SleeveBudget] = {}
        for definition in enabled_defs:
            target_notional = portfolio_value * definition.target_weight
            current_notional = invested_by_sleeve.get(definition.sleeve_id, 0.0)
            if definition.sleeve_id == CASH_SLEEVE_ID:
                available_cash = max(0.0, min(account_cash, target_notional))
                order_budget = 0.0
                rebalance_needed = account_cash < target_notional * 0.95
                sleeve_reserved = 0.0
            elif definition.sleeve_id == TOURNAMENT_SLEEVE_ID:
                tradable_cash = max(0.0, account_cash - cash_reserve_target)
                sleeve_cash_share = tradable_cash * (
                    definition.target_weight
                    / max(total_weight - self._cash_weight(enabled_defs), 1e-9)
                )
                sleeve_reserved = open_tournament_reserved
                available_cash = max(0.0, sleeve_cash_share - sleeve_reserved)
                headroom = max(0.0, target_notional - current_notional - sleeve_reserved)
                order_budget = max(
                    0.0,
                    min(available_cash, headroom, buying_power - cash_reserve_target),
                )
                rebalance_needed = current_notional > target_notional * 1.05
            else:
                tradable_cash = max(0.0, account_cash - cash_reserve_target)
                sleeve_cash_share = tradable_cash * (
                    definition.target_weight
                    / max(total_weight - self._cash_weight(enabled_defs), 1e-9)
                )
                sleeve_reserved = open_core_reserved
                available_cash = max(0.0, sleeve_cash_share - sleeve_reserved)
                headroom = max(0.0, target_notional - current_notional - sleeve_reserved)
                order_budget = max(
                    0.0,
                    min(available_cash, headroom, buying_power - cash_reserve_target),
                )
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
                    sleeve_reserved if definition.sleeve_id != CASH_SLEEVE_ID else 0.0,
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


def compute_sleeve_cash_surplus_deploy(
    snapshot: PortfolioSleeveSnapshot,
    *,
    min_surplus_usd: float = 50.0,
) -> dict[str, float]:
    """Extra buy budget per investable sleeve when account cash exceeds cash target."""
    if not snapshot.enabled:
        return {}

    cash_budget = snapshot.sleeves.get(CASH_SLEEVE_ID)
    if cash_budget is None:
        return {}

    surplus = float(snapshot.account_cash) - float(cash_budget.target_notional)
    if surplus < min_surplus_usd:
        return {}

    sleeves: list[tuple[str, float, float]] = []
    for sleeve_id in (CORE_SLEEVE_ID, TOURNAMENT_SLEEVE_ID):
        budget = snapshot.sleeves.get(sleeve_id)
        if budget is None or budget.target_weight <= 0:
            continue
        headroom = max(
            0.0,
            budget.target_notional - budget.current_notional - budget.open_order_reserved,
        )
        if headroom >= 10.0:
            sleeves.append((sleeve_id, budget.target_weight, headroom))

    if not sleeves:
        return {}

    total_weight = sum(weight for _, weight, _ in sleeves)
    if total_weight <= 0:
        return {}

    deployable = min(surplus, sum(headroom for _, _, headroom in sleeves))
    if deployable < min_surplus_usd:
        return {}

    extras: dict[str, float] = {}
    remaining = deployable
    for sleeve_id, weight, headroom in sleeves:
        share = deployable * (weight / total_weight)
        amount = min(share, headroom, remaining)
        if amount >= 10.0:
            extras[sleeve_id] = round(amount, 2)
            remaining -= amount
    return extras


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
