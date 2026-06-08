import unittest

from src.portfolio_sleeves import (
    CORE_SLEEVE_ID,
    PortfolioSleeveAllocator,
    cap_order_amount_for_sleeve,
    default_sleeves_config,
    trim_candidates_to_sleeve_budget,
    validate_sleeve_open_order_budget,
)
from src.settings import StrategySettings


class PortfolioSleevesTest(unittest.TestCase):
    def _settings(self) -> StrategySettings:
        return StrategySettings(
            portfolio_sleeves_enabled=True,
            sleeves=default_sleeves_config(),
        )

    def test_allocator_splits_core_budget(self) -> None:
        settings = self._settings()
        account = {"portfolio_value": 100_000.0, "cash": 20_000.0, "buying_power": 20_000.0}
        positions = [{"symbol": "NVDA", "market_value": 45_000.0}]
        allocator = PortfolioSleeveAllocator(
            settings,
            account=account,
            positions=positions,
            open_orders=[],
        )
        snapshot = allocator.build_snapshot()
        core = snapshot.sleeves[CORE_SLEEVE_ID]
        self.assertGreater(core.target_notional, 40_000.0)
        self.assertGreaterEqual(core.order_budget, 0.0)

    def test_cap_order_amount_respects_budget(self) -> None:
        settings = self._settings()
        account = {"portfolio_value": 100_000.0, "cash": 5_000.0, "buying_power": 5_000.0}
        allocator = PortfolioSleeveAllocator(
            settings,
            account=account,
            positions=[],
            open_orders=[{"side": "BUY", "notional": 4_000.0}],
        )
        capped = cap_order_amount_for_sleeve(
            2_000.0,
            sleeve_id=CORE_SLEEVE_ID,
            allocator=allocator,
        )
        self.assertLessEqual(capped, allocator.order_budget_for(CORE_SLEEVE_ID))

    def test_open_order_reconciliation_flags_over_reserved(self) -> None:
        settings = self._settings()
        account = {"portfolio_value": 100_000.0, "cash": 1_000.0, "buying_power": 1_000.0}
        open_orders = [{"side": "BUY", "notional": 5_000.0}]
        allocator = PortfolioSleeveAllocator(
            settings,
            account=account,
            positions=[],
            open_orders=open_orders,
        )
        snapshot = allocator.build_snapshot()
        ok, reason = validate_sleeve_open_order_budget(snapshot, open_orders)
        self.assertFalse(ok)
        self.assertIn("buying_power", reason.lower())

    def test_disabled_allocator_passthrough(self) -> None:
        settings = StrategySettings(portfolio_sleeves_enabled=False)
        account = {"portfolio_value": 50_000.0, "cash": 10_000.0, "buying_power": 10_000.0}
        allocator = PortfolioSleeveAllocator(settings, account=account, positions=[])
        snapshot = allocator.build_snapshot()
        self.assertFalse(snapshot.enabled)
        self.assertIn(CORE_SLEEVE_ID, snapshot.sleeves)

    def test_trim_candidates_enforces_running_budget(self) -> None:
        candidates = [
            {"ticker": "A", "order_amount": 800.0},
            {"ticker": "B", "order_amount": 800.0},
        ]
        trimmed, remaining = trim_candidates_to_sleeve_budget(candidates, 1000.0)
        self.assertEqual(len(trimmed), 2)
        self.assertAlmostEqual(trimmed[0]["order_amount"], 800.0)
        self.assertAlmostEqual(trimmed[1]["order_amount"], 200.0)
        self.assertAlmostEqual(remaining, 0.0)


if __name__ == "__main__":
    unittest.main()
