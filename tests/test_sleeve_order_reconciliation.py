import unittest

from src.portfolio_sleeves import (
    PortfolioSleeveAllocator,
    default_sleeves_config,
    validate_sleeve_open_order_budget,
)
from src.settings import StrategySettings


class SleeveOrderReconciliationTest(unittest.TestCase):
    def test_reconciliation_ok_without_open_orders(self) -> None:
        settings = StrategySettings(
            portfolio_sleeves_enabled=True,
            sleeves=default_sleeves_config(),
        )
        account = {"portfolio_value": 50_000.0, "cash": 10_000.0, "buying_power": 10_000.0}
        allocator = PortfolioSleeveAllocator(settings, account=account, positions=[])
        snapshot = allocator.build_snapshot()
        ok, reason = validate_sleeve_open_order_budget(snapshot, [])
        self.assertTrue(ok)
        self.assertEqual(reason, "")


if __name__ == "__main__":
    unittest.main()
