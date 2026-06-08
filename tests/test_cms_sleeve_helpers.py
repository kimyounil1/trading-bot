import unittest

from src.cms_helpers import (
    build_sleeve_control_panel_rows,
    validate_sleeve_target_weights,
)
from src.portfolio_sleeves import PortfolioSleeveAllocator, default_sleeves_config
from src.settings import StrategySettings


class CmsSleeveHelpersTest(unittest.TestCase):
    def test_validate_sleeve_weights_rejects_over_100(self) -> None:
        errors = validate_sleeve_target_weights(
            {"core": 0.6, "tournament": 0.3, "cash": 0.2}
        )
        self.assertTrue(errors)

    def test_build_sleeve_panel_rows(self) -> None:
        settings = StrategySettings(
            portfolio_sleeves_enabled=True,
            sleeves=default_sleeves_config(),
        )
        allocator = PortfolioSleeveAllocator(
            settings,
            account={"portfolio_value": 100_000.0, "cash": 20_000.0, "buying_power": 20_000.0},
            positions=[],
        )
        rows = build_sleeve_control_panel_rows(snapshot=allocator.build_snapshot())
        self.assertEqual(len(rows), 3)
        self.assertIn("order_budget", rows[0])


if __name__ == "__main__":
    unittest.main()
