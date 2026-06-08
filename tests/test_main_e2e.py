import unittest
from unittest.mock import patch, MagicMock, mock_open
from argparse import Namespace
from datetime import datetime, timezone
from types import SimpleNamespace
import pandas as pd
import numpy as np

from src.broker_adapter import OrderSubmission
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

    def _open_clock(self):
        return SimpleNamespace(
            is_open=True,
            is_regular_session=True,
            orders_allowed=True,
            session=SimpleNamespace(value="regular"),
            timestamp="2026-05-27T10:00:00Z",
            next_open=None,
            broker_provider="alpaca",
        )

    def _mock_broker(self, *, positions=None):
        mock_adapter = MagicMock()
        mock_adapter.get_account.return_value = {
            "cash": 10000.0,
            "portfolio_value": 10000.0,
            "last_equity": 10000.0,
            "positions_count": 0,
            "buying_power": 20000.0,
        }
        mock_adapter.get_positions.return_value = positions or []
        mock_adapter.get_open_symbols.return_value = {
            str(p["symbol"]).upper() for p in (positions or [])
        }
        mock_adapter.submit_buy_notional.return_value = OrderSubmission(
            order_id="order_123",
            status="ACCEPTED",
            side="BUY",
            order_type="MARKET",
        )
        mock_adapter.submit_sell_qty.return_value = OrderSubmission(
            order_id="exit_123",
            status="ACCEPTED",
            side="SELL",
            order_type="MARKET",
        )
        mock_adapter.wait_for_order_status.return_value = {
            "id": "order_123",
            "status": "FILLED",
            "side": "BUY",
            "type": "MARKET",
            "filled_qty": "1.0",
            "filled_avg_price": "150.0",
        }
        return mock_adapter

    @patch("src.main.parse_args")
    @patch("src.trading.run_context.load_settings")
    @patch("src.trading.run_context.apply_dynamic_profile")
    @patch("src.trading.run_context.get_market_clock")
    @patch("src.trading.run_context.get_broker_adapter")
    @patch("src.trading.run_context.load_price_data_batch")
    @patch("src.trading.exit_pipeline.get_signal_for_ticker")
    @patch("src.trading.buy_pipeline.get_signal_for_ticker")
    @patch("src.buy_guards.evaluate_ticker_consensus")
    @patch("src.trading.run_finalize.notify_run_summary")
    @patch("src.trading.run_context.load_peaks")
    @patch("src.trading.run_finalize.save_peaks")
    @patch("src.trading.exit_pipeline.get_position_entry_date")
    @patch("src.trading.run_context.check_price_frame_freshness")
    @patch("src.buy_guards.is_earnings_window")
    @patch("src.buy_guards.is_sector_allowed")
    @patch("src.trading.run_context.get_recent_buy_symbols")
    @patch("src.trading.run_context.get_today_buy_notional")
    @patch("src.buy_guards.is_correlation_allowed")
    def test_full_buy_flow(self, mock_corr, mock_today, mock_recent, mock_sector, mock_earnings, mock_fresh, mock_entry, 
                          mock_save_peaks, mock_load_peaks, mock_notify, 
                          mock_llm, mock_buy_signal, mock_exit_signal, mock_load_data, 
                          mock_broker, mock_clock, 
                          mock_profile, mock_settings, mock_args):
        
        mock_args.return_value = Namespace(execute=True)
        self.settings.tickers = ["AAPL"]
        mock_settings.return_value = self.settings
        mock_profile.return_value = (self.settings, "TEST_PROFILE")
        
        mock_clock.return_value = self._open_clock()
        mock_broker.return_value = self._mock_broker()
        mock_load_data.return_value = {"AAPL": pd.DataFrame(), "SPY": pd.DataFrame(), "^VIX": pd.DataFrame()}
        
        # Mock valid BUY signal
        buy_signal = ("BUY", {"close": 150.0, "ma20": 140.0, "ma50": 130.0, "rsi": 50.0}, 0.8)
        mock_buy_signal.return_value = buy_signal
        mock_exit_signal.return_value = buy_signal
        mock_fresh.return_value = (True, "")
        mock_llm.return_value = (True, "LLM Approved")
        mock_earnings.return_value = (False, "")
        mock_sector.return_value = (True, "")
        mock_corr.return_value = (True, "")
        mock_load_peaks.return_value = {}
        mock_recent.return_value = set()
        mock_today.return_value = 0.0
        
        main()
        mock_broker.return_value.submit_buy_notional.assert_called_once()
        print("E2E Buy Flow Verified")

    @patch("src.main.parse_args")
    @patch("src.trading.run_context.load_settings")
    @patch("src.trading.run_context.apply_dynamic_profile")
    @patch("src.trading.run_context.get_market_clock")
    @patch("src.trading.run_context.get_broker_adapter")
    @patch("src.trading.run_context.load_price_data_batch")
    @patch("src.trading.exit_pipeline.get_signal_for_ticker")
    @patch("src.trading.buy_pipeline.get_signal_for_ticker")
    @patch("src.trading.exit_pipeline.get_position_entry_date")
    @patch("src.trading.run_context.load_peaks")
    @patch("src.trading.run_context.check_price_frame_freshness")
    @patch("src.trading.run_finalize.notify_run_summary")
    def test_exit_by_time_limit(self, mock_notify, mock_fresh, mock_load_peaks, mock_entry,
                               mock_buy_signal, mock_exit_signal, mock_load_data, mock_broker, mock_clock, 
                               mock_profile, mock_settings, mock_args):
        
        mock_args.return_value = Namespace(execute=True)
        self.settings.tickers = ["AAPL"]
        mock_settings.return_value = self.settings
        mock_profile.return_value = (self.settings, "TEST_PROFILE")
        
        mock_clock.return_value = self._open_clock()
        positions_list = [{"symbol": "AAPL", "qty": 10, "current_price": 100.0, "market_value": 1000.0, "unrealized_plpc": 0.01}]
        broker = self._mock_broker(positions=positions_list)
        broker.get_account.return_value = {
            "cash": 5000.0,
            "portfolio_value": 10000.0,
            "last_equity": 10000.0,
            "positions_count": 1,
            "buying_power": 5000.0,
        }
        mock_broker.return_value = broker
        mock_load_data.return_value = {"AAPL": pd.DataFrame(), "SPY": pd.DataFrame(), "^VIX": pd.DataFrame()}
        mock_fresh.return_value = (True, "")
        
        # Signal is HOLD but time is up
        hold_signal = ("HOLD", {"close": 100.0}, 0.5)
        mock_buy_signal.return_value = hold_signal
        mock_exit_signal.return_value = hold_signal
        
        # 31 days ago (exceeds 30 day limit)
        mock_entry.return_value = datetime.now(timezone.utc) - pd.Timedelta(days=31)
        mock_load_peaks.return_value = {"AAPL": 110.0}
        broker.wait_for_order_status.return_value = {
            "id": "exit_123",
            "status": "FILLED",
            "side": "SELL",
            "type": "MARKET",
            "filled_qty": "10",
            "filled_avg_price": "100.0",
        }

        main()
        mock_broker.return_value.submit_sell_qty.assert_called_once()
        print("E2E Time-based Exit Verified")

    @patch("src.main.parse_args")
    @patch("src.trading.run_context.load_settings")
    @patch("src.trading.run_context.apply_dynamic_profile")
    @patch("src.trading.run_context.get_market_clock")
    @patch("src.trading.run_context.get_broker_adapter")
    @patch("src.trading.run_context.load_price_data_batch")
    @patch("src.trading.exit_pipeline.get_signal_for_ticker")
    @patch("src.trading.buy_pipeline.get_signal_for_ticker")
    @patch("src.trading.run_context.load_peaks")
    @patch("src.trading.run_context.check_price_frame_freshness")
    @patch("src.trading.run_finalize.notify_run_summary")
    def test_simultaneous_exit_and_trim(self, mock_notify, mock_fresh, mock_load_peaks, mock_buy_signal, mock_exit_signal, mock_load_data,
                                       mock_broker, mock_clock, mock_profile, mock_settings, mock_args):
        """Verify that Full Exit (Trailing Stop) takes precedence over Rebalance Trim."""
        mock_args.return_value = Namespace(execute=True)
        self.settings.tickers = ["AAPL"]
        # Target weight 10%, but position value is 2000/10000 = 20% -> should trim
        self.settings.max_position_pct = 0.1
        self.settings.rebalance_threshold_pct = 0.2
        mock_settings.return_value = self.settings
        mock_profile.return_value = (self.settings, "TEST_PROFILE")
        
        mock_clock.return_value = self._open_clock()
        positions_list = [
            {"symbol": "AAPL", "qty": 20, "current_price": 100.0, "market_value": 2000.0, "unrealized_plpc": -0.05}
        ]
        broker = self._mock_broker(positions=positions_list)
        broker.get_account.return_value = {
            "cash": 8000.0,
            "portfolio_value": 10000.0,
            "last_equity": 10000.0,
            "positions_count": 1,
            "buying_power": 8000.0,
        }
        mock_broker.return_value = broker
        mock_load_data.return_value = {"AAPL": pd.DataFrame(), "SPY": pd.DataFrame(), "^VIX": pd.DataFrame()}
        mock_fresh.return_value = (True, "")
        hold_signal = ("HOLD", {"close": 100.0}, 0.5)
        mock_buy_signal.return_value = hold_signal
        mock_exit_signal.return_value = hold_signal
        mock_load_peaks.return_value = {"AAPL": 110.0}
        broker.wait_for_order_status.return_value = {
            "id": "full_exit_123",
            "status": "FILLED",
            "side": "SELL",
            "filled_qty": "20",
            "filled_avg_price": "100.0",
        }

        main()
        
        self.assertEqual(mock_broker.return_value.submit_sell_qty.call_count, 1)
        args, kwargs = mock_broker.return_value.submit_sell_qty.call_args
        self.assertIn("exit_", kwargs["client_order_id"])
        print("E2E Precedence (Full Exit > Trim) Verified")

if __name__ == "__main__":
    unittest.main()
