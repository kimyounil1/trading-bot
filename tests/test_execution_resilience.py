import unittest
from unittest.mock import patch, MagicMock
from types import SimpleNamespace
from src.alpaca_client import submit_market_buy_notional_order, close_position_by_symbol
from src.llm_analyst import evaluate_ticker_consensus
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

    @patch("src.llm_analyst._load_cache")
    @patch("src.llm_analyst._save_cache")
    @patch("yfinance.Ticker")
    @patch("google.generativeai.GenerativeModel")
    def test_llm_caching(self, mock_model, mock_yf, mock_save, mock_load):
        # Mock cache empty
        mock_load.return_value = {}
        
        # Mock news and LLM
        mock_yf.return_value.news = [{"title": "Good News"}]
        mock_resp = MagicMock()
        mock_resp.text = "DECISION: APPROVE\nCATEGORY: None\nREASON: All good"
        mock_model.return_value.generate_content.return_value = mock_resp
        
        ticker = "AAPL"
        
        # First call: should call LLM
        ok1, reason1 = evaluate_ticker_consensus(ticker)
        self.assertTrue(ok1)
        mock_model.return_value.generate_content.assert_called_once()
        mock_save.assert_called_once()
        
        # Update mock_load to simulate saved cache
        cache_data = mock_save.call_args[0][0]
        mock_load.return_value = cache_data
        
        # Second call: should use cache
        ok2, reason2 = evaluate_ticker_consensus(ticker)
        self.assertTrue(ok2)
        self.assertEqual(reason1, reason2)
        # Should NOT call LLM again
        mock_model.return_value.generate_content.assert_called_once()

    @patch("src.llm_analyst.genai.GenerativeModel")
    @patch("yfinance.Ticker")
    def test_llm_degraded_mode_fail(self, mock_yf, mock_model):
        # Force exception
        mock_yf.side_effect = Exception("API Down")
        
        settings = SimpleNamespace(llm_degraded_mode="FAIL", llm_cache_enabled=False)
        
        ok, reason = evaluate_ticker_consensus("AAPL", settings=settings)
        self.assertFalse(ok)
        self.assertIn("Auto-Rejected", reason)

if __name__ == "__main__":
    unittest.main()
