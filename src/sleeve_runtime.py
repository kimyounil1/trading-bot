"""Runtime sleeve context for main.py buy execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from src.portfolio_sleeves import (
    CORE_SLEEVE_ID,
    PortfolioSleeveAllocator,
    PortfolioSleeveSnapshot,
    sleeve_fields_for_audit,
    sleeves_enabled,
    trim_candidates_to_sleeve_budget,
    validate_sleeve_open_order_budget,
)


@dataclass
class SleeveRunContext:
    settings: Any
    allocator: PortfolioSleeveAllocator
    snapshot: PortfolioSleeveSnapshot
    open_orders: list[dict[str, Any]]
    recon_ok: bool = True
    recon_reason: str = ""
    core_budget_remaining: Optional[float] = None

    @property
    def enabled(self) -> bool:
        return sleeves_enabled(self.settings)

    def audit_fields(
        self,
        *,
        budget_before: float | None = None,
        budget_after: float | None = None,
    ) -> dict[str, Any]:
        if not self.enabled:
            return {}
        return sleeve_fields_for_audit(
            self.snapshot,
            sleeve_id=CORE_SLEEVE_ID,
            budget_before=budget_before,
            budget_after=budget_after,
        )

    def apply_pre_candidate_gate(
        self,
        *,
        risk_allowed: bool,
        risk_reason: str,
        target_amount: float,
        order_amount: float,
    ) -> tuple[bool, str, float, float]:
        if not self.enabled:
            return risk_allowed, risk_reason, target_amount, order_amount
        if not self.recon_ok:
            return False, self.recon_reason, 0.0, 0.0
        if self.core_budget_remaining is not None and self.core_budget_remaining <= 0:
            return False, "core sleeve budget exhausted for this run", target_amount, 0.0
        return risk_allowed, risk_reason, target_amount, order_amount

    def trim_approved_buys(
        self,
        approved_buys: list[dict[str, Any]],
        *,
        min_amount: float = 10.0,
    ) -> list[dict[str, Any]]:
        if not self.enabled or not approved_buys:
            return approved_buys
        initial_core_budget = self.allocator.order_budget_for(CORE_SLEEVE_ID)
        before_count = len(approved_buys)
        trimmed, remaining = trim_candidates_to_sleeve_budget(
            approved_buys,
            initial_core_budget,
            min_amount=min_amount,
        )
        self.core_budget_remaining = remaining
        if len(trimmed) != before_count:
            print(
                "Portfolio sleeves: trimmed "
                f"{before_count - len(trimmed)} buy candidate(s) to fit "
                f"core budget (${initial_core_budget:.2f})"
            )
        return trimmed

    def check_submit_budget(self, order_amount: float) -> tuple[bool, str]:
        if not self.enabled or self.core_budget_remaining is None:
            return True, ""
        if order_amount > self.core_budget_remaining + 1e-6:
            return False, (
                f"core sleeve budget exhausted "
                f"(${self.core_budget_remaining:.2f} remaining)"
            )
        return True, ""

    def consume_submit_budget(self, order_amount: float) -> None:
        if self.core_budget_remaining is None:
            return
        self.core_budget_remaining = max(0.0, self.core_budget_remaining - order_amount)

    def buy_intent_sleeve_kwargs(
        self,
        order_amount: float,
        *,
        budget_before_submit: float | None,
    ) -> dict[str, Any]:
        if not self.enabled:
            return {
                "sleeve_id": CORE_SLEEVE_ID,
                "sleeve_strategy": "current_core",
                "sleeve_target_weight": None,
                "sleeve_budget_before": None,
                "sleeve_budget_after": None,
                "sleeve_risk_mode": "",
            }
        core = self.snapshot.sleeves.get(CORE_SLEEVE_ID)
        before = budget_before_submit
        return {
            "sleeve_id": CORE_SLEEVE_ID,
            "sleeve_strategy": core.strategy if core else "current_core",
            "sleeve_target_weight": core.target_weight if core else None,
            "sleeve_budget_before": before,
            "sleeve_budget_after": max(0.0, float(before or 0.0) - order_amount),
            "sleeve_risk_mode": core.risk_mode if core else "",
        }


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

    allocator = PortfolioSleeveAllocator(
        settings,
        account=account,
        positions=positions,
        open_orders=open_orders,
    )
    snapshot = allocator.build_snapshot()
    recon_ok = True
    recon_reason = ""
    if sleeves_enabled(settings):
        recon_ok, recon_reason = validate_sleeve_open_order_budget(snapshot, open_orders)
        sleeve_budgets = {
            sleeve_id: round(budget.order_budget, 2)
            for sleeve_id, budget in snapshot.sleeves.items()
        }
        print(f"Portfolio sleeves enabled: order_budgets={sleeve_budgets}")
        if not recon_ok:
            print(f"SLEEVE_RECONCILIATION_NO_GO: {recon_reason}")

    core_budget_remaining = (
        allocator.order_budget_for(CORE_SLEEVE_ID) if sleeves_enabled(settings) else None
    )
    return SleeveRunContext(
        settings=settings,
        allocator=allocator,
        snapshot=snapshot,
        open_orders=open_orders,
        recon_ok=recon_ok,
        recon_reason=recon_reason,
        core_budget_remaining=core_budget_remaining,
    )
