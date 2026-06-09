from types import SimpleNamespace

from src.portfolio_sleeves import (
    CORE_SLEEVE_ID,
    CASH_SLEEVE_ID,
    TOURNAMENT_SLEEVE_ID,
    PortfolioSleeveSnapshot,
    SleeveBudget,
    compute_sleeve_cash_surplus_deploy,
)
from src.sleeve_runtime import SleeveRunContext


def _snapshot(*, cash: float, core_mv: float, tour_mv: float, pv: float = 100_000.0):
    cash_target = pv * 0.20
    return PortfolioSleeveSnapshot(
        enabled=True,
        portfolio_value=pv,
        account_cash=cash,
        buying_power=cash,
        implicit_cash_weight=0.0,
        sleeves={
            CORE_SLEEVE_ID: SleeveBudget(
                sleeve_id=CORE_SLEEVE_ID,
                strategy="core",
                target_weight=0.50,
                target_notional=pv * 0.50,
                current_notional=core_mv,
                available_cash=0.0,
                order_budget=100.0,
                open_order_reserved=0.0,
                rebalance_needed=False,
            ),
            TOURNAMENT_SLEEVE_ID: SleeveBudget(
                sleeve_id=TOURNAMENT_SLEEVE_ID,
                strategy="tournament",
                target_weight=0.30,
                target_notional=pv * 0.30,
                current_notional=tour_mv,
                available_cash=0.0,
                order_budget=100.0,
                open_order_reserved=0.0,
                rebalance_needed=False,
            ),
            CASH_SLEEVE_ID: SleeveBudget(
                sleeve_id=CASH_SLEEVE_ID,
                strategy="cash",
                target_weight=0.20,
                target_notional=cash_target,
                current_notional=0.0,
                available_cash=cash,
                order_budget=0.0,
                open_order_reserved=0.0,
                rebalance_needed=False,
            ),
        },
    )


def test_compute_cash_surplus_deploy_splits_by_weight():
    snap = _snapshot(cash=50_000.0, core_mv=20_000.0, tour_mv=10_000.0)
    extras = compute_sleeve_cash_surplus_deploy(snap, min_surplus_usd=50.0)
    assert CORE_SLEEVE_ID in extras
    assert TOURNAMENT_SLEEVE_ID in extras
    assert extras[CORE_SLEEVE_ID] > extras[TOURNAMENT_SLEEVE_ID]


def test_compute_cash_surplus_deploy_skips_when_within_target():
    snap = _snapshot(cash=20_000.0, core_mv=40_000.0, tour_mv=30_000.0)
    assert compute_sleeve_cash_surplus_deploy(snap) == {}


def test_sleeve_run_context_apply_cash_surplus():
    snap = _snapshot(cash=50_000.0, core_mv=20_000.0, tour_mv=10_000.0)
    ctx = SleeveRunContext(
        settings=SimpleNamespace(portfolio_sleeves_enabled=True),
        allocator=object(),
        snapshot=snap,
        open_orders=[],
        budget_remaining={CORE_SLEEVE_ID: 100.0, TOURNAMENT_SLEEVE_ID: 50.0},
        recon_ok=True,
    )
    extras = ctx.apply_cash_surplus_deploy(min_surplus_usd=50.0)
    assert extras
    assert ctx.budget_remaining[CORE_SLEEVE_ID] > 100.0
    assert ctx.budget_remaining[TOURNAMENT_SLEEVE_ID] > 50.0
