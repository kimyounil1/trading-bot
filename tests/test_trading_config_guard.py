import unittest

from src.brokers.paper import PaperBrokerAdapter
from src.brokers.toss import TossBrokerAdapter
from src.settings import StrategySettings
from src.trading_config_guard import (
    apply_environment_profile,
    validate_config_schema,
    validate_live_policies,
    validate_trading_config,
)


class TradingConfigGuardTest(unittest.TestCase):
    def test_validate_config_schema_accepts_profile_keys(self) -> None:
        errors = validate_config_schema(
            {
                "tickers": ["AAPL"],
                "broker_provider": "alpaca",
                "trading_environment": "paper",
            }
        )
        self.assertEqual(errors, [])

    def test_live_policies_block_toss_broker(self) -> None:
        settings = StrategySettings(
            broker_provider="toss",
            live_safety_enabled=True,
            live_safety_max_daily_loss_pct=0.02,
        )
        reasons = validate_live_policies(settings, "live", TossBrokerAdapter())
        self.assertTrue(any("not live-capable" in r for r in reasons))

    def test_live_policies_require_safety_limits(self) -> None:
        settings = StrategySettings(
            broker_provider="alpaca",
            live_safety_enabled=True,
            live_safety_max_daily_loss_pct=0.0,
            live_safety_max_daily_loss_amount=0.0,
        )
        reasons = validate_live_policies(settings, "live", PaperBrokerAdapter())
        self.assertTrue(any("live_safety_max_daily_loss" in r for r in reasons))

    def test_apply_environment_profile_live_overlay(self) -> None:
        base = StrategySettings()
        live = apply_environment_profile(base, "live")
        self.assertEqual(live.trading_environment, "live")
        self.assertTrue(live.live_safety_enabled)

    def test_validate_trading_config_paper_ok(self) -> None:
        settings = apply_environment_profile(StrategySettings(), "paper")
        validate_trading_config(settings, "paper", PaperBrokerAdapter())


if __name__ == "__main__":
    unittest.main()
