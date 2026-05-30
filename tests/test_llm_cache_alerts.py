"""LLM cache alert evaluation ([AGY])."""

from src.llm_cache_report import evaluate_llm_cache_alerts, summarize_llm_cache


def test_llm_cache_alerts_fail_low_hit_rate():
    report = summarize_llm_cache(
        {
            "AAPL_2026-05-28": {"is_approved": True},
            "MSFT_2026-05-29": {"is_approved": False},
            "GOOG_2026-05-30": {"is_approved": True},
        }
    )
    alerts = evaluate_llm_cache_alerts(
        report,
        config={"min_cache_hit_rate": 0.99, "max_entries_per_ticker_day": 2.0},
    )
    assert alerts["passed"] is False


def test_llm_cache_alerts_pass_reasonable_cache():
    report = summarize_llm_cache(
        {
            "AAPL_2026-05-28": {"is_approved": True},
            "AAPL_2026-05-29": {"is_approved": True},
        }
    )
    alerts = evaluate_llm_cache_alerts(
        report,
        config={"min_cache_hit_rate": 0.3, "max_entries_per_ticker_day": 1.5},
    )
    assert alerts["passed"] is True
