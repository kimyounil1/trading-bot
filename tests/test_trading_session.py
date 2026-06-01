import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from src.trading_session import (
    TradingSession,
    orders_allowed_for_session,
    resolve_alpaca_session,
    resolve_trading_session,
    resolve_toss_day_market_session,
)

ET = ZoneInfo("America/New_York")
KST = ZoneInfo("Asia/Seoul")


class TradingSessionTest(unittest.TestCase):
    def test_regular_session_monday_morning(self) -> None:
        dt = datetime(2026, 6, 1, 11, 0, tzinfo=ET)
        self.assertEqual(resolve_alpaca_session(dt), TradingSession.REGULAR)

    def test_pre_market_session(self) -> None:
        dt = datetime(2026, 6, 2, 8, 0, tzinfo=ET)
        self.assertEqual(resolve_alpaca_session(dt), TradingSession.PRE_MARKET)

    def test_after_hours_session(self) -> None:
        dt = datetime(2026, 6, 2, 17, 30, tzinfo=ET)
        self.assertEqual(resolve_alpaca_session(dt), TradingSession.AFTER_HOURS)

    def test_overnight_session_sunday_evening(self) -> None:
        dt = datetime(2026, 5, 31, 21, 0, tzinfo=ET)
        self.assertEqual(resolve_alpaca_session(dt), TradingSession.OVERNIGHT)

    def test_closed_on_saturday(self) -> None:
        dt = datetime(2026, 6, 6, 12, 0, tzinfo=ET)
        self.assertEqual(resolve_alpaca_session(dt), TradingSession.CLOSED)

    def test_closed_friday_after_8pm(self) -> None:
        dt = datetime(2026, 6, 5, 21, 0, tzinfo=ET)
        self.assertEqual(resolve_alpaca_session(dt), TradingSession.CLOSED)

    def test_toss_day_market_kst(self) -> None:
        dt = datetime(2026, 6, 2, 13, 0, tzinfo=KST)
        self.assertEqual(
            resolve_toss_day_market_session(dt, start_kst="10:00", end_kst="18:00"),
            TradingSession.DAY_MARKET,
        )

    def test_orders_allowed_for_extended_session(self) -> None:
        state = resolve_trading_session(
            datetime(2026, 6, 2, 8, 0, tzinfo=ET),
            broker_provider="alpaca",
        )
        self.assertTrue(
            orders_allowed_for_session(
                state,
                extended_hours_enabled=True,
                enabled_trading_sessions=["regular", "pre_market"],
            )
        )

    def test_orders_blocked_when_extended_disabled(self) -> None:
        state = resolve_trading_session(
            datetime(2026, 6, 2, 8, 0, tzinfo=ET),
            broker_provider="alpaca",
        )
        self.assertFalse(
            orders_allowed_for_session(
                state,
                extended_hours_enabled=False,
                enabled_trading_sessions=["regular", "pre_market"],
            )
        )

    def test_toss_day_market_enabled(self) -> None:
        state = resolve_trading_session(
            datetime(2026, 6, 2, 13, 0, tzinfo=KST),
            broker_provider="toss",
            day_market_start_kst="10:00",
            day_market_end_kst="18:00",
        )
        self.assertEqual(state.session, TradingSession.DAY_MARKET)
        self.assertTrue(
            orders_allowed_for_session(
                state,
                extended_hours_enabled=False,
                enabled_trading_sessions=["day_market"],
            )
        )


if __name__ == "__main__":
    unittest.main()
