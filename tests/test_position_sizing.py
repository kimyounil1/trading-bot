from types import SimpleNamespace

from src.position_sizing import (
    cap_single_order_amount,
    conviction_adjustments,
    daily_order_budget,
    max_deployable_cash,
)


def test_conviction_boosts_position_and_lowers_cash_buffer():
    settings = SimpleNamespace(
        conviction_sizing_enabled=True,
        use_ai_score=True,
        ai_score_buy_threshold=0.4,
        conviction_ai_score_strong=0.6,
        conviction_position_mult_max=1.3,
        conviction_cash_buffer_mult_min=0.4,
        min_cash_buffer_pct=0.05,
    )
    adj = conviction_adjustments(settings, 0.6)
    assert adj.position_mult == 1.3
    assert adj.cash_buffer_mult == 0.4


def test_cap_single_order_pct_not_legacy_dollar():
    settings = SimpleNamespace(
        max_single_order_pct=0.25,
        max_test_order_amount=0.0,
    )
    assert cap_single_order_amount(5000.0, 10000.0, settings) == 2500.0


def test_daily_order_budget_prefers_pct():
    settings = SimpleNamespace(
        max_daily_order_pct=0.30,
        max_daily_order_amount=1000.0,
    )
    assert daily_order_budget(20000.0, settings) == 6000.0


def test_max_deployable_cash_respects_conviction_buffer():
    settings = SimpleNamespace(min_cash_buffer_pct=0.10)
    deployable = max_deployable_cash(
        cash=1000.0,
        portfolio_value=10000.0,
        settings=settings,
        cash_buffer_mult=0.5,
    )
    assert deployable == 500.0
