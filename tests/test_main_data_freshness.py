import unittest
from types import SimpleNamespace

import pandas as pd

from src.daily_bar_session import check_price_frame_freshness, drop_incomplete_session_bar


def _frame_for_dates(*dates: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(list(dates)),
            "close": [100.0 + idx for idx, _ in enumerate(dates)],
            "volume": [1_000_000] * len(dates),
        }
    )


class MainDataFreshnessTest(unittest.TestCase):
    def test_accepts_intraday_when_prior_completed_bar_exists(self) -> None:
        frame = _frame_for_dates("2026-05-26", "2026-05-27")
        market_clock = SimpleNamespace(
            is_open=True,
            timestamp="2026-05-27T14:00:00Z",
        )

        is_fresh, reason = check_price_frame_freshness(frame, market_clock)

        self.assertTrue(is_fresh)
        self.assertIn("intraday bar excluded", reason)

    def test_drop_incomplete_session_bar_removes_today(self) -> None:
        frame = _frame_for_dates("2026-05-26", "2026-05-27")
        market_clock = SimpleNamespace(
            is_open=True,
            timestamp="2026-05-27T14:00:00Z",
        )

        trimmed = drop_incomplete_session_bar(frame, market_clock)

        self.assertEqual(len(trimmed), 1)
        self.assertEqual(pd.Timestamp(trimmed["date"].iloc[-1]).date().isoformat(), "2026-05-26")

    def test_rejects_when_only_incomplete_session_bar(self) -> None:
        frame = _frame_for_dates("2026-05-27")
        market_clock = SimpleNamespace(
            is_open=True,
            timestamp="2026-05-27T14:00:00Z",
        )

        is_fresh, reason = check_price_frame_freshness(frame, market_clock)

        self.assertFalse(is_fresh)
        self.assertIn("no completed daily bar", reason)

    def test_rejects_stale_price_data(self) -> None:
        frame = _frame_for_dates("2026-05-20", "2026-05-21")
        market_clock = SimpleNamespace(
            is_open=False,
            timestamp="2026-05-27T22:00:00Z",
        )

        is_fresh, reason = check_price_frame_freshness(frame, market_clock)

        self.assertFalse(is_fresh)
        self.assertIn("stale price data", reason)

    def test_accepts_recent_completed_bar_when_market_closed(self) -> None:
        frame = _frame_for_dates("2026-05-23", "2026-05-26")
        market_clock = SimpleNamespace(
            is_open=False,
            timestamp="2026-05-27T22:00:00Z",
        )

        is_fresh, reason = check_price_frame_freshness(frame, market_clock)

        self.assertTrue(is_fresh)
        self.assertEqual(reason, "price data fresh (last_completed=2026-05-26)")


if __name__ == "__main__":
    unittest.main()
