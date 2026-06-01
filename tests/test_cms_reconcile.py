import unittest

import pandas as pd

from src.cms_helpers import reconcile_cms_execute_with_alpaca


class TestCmsReconcile(unittest.TestCase):
    def test_missing_open_after_cms_submit(self) -> None:
        execute = [{"action": "BUY", "ticker": "AAPL", "order_id": "ord-1", "status": "NEW"}]
        alerts = reconcile_cms_execute_with_alpaca(execute, open_orders=[], closed_orders=[])
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["kind"], "cms_missing_on_alpaca")

    def test_orphan_cms_open_order(self) -> None:
        execute: list[dict] = []
        open_orders = [
            {
                "id": "ord-orphan",
                "client_order_id": "cms_buy_20260601_AAPL",
                "symbol": "AAPL",
                "side": "BUY",
            }
        ]
        alerts = reconcile_cms_execute_with_alpaca(execute, open_orders, closed_orders=[])
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["kind"], "alpaca_open_without_cms_log")

    def test_no_alert_when_order_still_open(self) -> None:
        execute = [{"action": "BUY", "ticker": "AAPL", "order_id": "ord-1", "status": "NEW"}]
        open_orders = [{"id": "ord-1", "symbol": "AAPL", "side": "BUY"}]
        alerts = reconcile_cms_execute_with_alpaca(
            pd.DataFrame(execute), open_orders, closed_orders=[]
        )
        self.assertEqual(alerts, [])


if __name__ == "__main__":
    unittest.main()
