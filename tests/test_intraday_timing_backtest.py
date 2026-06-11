"""Tests for intraday timing backtest helpers."""

from __future__ import annotations

import unittest
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import pandas as pd

from src.intraday_timing_backtest import (
    EntryMode,
    TIMING_POLICIES,
    TimingPolicy,
    _resolve_entry,
    derive_timing_recommendations,
)

ET = ZoneInfo("America/New_York")


def _hourly_frame(day: date, open_px: float, prices: dict[tuple[int, int], float]) -> pd.DataFrame:
    rows = []
    for (hour, minute), close in prices.items():
        ts = datetime.combine(day, time(hour, minute), tzinfo=ET)
        rows.append(
            {
                "timestamp": pd.Timestamp(ts),
                "open": open_px,
                "high": max(open_px, close),
                "low": min(open_px, close),
                "close": close,
                "volume": 1000,
            }
        )
    return pd.DataFrame(rows).sort_values("timestamp")


class IntradayTimingBacktestTest(unittest.TestCase):
    def test_resolve_entry_fixed_hour(self) -> None:
        policy = TIMING_POLICIES[0]
        day = date(2026, 6, 2)
        hourly = _hourly_frame(
            day,
            open_px=100.0,
            prices={(9, 35): 101.0, (15, 45): 102.0},
        )
        ok, fill, reason = _resolve_entry(policy, hourly, day)
        self.assertTrue(ok)
        self.assertAlmostEqual(fill or 0.0, 101.0)
        self.assertEqual(reason, "fixed")

    def test_resolve_entry_dip_from_open(self) -> None:
        policy = next(p for p in TIMING_POLICIES if p.entry_mode == EntryMode.DIP_FROM_OPEN)
        day = date(2026, 6, 3)
        hourly = _hourly_frame(
            day,
            open_px=100.0,
            prices={(9, 30): 100.0, (10, 30): 98.5},
        )
        ok, fill, reason = _resolve_entry(policy, hourly, day)
        self.assertTrue(ok)
        self.assertAlmostEqual(fill or 0.0, 98.5)
        self.assertEqual(reason, "dip")

    def test_derive_timing_recommendations_keep_baseline(self) -> None:
        results = [
            {"policy_id": "1_current_0935_1545", "label_ko": "baseline", "total_return_pct": -1.0},
            {"policy_id": "5_fade_spike", "label_ko": "fade", "total_return_pct": -0.8},
        ]
        rec = derive_timing_recommendations(results)
        self.assertEqual(rec["recommended_policy"], "1_current_0935_1545")
        self.assertIn("유지", rec["verdict_ko"])

    def test_derive_timing_recommendations_adopt_alternative(self) -> None:
        results = [
            {"policy_id": "1_current_0935_1545", "label_ko": "baseline", "total_return_pct": -2.0},
            {"policy_id": "5_fade_spike", "label_ko": "fade", "total_return_pct": 1.0},
        ]
        rec = derive_timing_recommendations(results)
        self.assertEqual(rec["recommended_policy"], "5_fade_spike")
        self.assertIn("paper trial", rec["verdict_ko"])


if __name__ == "__main__":
    unittest.main()
