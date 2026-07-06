from types import SimpleNamespace

from src.portfolio_sleeves import trim_candidates_to_sleeve_budget
from src.rank_buy_allocator import (
    SKIP_RANK_TOP_K_REASON,
    apply_rank_top_k_new_buy_selection,
    max_rank_new_buys_per_run,
    rank_buy_top_k_enabled,
    select_rank_top_k_new_buy_tickers,
    sort_approved_buys_for_execution,
)


def _settings(**overrides):
    values = {
        "rank_ai_buy_gate_enabled": True,
        "rank_ai_buy_top_k_enabled": True,
        "max_orders_per_run": 2,
        "max_total_positions": 12,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_select_rank_top_k_new_buy_tickers_orders_by_percentile():
    rows = [
        {"ticker": "SHOP", "is_new_position": True, "rank_ai_percentile": 0.853},
        {"ticker": "RBLX", "is_new_position": True, "rank_ai_percentile": 0.992},
        {"ticker": "ADBE", "is_new_position": True, "rank_ai_percentile": 0.876},
    ]
    selected = select_rank_top_k_new_buy_tickers(rows, max_select=2)
    assert selected == {"RBLX", "ADBE"}


def test_apply_rank_top_k_keeps_add_on_buys():
    settings = _settings(max_orders_per_run=1)
    approved = [
        {
            "ticker": "RBLX",
            "is_new_position": True,
            "rank_ai_percentile": 0.99,
            "risk_reason": "ok",
        },
        {
            "ticker": "SHOP",
            "is_new_position": True,
            "rank_ai_percentile": 0.85,
            "risk_reason": "ok",
        },
        {
            "ticker": "AVGO",
            "is_new_position": False,
            "rank_ai_percentile": 0.70,
            "risk_reason": "add",
        },
    ]
    kept, skipped = apply_rank_top_k_new_buy_selection(
        approved,
        settings=settings,
        meaningful_positions_count=5,
    )
    kept_tickers = {row["ticker"] for row in kept}
    skipped_tickers = {row["ticker"] for row in skipped}
    assert kept_tickers == {"RBLX", "AVGO"}
    assert skipped_tickers == {"SHOP"}
    assert SKIP_RANK_TOP_K_REASON in skipped[0]["risk_reason"]


def test_rank_buy_top_k_disabled_when_gate_off():
    settings = _settings(rank_ai_buy_gate_enabled=False)
    assert not rank_buy_top_k_enabled(settings)


def test_sort_approved_buys_for_execution_by_rank_percentile():
    settings = _settings()
    rows = [
        {"ticker": "RBLX", "rank_ai_percentile": 0.894, "order_amount": 19278.0},
        {"ticker": "NEM", "rank_ai_percentile": 0.854, "order_amount": 19278.0},
        {"ticker": "AMC", "rank_ai_percentile": 1.0, "order_amount": 15502.0},
    ]
    ordered = sort_approved_buys_for_execution(rows, settings=settings)
    assert [row["ticker"] for row in ordered] == ["AMC", "RBLX", "NEM"]


def test_sort_then_trim_prefers_highest_rank_under_budget():
    settings = _settings()
    rows = sort_approved_buys_for_execution(
        [
            {"ticker": "RBLX", "rank_ai_percentile": 0.894, "order_amount": 19278.0},
            {"ticker": "NEM", "rank_ai_percentile": 0.854, "order_amount": 19278.0},
            {"ticker": "AMC", "rank_ai_percentile": 1.0, "order_amount": 15502.0},
        ],
        settings=settings,
    )
    trimmed, _ = trim_candidates_to_sleeve_budget(rows, 27868.9)
    tickers = [row["ticker"] for row in trimmed]
    assert tickers == ["AMC", "RBLX"]
    assert trimmed[0]["order_amount"] == 15502.0
    assert trimmed[1]["order_amount"] == 27868.9 - 15502.0


def test_max_rank_new_buys_respects_slots_and_orders():
    settings = _settings(max_orders_per_run=6, max_total_positions=12)
    assert max_rank_new_buys_per_run(settings, meaningful_positions_count=10) == 2
    assert max_rank_new_buys_per_run(settings, meaningful_positions_count=5) == 6
