import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.risk.live_safety import LiveSafetyConfig, LiveSafetyGuard
from src.settings import StrategySettings


class LiveSafetyGuardTest(unittest.TestCase):
    def test_kill_switch_blocks_without_enabled_flag(self) -> None:
        with TemporaryDirectory() as tmp:
            kill = Path(tmp) / "KILL_SWITCH"
            kill.write_text("1", encoding="utf-8")
            guard = LiveSafetyGuard(
                LiveSafetyConfig(enabled=False, kill_switch_path=kill),
                account={"portfolio_value": 10000.0, "last_equity": 10000.0},
            )
            result = guard.check_new_buy(notional=100.0, open_positions_count=0)
            self.assertFalse(result.allowed)
            self.assertIn("kill switch", result.reason)

    def test_daily_loss_pct_when_enabled(self) -> None:
        guard = LiveSafetyGuard(
            LiveSafetyConfig(enabled=True, max_daily_loss_pct=0.05),
            account={"portfolio_value": 9000.0, "last_equity": 10000.0},
        )
        result = guard.check_new_buy(notional=100.0, open_positions_count=0)
        self.assertFalse(result.allowed)
        self.assertIn("daily loss pct", result.reason)

    def test_max_orders_per_day(self) -> None:
        with TemporaryDirectory() as tmp:
            state = Path(tmp) / "state.json"
            state.write_text(
                '{"days": {"2026-06-04": {"orders_submitted": 2}}}',
                encoding="utf-8",
            )
            guard = LiveSafetyGuard(
                LiveSafetyConfig(
                    enabled=True,
                    state_path=state,
                    max_orders_per_day=2,
                ),
                trading_day=__import__("datetime").date(2026, 6, 4),
                account={"portfolio_value": 10000.0, "last_equity": 10000.0},
            )
            result = guard.check_new_buy(notional=50.0, open_positions_count=0)
            self.assertFalse(result.allowed)
            self.assertIn("daily order cap", result.reason)

    def test_from_settings_defaults(self) -> None:
        guard = LiveSafetyGuard.from_settings(StrategySettings())
        self.assertFalse(guard.config.enabled)
        result = guard.check_new_buy(notional=10.0, open_positions_count=0)
        self.assertTrue(result.allowed)


if __name__ == "__main__":
    unittest.main()
