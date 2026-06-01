import unittest
from unittest.mock import MagicMock, patch

from src.broker_adapter import AlpacaBrokerAdapter, OrderSubmission, get_broker_adapter
from src.market_clock import MarketClock
from src.trading_session import TradingSession


class BrokerAdapterTest(unittest.TestCase):
    def test_get_broker_adapter_alpaca(self) -> None:
        adapter = get_broker_adapter("alpaca")
        self.assertEqual(adapter.provider, "alpaca")

    def test_get_broker_adapter_toss_stub(self) -> None:
        adapter = get_broker_adapter("toss")
        self.assertEqual(adapter.provider, "toss")
        with self.assertRaises(NotImplementedError):
            adapter.submit_buy_notional(
                "AAPL",
                100.0,
                limit_price=150.0,
                market_clock=MarketClock(
                    is_open=False,
                    timestamp="2026-06-02T13:00:00+09:00",
                    next_open="",
                    next_close="",
                    session=TradingSession.DAY_MARKET,
                    orders_allowed=True,
                ),
                slippage_pct=0.005,
            )

    @patch("src.alpaca_client.submit_limit_buy_notional_order")
    def test_alpaca_extended_buy_uses_limit(self, mock_limit) -> None:
        mock_limit.return_value = MagicMock(
            id="ord_1",
            status="accepted",
            side="buy",
            type="limit",
        )
        adapter = AlpacaBrokerAdapter()
        clock = MarketClock(
            is_open=False,
            timestamp="2026-06-02T08:00:00-04:00",
            next_open="",
            next_close="",
            session=TradingSession.PRE_MARKET,
            orders_allowed=True,
        )
        submission = adapter.submit_buy_notional(
            "AAPL",
            100.0,
            limit_price=150.0,
            market_clock=clock,
            slippage_pct=0.005,
        )
        mock_limit.assert_called_once()
        self.assertEqual(submission.order_id, "ord_1")
        self.assertEqual(submission.order_type, "limit")


if __name__ == "__main__":
    unittest.main()
