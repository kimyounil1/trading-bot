import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.portfolio_sleeves import (
    CORE_SLEEVE_ID,
    TOURNAMENT_SLEEVE_ID,
    PortfolioSleeveAllocator,
    default_sleeves_config,
)
from src.settings import StrategySettings
from src.sleeve_rebalance import (
    build_sleeve_allocation_rebalance_plan,
    build_sleeve_rebalance_actions,
    build_sleeve_retag_actions,
)
from src.sleeve_rebalance_state import (
    allocation_rebalance_pending,
    clear_allocation_rebalance_pending,
    max_abs_sleeve_drift,
    request_allocation_rebalance,
    should_run_allocation_rebalance,
)


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

    def test_all_core_book_gets_proportional_retag(self) -> None:
        settings = StrategySettings(
            portfolio_sleeves_enabled=True,
            sleeves=default_sleeves_config(),
        )
        positions = [
            {"symbol": "AAA", "qty": 10, "current_price": 100.0, "market_value": 1_000.0},
            {"symbol": "BBB", "qty": 20, "current_price": 100.0, "market_value": 2_000.0},
            {"symbol": "CCC", "qty": 30, "current_price": 100.0, "market_value": 3_000.0},
        ]
        allocator = PortfolioSleeveAllocator(
            settings,
            account={
                "portfolio_value": 80_000.0,
                "cash": 56_000.0,
                "buying_power": 56_000.0,
            },
            positions=positions,
            sleeve_position_map={row["symbol"]: CORE_SLEEVE_ID for row in positions},
        )
        snapshot = allocator.build_snapshot()
        retags = build_sleeve_retag_actions(
            snapshot=snapshot,
            positions=positions,
            sleeve_position_map={row["symbol"]: CORE_SLEEVE_ID for row in positions},
            dust_min_usd=5.0,
        )
        self.assertTrue(retags)
        self.assertEqual(retags[0].to_sleeve_id, TOURNAMENT_SLEEVE_ID)
        moved_notional = sum(action.notional for action in retags)
        self.assertAlmostEqual(moved_notional, 3_000.0, delta=1_000.0)

    def test_allocation_plan_combines_retag_and_trim(self) -> None:
        settings = StrategySettings(
            portfolio_sleeves_enabled=True,
            sleeves=default_sleeves_config(),
        )
        positions = [
            {"symbol": "AAPL", "qty": 100, "current_price": 600.0, "market_value": 60_000.0},
            {"symbol": "MSFT", "qty": 10, "current_price": 400.0, "market_value": 4_000.0},
        ]
        sleeve_map = {"AAPL": CORE_SLEEVE_ID, "MSFT": CORE_SLEEVE_ID}
        allocator = PortfolioSleeveAllocator(
            settings,
            account={
                "portfolio_value": 100_000.0,
                "cash": 36_000.0,
                "buying_power": 36_000.0,
            },
            positions=positions,
            sleeve_position_map=sleeve_map,
        )
        plan = build_sleeve_allocation_rebalance_plan(
            snapshot=allocator.build_snapshot(),
            positions=positions,
            sleeve_position_map=sleeve_map,
            dust_min_usd=5.0,
            trigger_reason="test",
        )
        self.assertTrue(plan.retag_actions or plan.sell_actions)


class SleeveRebalanceStateTest(unittest.TestCase):
    def test_pending_request_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            self.assertFalse(allocation_rebalance_pending(path=path))
            request_allocation_rebalance(reason="test", path=path)
            self.assertTrue(allocation_rebalance_pending(path=path))
            clear_allocation_rebalance_pending(path=path)
            self.assertFalse(allocation_rebalance_pending(path=path))

    def test_drift_triggers_allocation_mode(self) -> None:
        settings = StrategySettings(
            portfolio_sleeves_enabled=True,
            sleeves=default_sleeves_config(),
        )
        allocator = PortfolioSleeveAllocator(
            settings,
            account={
                "portfolio_value": 80_000.0,
                "cash": 56_000.0,
                "buying_power": 56_000.0,
            },
            positions=[
                {"symbol": "AAA", "qty": 24, "current_price": 100.0, "market_value": 2_400.0},
            ],
            sleeve_position_map={"AAA": CORE_SLEEVE_ID},
        )
        snapshot = allocator.build_snapshot()
        self.assertGreater(max_abs_sleeve_drift(snapshot), 0.05)
        with patch(
            "src.sleeve_rebalance_state.allocation_rebalance_pending",
            return_value=False,
        ):
            run, reason = should_run_allocation_rebalance(snapshot)
        self.assertTrue(run)
        self.assertIn("drift=", reason)


if __name__ == "__main__":
    unittest.main()
