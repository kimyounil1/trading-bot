import unittest

from src.portfolio_sleeves import (
    CORE_SLEEVE_ID,
    PortfolioSleeveAllocator,
    default_sleeves_config,
)
from src.settings import StrategySettings
from src.sleeve_rebalance import build_sleeve_rebalance_actions


class SleeveRebalanceTest(unittest.TestCase):
    def test_core_overweight_generates_trim_plan(self) -> None:
        settings = StrategySettings(
            portfolio_sleeves_enabled=True,
            sleeves=default_sleeves_config(),
        )
        allocator = PortfolioSleeveAllocator(
            settings,
            account={
                "portfolio_value": 100_000.0,
                "cash": 5_000.0,
                "buying_power": 5_000.0,
            },
            positions=[
                {"symbol": "AAPL", "qty": 100, "current_price": 600.0, "market_value": 60_000.0},
            ],
            sleeve_position_map={"AAPL": CORE_SLEEVE_ID},
        )
        snapshot = allocator.build_snapshot()
        actions = build_sleeve_rebalance_actions(
            snapshot=snapshot,
            positions=allocator.positions,
            sleeve_position_map={"AAPL": CORE_SLEEVE_ID},
            dust_min_usd=5.0,
            min_excess_usd=1_000.0,
        )
        self.assertTrue(actions)
        self.assertEqual(actions[0].sleeve_id, CORE_SLEEVE_ID)
        self.assertGreater(actions[0].sell_qty, 0)


if __name__ == "__main__":
    unittest.main()
