import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.brokers.paper import PaperBrokerAdapter
from src.market_clock import MarketClock
from src.position_dust import (
    count_meaningful_positions,
    meaningful_gross_exposure,
    meaningful_open_symbols,
)
from src.risk.live_safety import LiveSafetyConfig, LiveSafetyGuard
from src.settings import StrategySettings
from src.trading_session import TradingSession


class PositionDustGuardTest(unittest.TestCase):
    def test_meaningful_open_symbols_excludes_dust(self) -> None:
        positions = [
            {"symbol": "AAPL", "market_value": 1000.0},
            {"symbol": "STUB", "market_value": 1.0},
        ]
        symbols = meaningful_open_symbols(positions, min_usd=5.0)
        self.assertEqual(symbols, {"AAPL"})
        self.assertEqual(count_meaningful_positions(positions, min_usd=5.0), 1)
        self.assertAlmostEqual(
            meaningful_gross_exposure(positions, min_usd=5.0),
            1000.0,
        )


class BrokerOrderPathTest(unittest.TestCase):
    def _clock(self) -> MarketClock:
        return MarketClock(
            is_open=True,
            timestamp="2026-06-05T12:00:00Z",
            next_open="",
            next_close="",
            session=TradingSession.REGULAR,
            orders_allowed=True,
        )

    def test_duplicate_client_order_id_is_idempotent(self) -> None:
        broker = PaperBrokerAdapter(cash=50_000.0, prices={"AAPL": 100.0})
        kwargs = dict(
            limit_price=100.0,
            market_clock=self._clock(),
            slippage_pct=0.0,
            client_order_id="dup_test",
        )
        first = broker.submit_buy_notional("AAPL", 100.0, **kwargs)
        second = broker.submit_buy_notional("AAPL", 100.0, **kwargs)
        self.assertEqual(first.order_id, second.order_id)
        self.assertEqual(len(broker.get_positions()), 1)

    def test_kill_switch_blocks_buy(self) -> None:
        with TemporaryDirectory() as tmp:
            kill = Path(tmp) / "KILL_SWITCH"
            kill.write_text("1", encoding="utf-8")
            guard = LiveSafetyGuard(
                LiveSafetyConfig(enabled=False, kill_switch_path=kill),
                account={"portfolio_value": 10_000.0, "last_equity": 10_000.0},
            )
            result = guard.check_new_buy(notional=100.0, open_positions_count=0)
            self.assertFalse(result.allowed)

    def test_daily_loss_blocks_when_enabled(self) -> None:
        guard = LiveSafetyGuard(
            LiveSafetyConfig(enabled=True, max_daily_loss_pct=0.05),
            account={"portfolio_value": 9000.0, "last_equity": 10_000.0},
        )
        result = guard.check_new_buy(notional=50.0, open_positions_count=0)
        self.assertFalse(result.allowed)

    def test_broker_submit_failure_increments_guard(self) -> None:
        with TemporaryDirectory() as tmp:
            state = Path(tmp) / "state.json"
            guard = LiveSafetyGuard(
                LiveSafetyConfig(
                    enabled=True,
                    state_path=state,
                    max_consecutive_order_failures=2,
                ),
                account={"portfolio_value": 10_000.0, "last_equity": 10_000.0},
            )
            guard.record_order_failure()
            guard.record_order_failure()
            result = guard.check_new_buy(notional=10.0, open_positions_count=0)
            self.assertFalse(result.allowed)

    def test_paper_broker_submit_failure_raises(self) -> None:
        broker = PaperBrokerAdapter(fail_submit=True)
        with self.assertRaises(ConnectionError):
            broker.submit_buy_notional(
                "AAPL",
                10.0,
                limit_price=100.0,
                market_clock=self._clock(),
                slippage_pct=0.0,
            )


class LoadSettingsProfileTest(unittest.TestCase):
    def test_load_settings_applies_paper_profile(self) -> None:
        settings = StrategySettings(live_safety_enabled=True)
        from src.trading_config_guard import apply_environment_profile

        paper = apply_environment_profile(settings, "paper")
        self.assertFalse(paper.live_safety_enabled)


if __name__ == "__main__":
    unittest.main()
