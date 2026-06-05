import unittest
from argparse import Namespace
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

from src.features import build_features
from src.main import get_signal_for_ticker, main
from src.settings import StrategySettings, validate_settings


def _sample_price_frame(rows: int = 260) -> pd.DataFrame:
    values = np.arange(rows, dtype=float)
    # Test session date is 2026-05-21, so we use dates ending near that.
    return pd.DataFrame(
        {
            "date": pd.date_range(end="2026-05-20", periods=rows),
            "open": values + 1.0,
            "high": values + 2.0,
            "low": values + 0.5,
            "close": values + 1.5,
            "adj_close": values + 1.5,
            "volume": values + 100.0,
        }
    )


class PreQlibReadinessTest(unittest.TestCase):
    def test_validate_settings_normalizes_tickers(self) -> None:
        settings = StrategySettings(
            tickers=[" aapl ", "msft"],
            ma_fast=10,
            ma_slow=50,
            rsi_buy_limit=65,
            max_position_pct=0.4,
            max_total_positions=2,
            stop_loss_pct=0.05,
            take_profit_pct=0.1,
            max_test_order_amount=10.0,
            max_orders_per_run=1,
            max_daily_order_amount=1000.0,
            buy_cooldown_days=1,
            use_ai_score=False,
            ai_score_buy_threshold=0.55,
            market_regime_filter_enabled=False,
            market_regime_ticker="SPY",
            market_regime_ma_fast=50,
            market_regime_ma_slow=200,
        )

        validated = validate_settings(settings)
        self.assertEqual(validated.tickers, ["AAPL", "MSFT"])

    def test_validate_settings_rejects_invalid_moving_average_order(self) -> None:
        settings = StrategySettings(
            tickers=["AAPL"],
            ma_fast=50,
            ma_slow=50,
            rsi_buy_limit=65,
            max_position_pct=0.4,
            max_total_positions=2,
            stop_loss_pct=0.05,
            take_profit_pct=0.1,
            max_test_order_amount=10.0,
            max_orders_per_run=1,
            max_daily_order_amount=1000.0,
            buy_cooldown_days=1,
            use_ai_score=False,
            ai_score_buy_threshold=0.55,
            market_regime_filter_enabled=False,
            market_regime_ticker="SPY",
            market_regime_ma_fast=50,
            market_regime_ma_slow=200,
        )

        with self.assertRaisesRegex(ValueError, "ma_fast must be smaller than ma_slow"):
            validate_settings(settings)

    def test_build_features_rejects_short_input(self) -> None:
        with self.assertRaisesRegex(ValueError, "Not enough rows to build features"):
            build_features(_sample_price_frame(204), prediction_horizon=5)

    def test_build_features_rejects_missing_columns(self) -> None:
        frame = _sample_price_frame().drop(columns=["volume"])
        with self.assertRaisesRegex(ValueError, "Missing required price columns"):
            build_features(frame)

    def test_main_dry_run_smoke(self) -> None:
        settings = StrategySettings(
            tickers=["AAPL"],
            ma_fast=10,
            ma_slow=50,
            rsi_buy_limit=65,
            max_position_pct=0.4,
            max_total_positions=2,
            stop_loss_pct=0.05,
            take_profit_pct=0.1,
            max_test_order_amount=10.0,
            max_orders_per_run=1,
            max_daily_order_amount=1000.0,
            buy_cooldown_days=1,
            use_ai_score=False,
            ai_score_buy_threshold=0.55,
            market_regime_filter_enabled=False,
            market_regime_ticker="SPY",
            market_regime_ma_fast=50,
            market_regime_ma_slow=200,
        )
        frame = _sample_price_frame(80)

        with patch("src.main.parse_args", return_value=Namespace(execute=False)), patch(
            "src.main.load_settings", return_value=settings
        ), patch(
            "src.main.get_market_clock",
            return_value=SimpleNamespace(
                is_open=False,
                orders_allowed=False,
                session=SimpleNamespace(value="closed"),
                timestamp="2026-05-21T09:30:00Z",
                next_open="2026-05-22T09:30:00Z",
                next_close="2026-05-21T16:00:00Z",
                broker_provider="alpaca",
                extended_hours_enabled=False,
            ),
        ), patch(
            "src.main.get_broker_adapter"
        ) as broker_adapter_mock, patch(
            "src.main.load_price_data_batch", return_value={"AAPL": frame}
        ), patch(
            "src.main.get_today_buy_notional", return_value=0.0
        ), patch(
            "src.main.get_recent_buy_symbols", return_value=set()
        ), patch(
            "src.main.log_signal"
        ) as log_signal_mock, patch(
            "src.main.notify_error"
        ) as notify_error_mock, patch(
            "src.main.notify_run_summary"
        ) as notify_summary_mock:
            broker_adapter_mock.return_value.get_account.return_value = {
                "cash": 1000.0,
                "positions_count": 0,
                "portfolio_value": 1000.0,
                "last_equity": 1000.0,
                "buying_power": 1000.0,
            }
            broker_adapter_mock.return_value.get_positions.return_value = []
            broker_adapter_mock.return_value.get_open_symbols.return_value = set()
            broker_adapter_mock.return_value.submit_buy_notional = MagicMock()
            main()

        log_signal_mock.assert_called_once()
        broker_adapter_mock.return_value.submit_buy_notional.assert_not_called()
        notify_error_mock.assert_not_called()
        notify_summary_mock.assert_called_once()

    def test_get_signal_for_ticker_blocks_buy_in_bearish_market_regime(self) -> None:
        settings = StrategySettings(
            tickers=["AAPL"],
            ma_fast=10,
            ma_slow=50,
            rsi_buy_limit=101,
            max_position_pct=0.4,
            max_total_positions=2,
            stop_loss_pct=0.05,
            take_profit_pct=0.1,
            max_test_order_amount=10.0,
            max_orders_per_run=1,
            max_daily_order_amount=1000.0,
            buy_cooldown_days=1,
            use_ai_score=False,
            ai_score_buy_threshold=0.55,
            market_regime_filter_enabled=True,
            market_regime_ticker="SPY",
            market_regime_ma_fast=50,
            market_regime_ma_slow=200,
        )

        signal, _, _ = get_signal_for_ticker(
            "AAPL",
            _sample_price_frame(80),
            settings,
            market_regime_bullish=False,
        )

        self.assertEqual(signal, "HOLD")


if __name__ == "__main__":
    unittest.main()
