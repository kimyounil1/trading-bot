import unittest
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

from src.buy_guards import (
    apply_shared_buy_guards,
    execution_label_for_cache,
)


class TestBuyGuards(unittest.TestCase):
    def test_execution_label_daily_limit(self) -> None:
        label, would = execution_label_for_cache(
            risk_allowed=False,
            reason="daily order amount limit reached",
            dry_run_orders_count=0,
            max_orders_per_run=3,
            orders_allowed=True,
        )
        self.assertEqual(label, "SKIP_DAILY_LIMIT")
        self.assertFalse(would)

    def test_execution_label_would_submit(self) -> None:
        label, would = execution_label_for_cache(
            risk_allowed=True,
            reason="buy safety limits passed",
            dry_run_orders_count=0,
            max_orders_per_run=3,
            orders_allowed=True,
        )
        self.assertEqual(label, "WOULD_SUBMIT_IF_EXECUTED")
        self.assertTrue(would)

    @patch("src.buy_guards.evaluate_ticker_consensus", return_value=(True, "ok"))
    @patch("src.buy_guards.get_ticker_sentiment", return_value=-0.9)
    def test_news_sentiment_blocks(self, _sentiment, _llm) -> None:
        settings = SimpleNamespace(
            news_sentiment_enabled=True,
            news_sentiment_threshold=-0.3,
            llm_advisory_only=True,
        )
        result = apply_shared_buy_guards(
            ticker="AAPL",
            position=None,
            settings=settings,
            risk_allowed=True,
            risk_reason="ok",
            target_amount=100.0,
            ai_score=0.8,
            open_symbols=set(),
            ticker_data={},
            vix_df=None,
            llm_cache_only=True,
        )
        self.assertFalse(result.risk_allowed)
        self.assertIn("negative news sentiment", result.risk_reason)


class TestCandidateCacheMeta(unittest.TestCase):
    def test_build_meta_includes_extended_hours_fields(self) -> None:
        from src.candidate_cache import build_candidate_cache

        with patch("src.candidate_cache.get_market_clock") as mock_clock, patch(
            "src.candidate_cache.get_account_summary"
        ) as mock_account, patch(
            "src.candidate_cache.get_positions_summary", return_value=[]
        ), patch(
            "src.candidate_cache._resolve_watchlist_tickers", return_value=(["AAPL"], None)
        ), patch(
            "src.candidate_cache._load_cache_ticker_data", return_value={}
        ), patch(
            "src.candidate_cache.build_data_quality_rows",
            return_value=(
                pd.DataFrame(columns=["ticker", "rows", "data_status", "reason"]),
                pd.DataFrame(columns=["ticker", "data_status", "reason"]),
            ),
        ), patch(
            "src.candidate_cache.load_macro_data", return_value=None
        ):
            mock_account.return_value = {
                "cash": 10000.0,
                "portfolio_value": 10000.0,
                "positions_count": 0,
                "buying_power": 10000.0,
            }
            mock_clock.return_value = SimpleNamespace(
                orders_allowed=True,
                session=SimpleNamespace(value="regular"),
                broker_provider="alpaca",
                extended_hours_enabled=True,
                is_open=True,
                timestamp="2026-06-01T14:00:00Z",
                next_open=None,
                next_close=None,
            )
            meta, buy_df, exit_df, quality_df, errors_df = build_candidate_cache()

        self.assertIn("orders_allowed", meta)
        self.assertIn("trading_session", meta)
        self.assertIn("extended_hours_enabled", meta)
        self.assertTrue(meta["extended_hours_enabled"])


if __name__ == "__main__":
    unittest.main()
