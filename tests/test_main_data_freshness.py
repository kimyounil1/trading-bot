import unittest
from types import SimpleNamespace

import pandas as pd

from src.main import _check_price_frame_freshness


def _frame_for_dates(*dates: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(list(dates)),
            "close": [100.0 + idx for idx, _ in enumerate(dates)],
        }
    )


class MainDataFreshnessTest(unittest.TestCase):
    def test_rejects_incomplete_intraday_bar_when_market_is_open(self) -> None:
        frame = _frame_for_dates("2026-05-26", "2026-05-27")
        market_clock = SimpleNamespace(
            is_open=True,
            timestamp="2026-05-27T14:00:00Z",
        )

        is_fresh, reason = _check_price_frame_freshness(frame, market_clock)

        self.assertFalse(is_fresh)
        self.assertIn("incomplete intraday bar", reason)

    def test_rejects_stale_price_data(self) -> None:
        frame = _frame_for_dates("2026-05-20", "2026-05-21")
        market_clock = SimpleNamespace(
            is_open=False,
            timestamp="2026-05-27T22:00:00Z",
        )

        is_fresh, reason = _check_price_frame_freshness(frame, market_clock)

        self.assertFalse(is_fresh)
        self.assertIn("stale price data", reason)

    def test_accepts_recent_completed_bar(self) -> None:
        frame = _frame_for_dates("2026-05-23", "2026-05-26")
        market_clock = SimpleNamespace(
            is_open=True,
            timestamp="2026-05-27T14:00:00Z",
        )

        is_fresh, reason = _check_price_frame_freshness(frame, market_clock)

        self.assertTrue(is_fresh)
        self.assertEqual(reason, "price data fresh")


if __name__ == "__main__":
    unittest.main()
