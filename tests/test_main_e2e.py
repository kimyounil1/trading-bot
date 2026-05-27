import unittest
from unittest.mock import patch, MagicMock, mock_open
from argparse import Namespace
from datetime import datetime, timezone
from types import SimpleNamespace
import pandas as pd
import numpy as np

from src.main import main
from src.settings import StrategySettings

class TestMainE2E(unittest.TestCase):
    def setUp(self):
        # Common mock data
        self.settings = StrategySettings(
            tickers=["AAPL"],
            ma_fast=10,
            ma_slow=50,
            rsi_buy_limit=65,
            max_position_pct=0.1,
            max_total_positions=5,
            stop_loss_pct=0.05,
            take_profit_pct=0.1,
            trailing_stop_pct=0.05,
            max_test_order_amount=100.0,
            max_holding_days=30,
            use_ai_score=True,
            ai_score_buy_threshold=0.5,
            correlation_guard_enabled=False,
            macro_event_risk_enabled=False,
            adaptive_trailing_stop_enabled=False
        )
        
        # Sample price data that generates a BUY signal
        # ma_fast > ma_slow, rsi < buy_limit
        rows = 100
        values = np.linspace(100, 150, rows)
        self.buy_frame = pd.DataFrame({
            "date": pd.date_range(end="2026-05-26", periods=rows),
            "open": values, "high": values + 2, "low": values - 1, "close": values + 1,
            "adj_close": values + 1, "volume": 1000000
        })

    @patch("src.main.parse_args")
    @patch("src.main.load_settings")
    @patch("src.main.apply_dynamic_profile")
    @patch("src.main.get_market_clock")
    @patch("src.main.get_account_summary")
    @patch("src.main.get_open_symbols")
    @patch("src.main.get_positions_summary")
    @patch("src.main.load_price_data_batch")
    @patch("src.main.get_signal_for_ticker")
    @patch("src.main.evaluate_ticker_consensus")
    @patch("src.main.submit_market_buy_notional_order")
    @patch("src.main.wait_for_order_status")
    @patch("src.main.notify_run_summary")
    @patch("src.main._load_peaks")
    @patch("src.main._save_peaks")
    @patch("src.main.get_position_entry_date")
    @patch("src.main._check_price_frame_freshness")
    @patch("src.main.is_earnings_window")
    @patch("src.main.is_sector_allowed")
    @patch("src.main.get_recent_buy_symbols")
    @patch("src.main.get_today_buy_notional")
    @patch("src.main.is_correlation_allowed")
    def test_full_buy_flow(self, mock_corr, mock_today, mock_recent, mock_sector, mock_earnings, mock_fresh, mock_entry, 
                          mock_save_peaks, mock_load_peaks, mock_notify, mock_wait, 
                          mock_submit, mock_llm, mock_signal, mock_load_data, 
                          mock_pos, mock_open_sym, mock_acc, mock_clock, 
                          mock_profile, mock_settings, mock_args):
        
        mock_args.return_value = Namespace(execute=True)
        self.settings.tickers = ["AAPL"]
        mock_settings.return_value = self.settings
        mock_profile.return_value = (self.settings, "TEST_PROFILE")
        
        mock_clock.return_value = SimpleNamespace(is_open=True, timestamp="2026-05-27T10:00:00Z", next_open=None)
        mock_acc.return_value = {"cash": 10000.0, "portfolio_value": 10000.0, "positions_count": 0, "buying_power": 20000.0}
        mock_open_sym.return_value = set()
        mock_pos.return_value = []
        mock_load_data.return_value = {"AAPL": pd.DataFrame(), "SPY": pd.DataFrame(), "^VIX": pd.DataFrame()}
        
        # Mock valid BUY signal
        mock_signal.return_value = ("BUY", {"close": 150.0, "ma20": 140.0, "ma50": 130.0, "rsi": 50.0}, 0.8)
        mock_fresh.return_value = (True, "")
        mock_llm.return_value = (True, "LLM Approved")
        mock_earnings.return_value = (False, "")
        mock_sector.return_value = (True, "")
        mock_corr.return_value = (True, "")
        mock_load_peaks.return_value = {}
        mock_recent.return_value = set()
        mock_today.return_value = 0.0
        
        mock_order = MagicMock()
        mock_order.id = "order_123"; mock_order.status = "ACCEPTED"; mock_order.side = "BUY"; mock_order.type = "MARKET"
        mock_submit.return_value = mock_order
        mock_wait.return_value = {"id": "order_123", "status": "FILLED", "side": "BUY", "type": "MARKET", "filled_qty": "1.0", "filled_avg_price": "150.0"}

        main()
        mock_submit.assert_called_once()
        print("E2E Buy Flow Verified")

    @patch("src.main.parse_args")
    @patch("src.main.load_settings")
    @patch("src.main.apply_dynamic_profile")
    @patch("src.main.get_market_clock")
    @patch("src.main.get_account_summary")
    @patch("src.main.get_open_symbols")
    @patch("src.main.get_positions_summary")
    @patch("src.main.load_price_data_batch")
    @patch("src.main.get_signal_for_ticker")
    @patch("src.main.get_position_entry_date")
    @patch("src.main.close_position_by_symbol")
    @patch("src.main.wait_for_order_status")
    @patch("src.main._load_peaks")
    @patch("src.main._check_price_frame_freshness")
    @patch("src.main.notify_run_summary")
    def test_exit_by_time_limit(self, mock_notify, mock_fresh, mock_load_peaks, mock_wait, mock_close, mock_entry, 
                               mock_signal, mock_load_data, mock_pos, mock_open_sym, mock_acc, mock_clock, 
                               mock_profile, mock_settings, mock_args):
        
        mock_args.return_value = Namespace(execute=True)
        self.settings.tickers = ["AAPL"]
        mock_settings.return_value = self.settings
        mock_profile.return_value = (self.settings, "TEST_PROFILE")
        
        mock_clock.return_value = SimpleNamespace(is_open=True, timestamp="2026-05-27T10:00:00Z")
        # Ensure positions is not empty
        positions_list = [{"symbol": "AAPL", "qty": 10, "current_price": 100.0, "market_value": 1000.0, "unrealized_plpc": 0.01}]
        mock_pos.return_value = positions_list
        mock_acc.return_value = {"cash": 5000.0, "portfolio_value": 10000.0, "positions_count": 1}
        mock_open_sym.return_value = {"AAPL"}
        mock_load_data.return_value = {"AAPL": pd.DataFrame(), "SPY": pd.DataFrame(), "^VIX": pd.DataFrame()}
        mock_fresh.return_value = (True, "")
        
        # Signal is HOLD but time is up
        mock_signal.return_value = ("HOLD", {"close": 100.0}, 0.5)
        
        # 31 days ago (exceeds 30 day limit)
        mock_entry.return_value = datetime.now(timezone.utc) - pd.Timedelta(days=31)
        mock_load_peaks.return_value = {"AAPL": 110.0}
        
        mock_order = MagicMock()
        mock_order.id = "exit_123"; mock_order.status = "ACCEPTED"; mock_order.side = "SELL"; mock_order.type = "MARKET"
        mock_close.return_value = mock_order
        mock_wait.return_value = {"id": "exit_123", "status": "FILLED", "side": "SELL", "type": "MARKET", "filled_qty": "10", "filled_avg_price": "100.0"}

        main()
        mock_close.assert_called_once()
        print("E2E Time-based Exit Verified")

    @patch("src.main.parse_args")
    @patch("src.main.load_settings")
    @patch("src.main.apply_dynamic_profile")
    @patch("src.main.get_market_clock")
    @patch("src.main.get_account_summary")
    @patch("src.main.get_open_symbols")
    @patch("src.main.get_positions_summary")
    @patch("src.main.load_price_data_batch")
    @patch("src.main.get_signal_for_ticker")
    @patch("src.main.close_position_by_symbol")
    @patch("src.main.wait_for_order_status")
    @patch("src.main._load_peaks")
    @patch("src.main._check_price_frame_freshness")
    @patch("src.main.notify_run_summary")
    def test_simultaneous_exit_and_trim(self, mock_notify, mock_fresh, mock_load_peaks, mock_wait, mock_close,
                                       mock_signal, mock_load_data, mock_pos, mock_open_sym, mock_acc, 
                                       mock_clock, mock_profile, mock_settings, mock_args):
        """Verify that Full Exit (Trailing Stop) takes precedence over Rebalance Trim."""
        mock_args.return_value = Namespace(execute=True)
        self.settings.tickers = ["AAPL"]
        # Target weight 10%, but position value is 2000/10000 = 20% -> should trim
        self.settings.max_position_pct = 0.1
        self.settings.rebalance_threshold_pct = 0.2
        mock_settings.return_value = self.settings
        mock_profile.return_value = (self.settings, "TEST_PROFILE")
        
        mock_clock.return_value = SimpleNamespace(is_open=True, timestamp="2026-05-27T10:00:00Z")
        mock_acc.return_value = {"cash": 8000.0, "portfolio_value": 10000.0, "positions_count": 1}
        mock_open_sym.return_value = {"AAPL"}
        # Current price 100, Peak was 110. Drawdown = 10/110 = 9%. Stop is 5% -> should FULL EXIT
        mock_pos.return_value = [{"symbol": "AAPL", "qty": 20, "current_price": 100.0, "market_value": 2000.0, "unrealized_plpc": -0.05}]
        mock_load_data.return_value = {"AAPL": pd.DataFrame()}
        mock_fresh.return_value = (True, "")
        mock_signal.return_value = ("HOLD", {"close": 100.0}, 0.5)
        mock_load_peaks.return_value = {"AAPL": 110.0}
        
        mock_order = MagicMock()
        mock_order.id = "full_exit_123"; mock_order.status = "ACCEPTED"
        mock_close.return_value = mock_order
        mock_wait.return_value = {"id": "full_exit_123", "status": "FILLED", "side": "SELL", "filled_qty": "20"}

        main()
        
        # Should only call close once (for full exit), NOT a separate call for trim
        self.assertEqual(mock_close.call_count, 1)
        args, kwargs = mock_close.call_args
        self.assertIn("exit_", kwargs["client_order_id"]) # Full exit prefix
        print("E2E Precedence (Full Exit > Trim) Verified")

if __name__ == "__main__":
    unittest.main()
