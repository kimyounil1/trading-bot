import unittest
from unittest.mock import MagicMock, patch

from src.broker_adapter import AlpacaBrokerAdapter, OrderSubmission, get_broker_adapter
from src.brokers.paper import PaperBrokerAdapter
from src.brokers.toss import TossBrokerAdapter
from src.market_clock import MarketClock
from src.trading_session import TradingSession


class BrokerAdapterTest(unittest.TestCase):
    def test_get_broker_adapter_alpaca(self) -> None:
        adapter = get_broker_adapter("alpaca")
        self.assertEqual(adapter.provider, "alpaca")

    def test_get_broker_adapter_paper(self) -> None:
        adapter = get_broker_adapter("paper")
        self.assertIsInstance(adapter, PaperBrokerAdapter)

    @patch("src.alpaca_client.get_account_summary")
    def test_alpaca_get_account_delegates(self, mock_account) -> None:
        mock_account.return_value = {"cash": 1.0, "portfolio_value": 2.0}
        adapter = AlpacaBrokerAdapter()
        self.assertEqual(adapter.get_account()["portfolio_value"], 2.0)

    @patch("src.alpaca_client.get_recent_closed_orders")
    def test_alpaca_get_recent_closed_orders_delegates(self, mock_closed) -> None:
        mock_closed.return_value = [{"id": "ord-1", "status": "FILLED"}]
        adapter = AlpacaBrokerAdapter()
        orders = adapter.get_recent_closed_orders(limit=25)
        mock_closed.assert_called_once_with(limit=25)
        self.assertEqual(orders[0]["id"], "ord-1")

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

    def test_toss_not_live_capable(self) -> None:
        self.assertFalse(TossBrokerAdapter().is_live_capable())

    def test_toss_cancel_order_blocked(self) -> None:
        with self.assertRaises(NotImplementedError):
            TossBrokerAdapter().cancel_order("ord-1")

    @patch("src.brokers.toss.get_holdings")
    def test_toss_get_positions_normalizes(self, mock_holdings) -> None:
        mock_holdings.return_value = [
            {"symbol": "005930", "quantity": 10, "averagePrice": 70000},
            {"stockCode": "aapl", "qty": 3},
        ]
        positions = TossBrokerAdapter().get_positions()
        self.assertEqual(positions[0]["symbol"], "005930")
        self.assertEqual(positions[0]["qty"], 10)
        self.assertEqual(positions[1]["symbol"], "AAPL")

    @patch("src.brokers.toss.get_stocks")
    def test_toss_asset_info_normalizes_leveraged_etf(self, mock_stocks) -> None:
        mock_stocks.return_value = [
            {
                "symbol": "LNOK",
                "englishName": "DEFIANCE DAILY TARGET 2X LONG NOK ETF",
                "status": "ACTIVE",
                "securityType": "ETF",
                "leverageFactor": "2",
                "market": "AMEX",
            }
        ]

        info = TossBrokerAdapter().get_asset_info("lnok")

        self.assertTrue(info["active"])
        self.assertTrue(info["tradable"])
        self.assertEqual(info["security_type"], "ETF")
        self.assertEqual(info["leverage_factor"], 2.0)

    @patch("src.alpaca_client.discover_leveraged_long_assets")
    @patch("src.brokers.toss.get_stocks")
    def test_toss_discovery_verifies_candidate_metadata(
        self,
        mock_stocks,
        mock_discover,
    ) -> None:
        mock_discover.return_value = [
            {"symbol": "LNOK", "name": "Defiance Daily Target 2X Long NOK ETF"}
        ]
        mock_stocks.return_value = [
            {
                "symbol": "LNOK",
                "englishName": "DEFIANCE DAILY TARGET 2X LONG NOK ETF",
                "status": "ACTIVE",
                "securityType": "ETF",
                "leverageFactor": "2",
            }
        ]

        products = TossBrokerAdapter().discover_leveraged_long_products("NOK")

        self.assertEqual([row["symbol"] for row in products], ["LNOK"])

    @patch("src.brokers.toss.resolve_account_seq", return_value="1")
    @patch("src.brokers.toss.get_buying_power", return_value={"cash": 500.0})
    def test_toss_get_account(self, _mock_bp, _mock_seq) -> None:
        account = TossBrokerAdapter().get_account()
        self.assertEqual(account["account_seq"], "1")
        self.assertEqual(account["buying_power"]["cash"], 500.0)

    @patch("src.brokers.toss.get_orders")
    def test_toss_open_orders_uses_pending_status(self, mock_orders) -> None:
        mock_orders.return_value = [{"orderId": "o1"}]
        TossBrokerAdapter().get_open_orders(limit=25)
        mock_orders.assert_called_once_with(status="OPEN", limit=25)

    @patch("src.alpaca_client.submit_limit_buy_notional_order")
    @patch("src.alpaca_client.get_asset_summary")
    def test_alpaca_extended_buy_uses_limit(self, mock_asset, mock_limit) -> None:
        mock_asset.return_value = {
            "active": True,
            "tradable": True,
            "fractionable": True,
        }
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

    @patch("src.alpaca_client.submit_limit_buy_notional_order")
    @patch("src.alpaca_client.get_asset_summary")
    def test_alpaca_nonfractionable_extended_buy_uses_whole_shares(
        self,
        mock_asset,
        mock_limit,
    ) -> None:
        mock_asset.return_value = {
            "active": True,
            "tradable": True,
            "fractionable": False,
        }
        mock_limit.return_value = MagicMock(
            id="ord_2",
            status="accepted",
            side="buy",
            type="limit",
        )
        clock = MarketClock(
            is_open=False,
            timestamp="2026-06-02T08:00:00-04:00",
            next_open="",
            next_close="",
            session=TradingSession.PRE_MARKET,
            orders_allowed=True,
        )
        AlpacaBrokerAdapter().submit_buy_notional(
            "PLUL",
            1000.0,
            limit_price=8.0,
            market_clock=clock,
            slippage_pct=0.005,
        )
        self.assertTrue(mock_limit.call_args.kwargs["whole_shares"])

    @patch("src.alpaca_client.close_position_by_symbol")
    @patch("src.alpaca_client.get_asset_summary")
    def test_alpaca_nonfractionable_partial_sell_uses_whole_shares(
        self,
        mock_asset,
        mock_close,
    ) -> None:
        mock_asset.return_value = {
            "active": True,
            "tradable": True,
            "fractionable": False,
        }
        mock_close.return_value = MagicMock(
            id="ord_3",
            status="filled",
            side="sell",
            type="market",
        )
        clock = MarketClock(
            is_open=True,
            timestamp="2026-07-13T15:45:00-04:00",
            next_open="",
            next_close="",
            session=TradingSession.REGULAR,
            orders_allowed=True,
        )

        AlpacaBrokerAdapter().submit_sell_qty(
            "PLUL",
            100.75,
            limit_price=8.94,
            market_clock=clock,
            slippage_pct=0.005,
            client_order_id="slev_test_PLUL_1",
        )

        self.assertEqual(mock_close.call_args.kwargs["qty"], 100.0)


if __name__ == "__main__":
    unittest.main()
