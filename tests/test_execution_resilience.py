import unittest
from unittest.mock import patch, MagicMock
from types import SimpleNamespace
from src.alpaca_client import submit_market_buy_notional_order, close_position_by_symbol
from src.llm_analyst import evaluate_ticker_consensus
from src.settings import StrategySettings
import json
from pathlib import Path

class TestExecutionResilience(unittest.TestCase):
    @patch("src.alpaca_client.get_trading_client")
    def test_idempotency_buy_order(self, mock_get_client):
        mock_client = mock_get_client.return_value
        
        ticker = "AAPL"
        notional = 100.0
        client_order_id = "test_buy_id"
        
        submit_market_buy_notional_order(ticker, notional, client_order_id=client_order_id)
        
        # Verify that client_order_id was passed to MarketOrderRequest
        args, kwargs = mock_client.submit_order.call_args
        request = kwargs["order_data"]
        self.assertEqual(request.client_order_id, client_order_id)
        self.assertEqual(request.symbol, ticker)

    @patch("src.alpaca_client.get_trading_client")
    def test_idempotent_close_position(self, mock_get_client):
        mock_client = mock_get_client.return_value
        # Mock position
        mock_client.get_open_position.return_value = SimpleNamespace(qty="10.5")
        
        ticker = "AAPL"
        client_order_id = "test_exit_id"
        
        close_position_by_symbol(ticker, client_order_id=client_order_id)
        
        # Should call submit_order instead of close_position when client_order_id is present
        mock_client.submit_order.assert_called_once()
        args, kwargs = mock_client.submit_order.call_args
        request = kwargs["order_data"]
        self.assertEqual(request.client_order_id, client_order_id)
        self.assertEqual(float(request.qty), 10.5)
        self.assertEqual(request.side.value, "sell")

    @patch("src.llm_analyst.GEMINI_API_KEY", "test-key")
    @patch("src.llm_analyst._load_cache")
    @patch("src.llm_analyst._save_cache")
    @patch("src.llm_analyst._headlines_before_date")
    @patch("src.llm_analyst._generate_llm_text_with_provider")
    def test_llm_caching(self, mock_generate, mock_headlines, mock_save, mock_load):
        mock_load.return_value = {}
        mock_headlines.return_value = ["Good News"]
        mock_generate.return_value = (
            "DECISION: APPROVE\nCATEGORY: None\nREASON: All good",
            "gemini",
        )

        ticker = "AAPL"
        as_of = "2026-06-01"

        ok1, reason1 = evaluate_ticker_consensus(ticker, as_of_date=as_of)
        self.assertTrue(ok1)
        mock_generate.assert_called_once()
        mock_save.assert_called_once()

        cache_data = mock_save.call_args[0][0]
        mock_load.return_value = cache_data

        ok2, reason2 = evaluate_ticker_consensus(ticker, as_of_date=as_of)
        self.assertTrue(ok2)
        self.assertEqual(reason1, reason2)
        mock_generate.assert_called_once()

    @patch("src.llm_analyst.GEMINI_API_KEY", "test-key")
    @patch("src.llm_analyst._generate_llm_text_with_provider")
    @patch("src.llm_analyst._headlines_before_date")
    def test_llm_degraded_mode_fail(self, mock_headlines, mock_generate):
        mock_headlines.return_value = ["Breaking: market halt"]
        mock_generate.side_effect = Exception("API Down")

        settings = SimpleNamespace(llm_degraded_mode="FAIL", llm_cache_enabled=False)

        ok, reason = evaluate_ticker_consensus("AAPL", settings=settings)
        self.assertFalse(ok)
        self.assertIn("Auto-Rejected", reason)

    @patch("src.llm_analyst.GEMINI_API_KEY", "test-key")
    @patch("src.llm_analyst._generate_llm_text_with_provider")
    @patch("src.llm_analyst._headlines_before_date")
    def test_llm_degraded_mode_pass(self, mock_headlines, mock_generate):
        mock_headlines.return_value = ["Breaking: API timeout"]
        mock_generate.side_effect = Exception("Gemini/YFinance Timeout")

        settings = SimpleNamespace(llm_degraded_mode="PASS", llm_cache_enabled=False)

        ok, reason = evaluate_ticker_consensus("AAPL", settings=settings)
        self.assertTrue(ok)
        self.assertIn("Auto-Approved", reason)

    def test_corrupted_peaks_json(self):
        import tempfile
        from pathlib import Path
        from src.main import _load_peaks
        import src.main
        
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_file = Path(tmpdir) / "trailing_peaks.json"
            
            orig_path = src.main.PEAKS_PATH
            src.main.PEAKS_PATH = temp_file
            
            try:
                # Write corrupted JSON
                temp_file.write_text("invalid json format {", encoding="utf-8")
                
                # Load peaks (should handle error, quarantine file, and return empty dict)
                peaks = _load_peaks()
                self.assertEqual(peaks, {})
                
                # Verify quarantine
                corrupt_file = temp_file.with_suffix(".json.corrupt")
                self.assertTrue(corrupt_file.exists())
                self.assertFalse(temp_file.exists())
            finally:
                src.main.PEAKS_PATH = orig_path

    def test_empty_dataframe_handling(self):
        import pandas as pd
        from src.main import _check_price_frame_freshness
        from types import SimpleNamespace
        
        market_clock = SimpleNamespace(is_open=True, timestamp=pd.Timestamp("2026-05-29 10:00:00"))
        
        # 1. None dataframe
        fresh, reason = _check_price_frame_freshness(None, market_clock)
        self.assertFalse(fresh)
        self.assertEqual(reason, "price data is empty")
        
        # 2. Empty DataFrame
        df_empty = pd.DataFrame()
        fresh, reason = _check_price_frame_freshness(df_empty, market_clock)
        self.assertFalse(fresh)
        self.assertEqual(reason, "price data is empty")
        
        # 3. Missing date column
        df_no_date = pd.DataFrame({"close": [100.0]})
        fresh, reason = _check_price_frame_freshness(df_no_date, market_clock)
        self.assertFalse(fresh)
        self.assertEqual(reason, "price data missing date column")
        
        # 4. Invalid dates
        df_invalid_date = pd.DataFrame({"date": ["not-a-date"], "close": [100.0]})
        fresh, reason = _check_price_frame_freshness(df_invalid_date, market_clock)
        self.assertFalse(fresh)
        self.assertEqual(reason, "price data has no valid dates")

    @patch("src.main.get_broker_adapter")
    @patch("src.main.notify_error")
    def test_alpaca_timeout_failure_stops_execution(self, mock_notify, mock_get_broker):
        from src.main import main
        from argparse import Namespace
        
        broker = MagicMock()
        broker.get_account.side_effect = ConnectionError("Alpaca Connection Timeout")
        mock_get_broker.return_value = broker
        
        # Set execute mode to True so it fails safe instead of fallback
        with patch("src.main.parse_args") as mock_args, \
             patch("src.main.load_settings") as mock_settings:
            
            mock_args.return_value = Namespace(execute=True)
            mock_settings.return_value = StrategySettings(
                tickers=["AAPL"],
                broker_provider="alpaca",
                dynamic_universe_enabled=False,
                sector_rotation_enabled=False,
                use_ai_score=False,
                market_regime_filter_enabled=False,
            )
            
            # Should raise ConnectionError
            with self.assertRaises(ConnectionError):
                main()

if __name__ == "__main__":
    unittest.main()
