import unittest
from unittest.mock import MagicMock

from src.cms_helpers import build_sleeves_config_dict, save_sleeve_settings
from src.portfolio_sleeves import default_sleeves_config
from src.settings import StrategySettings
from src.sleeve_runtime import SleeveRunContext, init_sleeve_run_context


class SleeveRuntimeTest(unittest.TestCase):
    def test_trim_approved_buys_enforces_running_budget(self) -> None:
        settings = StrategySettings(
            portfolio_sleeves_enabled=True,
            sleeves=default_sleeves_config(),
        )
        broker = MagicMock()
        broker.get_open_orders.return_value = []
        ctx = init_sleeve_run_context(
            settings,
            broker_adapter=broker,
            account={
                "portfolio_value": 100_000.0,
                "cash": 30_000.0,
                "buying_power": 30_000.0,
            },
            positions=[{"symbol": "NVDA", "market_value": 40_000.0}],
        )
        approved = [
            {"ticker": "A", "order_amount": 800.0},
            {"ticker": "B", "order_amount": 800.0},
        ]
        trimmed = ctx.trim_approved_buys(approved)
        self.assertEqual(len(trimmed), 2)
        self.assertLessEqual(
            trimmed[0]["order_amount"] + trimmed[1]["order_amount"],
            ctx.allocator.order_budget_for("core") + 1e-6,
        )

    def test_consume_submit_budget(self) -> None:
        ctx = SleeveRunContext(
            settings=StrategySettings(),
            allocator=MagicMock(),
            snapshot=MagicMock(),
            open_orders=[],
            core_budget_remaining=500.0,
        )
        ok, _ = ctx.check_submit_budget(200.0)
        self.assertTrue(ok)
        ctx.consume_submit_budget(200.0)
        self.assertAlmostEqual(ctx.core_budget_remaining, 300.0)


class CmsSleeveSaveTest(unittest.TestCase):
    def test_build_sleeves_config_dict_marks_tournament_paper_only(self) -> None:
        payload = build_sleeves_config_dict(
            core_weight=0.5,
            tournament_weight=0.3,
            cash_weight=0.2,
        )
        self.assertTrue(payload["tournament"]["paper_only"])

    def test_save_sleeve_settings_rejects_invalid_total(self) -> None:
        settings = StrategySettings(portfolio_sleeves_enabled=False)
        errors = save_sleeve_settings(
            settings,
            portfolio_sleeves_enabled=True,
            core_weight=0.6,
            tournament_weight=0.3,
            cash_weight=0.2,
        )
        self.assertTrue(errors)


if __name__ == "__main__":
    unittest.main()
