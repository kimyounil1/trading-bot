"""Runtime sleeve context for trading pipelines."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from src.portfolio_sleeves import (
    CORE_SLEEVE_ID,
    TOURNAMENT_SLEEVE_ID,
    PortfolioSleeveAllocator,
    PortfolioSleeveSnapshot,
    sleeve_fields_for_audit,
    sleeves_enabled,
    trim_candidates_to_sleeve_budget,
    validate_sleeve_open_order_budget,
)
from src.sleeve_position_registry import (
    bootstrap_open_positions,
    load_sleeve_position_map,
    tag_symbol,
    untag_symbol,
)


@dataclass
class SleeveRunContext:
    settings: Any
    allocator: PortfolioSleeveAllocator
    snapshot: PortfolioSleeveSnapshot
    open_orders: list[dict[str, Any]]
    sleeve_position_map: dict[str, str] = field(default_factory=dict)
    recon_ok: bool = True
    recon_reason: str = ""
    budget_remaining: dict[str, float] = field(default_factory=dict)

    @property
    def enabled(self) -> bool:
        return sleeves_enabled(self.settings)

    @property
    def core_budget_remaining(self) -> Optional[float]:
        return self.budget_remaining.get(CORE_SLEEVE_ID)

    def refresh_snapshot(self) -> None:
        self.snapshot = self.allocator.build_snapshot()

    def audit_fields(
        self,
        *,
        sleeve_id: str = CORE_SLEEVE_ID,
        budget_before: float | None = None,
        budget_after: float | None = None,
    ) -> dict[str, Any]:
        if not self.enabled:
            return {}
        return sleeve_fields_for_audit(
            self.snapshot,
            sleeve_id=sleeve_id,
            budget_before=budget_before,
            budget_after=budget_after,
        )

    def apply_pre_candidate_gate(
        self,
        *,
        sleeve_id: str = CORE_SLEEVE_ID,
        risk_allowed: bool,
        risk_reason: str,
        target_amount: float,
        order_amount: float,
    ) -> tuple[bool, str, float, float]:
        if not self.enabled:
            return risk_allowed, risk_reason, target_amount, order_amount
        if not self.recon_ok:
            return False, self.recon_reason, 0.0, 0.0
        remaining = self.budget_remaining.get(str(sleeve_id).lower())
        if remaining is not None and remaining <= 0:
            return (
                False,
                f"{sleeve_id} sleeve budget exhausted for this run",
                target_amount,
                0.0,
            )
        return risk_allowed, risk_reason, target_amount, order_amount

    def trim_approved_buys(
        self,
        approved_buys: list[dict[str, Any]],
        *,
        sleeve_id: str = CORE_SLEEVE_ID,
        min_amount: float = 10.0,
    ) -> list[dict[str, Any]]:
        if not self.enabled or not approved_buys:
            return approved_buys
        sleeve_key = str(sleeve_id).lower()
        initial_budget = self.allocator.order_budget_for(sleeve_key)
        before_count = len(approved_buys)
        trimmed, remaining = trim_candidates_to_sleeve_budget(
            approved_buys,
            initial_budget,
            min_amount=min_amount,
        )
        self.budget_remaining[sleeve_key] = remaining
        if len(trimmed) != before_count:
            print(
                f"Portfolio sleeves: trimmed {before_count - len(trimmed)} "
                f"{sleeve_key} buy candidate(s) to fit budget (${initial_budget:.2f})"
            )
        return trimmed

    def check_submit_budget(
        self,
        order_amount: float,
        *,
        sleeve_id: str = CORE_SLEEVE_ID,
    ) -> tuple[bool, str]:
        if not self.enabled:
            return True, ""
        sleeve_key = str(sleeve_id).lower()
        remaining = self.budget_remaining.get(sleeve_key)
        if remaining is None:
            return True, ""
        if order_amount > remaining + 1e-6:
            return (
                False,
                f"{sleeve_key} sleeve budget exhausted (${remaining:.2f} remaining)",
            )
        return True, ""

    def consume_submit_budget(
        self,
        order_amount: float,
        *,
        sleeve_id: str = CORE_SLEEVE_ID,
    ) -> None:
        sleeve_key = str(sleeve_id).lower()
        if sleeve_key not in self.budget_remaining:
            return
        self.budget_remaining[sleeve_key] = max(
            0.0,
            self.budget_remaining[sleeve_key] - order_amount,
        )

    def buy_intent_sleeve_kwargs(
        self,
        order_amount: float,
        *,
        sleeve_id: str = CORE_SLEEVE_ID,
        budget_before_submit: float | None,
    ) -> dict[str, Any]:
        sleeve_key = str(sleeve_id).lower()
        if not self.enabled:
            return {
                "sleeve_id": sleeve_key,
                "sleeve_strategy": "current_core",
                "sleeve_target_weight": None,
                "sleeve_budget_before": None,
                "sleeve_budget_after": None,
                "sleeve_risk_mode": "",
            }
        sleeve = self.snapshot.sleeves.get(sleeve_key)
        before = budget_before_submit
        return {
            "sleeve_id": sleeve_key,
            "sleeve_strategy": sleeve.strategy if sleeve else sleeve_key,
            "sleeve_target_weight": sleeve.target_weight if sleeve else None,
            "sleeve_budget_before": before,
            "sleeve_budget_after": max(0.0, float(before or 0.0) - order_amount),
            "sleeve_risk_mode": sleeve.risk_mode if sleeve else "",
        }

    def record_fill(self, ticker: str, *, sleeve_id: str) -> None:
        tag_symbol(str(ticker).upper(), str(sleeve_id).lower())
        self.sleeve_position_map[str(ticker).upper()] = str(sleeve_id).lower()

    def record_exit(self, ticker: str) -> None:
        symbol = str(ticker).upper()
        untag_symbol(symbol)
        self.sleeve_position_map.pop(symbol, None)


def init_sleeve_run_context(
    settings: Any,
    *,
    broker_adapter: Any,
    account: dict[str, Any],
    positions: list[dict[str, Any]],
) -> SleeveRunContext:
    open_orders: list[dict[str, Any]] = []
    try:
        open_orders = broker_adapter.get_open_orders()
    except Exception as exc:
        print(f"Warning: open orders unavailable for sleeve allocator: {exc}")

    open_symbols = {
        str(position.get("symbol", "")).upper()
        for position in positions
        if position.get("symbol")
    }
    if sleeves_enabled(settings):
        sleeve_position_map = bootstrap_open_positions(open_symbols)
    else:
        sleeve_position_map = load_sleeve_position_map()

    allocator = PortfolioSleeveAllocator(
        settings,
        account=account,
        positions=positions,
        open_orders=open_orders,
        sleeve_position_map=sleeve_position_map,
    )
    snapshot = allocator.build_snapshot()
    recon_ok = True
    recon_reason = ""
    budget_remaining: dict[str, float] = {}

    if sleeves_enabled(settings):
        recon_ok, recon_reason = validate_sleeve_open_order_budget(snapshot, open_orders)
        sleeve_budgets = {
            sleeve_id: round(budget.order_budget, 2)
            for sleeve_id, budget in snapshot.sleeves.items()
        }
        print(f"Portfolio sleeves enabled: order_budgets={sleeve_budgets}")
        if not recon_ok:
            print(f"SLEEVE_RECONCILIATION_NO_GO: {recon_reason}")
        for sleeve_id, budget in snapshot.sleeves.items():
            if sleeve_id == "cash":
                continue
            budget_remaining[sleeve_id] = float(budget.order_budget)

    return SleeveRunContext(
        settings=settings,
        allocator=allocator,
        snapshot=snapshot,
        open_orders=open_orders,
        sleeve_position_map=dict(sleeve_position_map),
        recon_ok=recon_ok,
        recon_reason=recon_reason,
        budget_remaining=budget_remaining,
    )
