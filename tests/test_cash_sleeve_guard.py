import unittest

from src.portfolio_sleeves import (
    CASH_SLEEVE_ID,
    PortfolioSleeveAllocator,
    default_sleeves_config,
)
from src.settings import StrategySettings


class CashSleeveGuardTest(unittest.TestCase):
    def test_cash_sleeve_has_zero_order_budget(self) -> None:
        settings = StrategySettings(
            portfolio_sleeves_enabled=True,
            sleeves=default_sleeves_config(),
        )
        account = {"portfolio_value": 100_000.0, "cash": 25_000.0, "buying_power": 25_000.0}
        allocator = PortfolioSleeveAllocator(
            settings,
            account=account,
            positions=[],
            open_orders=[],
        )
        cash = allocator.build_snapshot().sleeves[CASH_SLEEVE_ID]
        self.assertEqual(cash.order_budget, 0.0)
        self.assertGreater(cash.target_notional, 0.0)


if __name__ == "__main__":
    unittest.main()
