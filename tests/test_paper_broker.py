import unittest

from src.brokers.paper import PaperBrokerAdapter
from src.market_clock import MarketClock
from src.trading_session import TradingSession


class PaperBrokerAdapterTest(unittest.TestCase):
    def _clock(self) -> MarketClock:
        return MarketClock(
            is_open=True,
            timestamp="2026-06-04T14:00:00Z",
            next_open="",
            next_close="",
            session=TradingSession.REGULAR,
            orders_allowed=True,
        )

    def test_buy_and_positions(self) -> None:
        broker = PaperBrokerAdapter(cash=50_000.0, prices={"AAPL": 100.0})
        broker.submit_buy_notional(
            "AAPL",
            1000.0,
            limit_price=100.0,
            market_clock=self._clock(),
            slippage_pct=0.0,
            client_order_id="buy_test_1",
        )
        positions = broker.get_positions()
        self.assertEqual(len(positions), 1)
        self.assertEqual(positions[0]["symbol"], "AAPL")
        account = broker.get_account()
        self.assertLess(account["cash"], 50_000.0)

    def test_duplicate_client_order_id_is_idempotent(self) -> None:
        broker = PaperBrokerAdapter(cash=50_000.0, prices={"AAPL": 100.0})
        first = broker.submit_buy_notional(
            "AAPL",
            500.0,
            limit_price=100.0,
            market_clock=self._clock(),
            slippage_pct=0.0,
            client_order_id="dup_coid",
        )
        second = broker.submit_buy_notional(
            "AAPL",
            500.0,
            limit_price=100.0,
            market_clock=self._clock(),
            slippage_pct=0.0,
            client_order_id="dup_coid",
        )
        self.assertEqual(first.order_id, second.order_id)
        self.assertEqual(len(broker.get_positions()), 1)

    def test_not_live_capable(self) -> None:
        broker = PaperBrokerAdapter()
        self.assertFalse(broker.is_live_capable())


if __name__ == "__main__":
    unittest.main()
