import unittest
from unittest.mock import patch

from src.portfolio_sleeves import CORE_SLEEVE_ID, cap_order_amount_for_sleeve
from src.settings import StrategySettings


class SleeveOrderBudgetIntegrationTest(unittest.TestCase):
    @patch("src.main.PortfolioSleeveAllocator")
    def test_cap_order_amount_for_sleeve_import(self, _mock) -> None:
        settings = StrategySettings(portfolio_sleeves_enabled=False)
        self.assertFalse(settings.portfolio_sleeves_enabled)
        self.assertEqual(CORE_SLEEVE_ID, "core")

    def test_cap_respects_zero_budget(self) -> None:
        from src.portfolio_sleeves import PortfolioSleeveAllocator, default_sleeves_config

        settings = StrategySettings(
            portfolio_sleeves_enabled=True,
            sleeves=default_sleeves_config(),
        )
        account = {"portfolio_value": 100_000.0, "cash": 1_000.0, "buying_power": 500.0}
        allocator = PortfolioSleeveAllocator(
            settings,
            account=account,
            positions=[{"symbol": "NVDA", "market_value": 60_000.0}],
            open_orders=[{"side": "BUY", "notional": 2_000.0}],
        )
        capped = cap_order_amount_for_sleeve(
            1_500.0,
            sleeve_id=CORE_SLEEVE_ID,
            allocator=allocator,
        )
        self.assertLessEqual(capped, allocator.order_budget_for(CORE_SLEEVE_ID))


if __name__ == "__main__":
    unittest.main()
