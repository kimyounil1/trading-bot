import unittest

from src.alpaca_client import order_is_filled, order_is_open, serialize_alpaca_order


class _FakeOrder:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class AlpacaOrderBoardTest(unittest.TestCase):
    def test_order_is_open_and_filled(self) -> None:
        self.assertTrue(order_is_open("OrderStatus.NEW"))
        self.assertTrue(order_is_open("OrderStatus.PARTIALLY_FILLED"))
        self.assertFalse(order_is_open("OrderStatus.FILLED"))
        self.assertTrue(order_is_filled("OrderStatus.FILLED"))
        self.assertFalse(order_is_filled("OrderStatus.CANCELED"))

    def test_serialize_alpaca_order_includes_limit_and_fill_pct(self) -> None:
        order = _FakeOrder(
            id="abc-123",
            symbol="AMT",
            status="OrderStatus.NEW",
            side="OrderSide.BUY",
            type="OrderType.LIMIT",
            qty="10",
            filled_qty="0",
            filled_avg_price=None,
            limit_price="215.5",
            notional=None,
            extended_hours=True,
            submitted_at="2026-06-01T04:00:00Z",
            filled_at=None,
            updated_at="2026-06-01T04:00:00Z",
        )

        payload = serialize_alpaca_order(order)

        self.assertEqual(payload["symbol"], "AMT")
        self.assertEqual(payload["status_simple"], "NEW")
        self.assertEqual(payload["limit_price"], "215.5")
        self.assertTrue(payload["extended_hours"])
        self.assertEqual(payload["fill_pct"], 0.0)


if __name__ == "__main__":
    unittest.main()
