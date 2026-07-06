"""Tests for rank leaderboard helpers."""

from __future__ import annotations

import unittest

import pandas as pd

from src.rank_ai_gate import RankAIGateScore
from src.rank_leaderboard import build_rank_leaderboard_frame, format_rank_leaderboard_for_display


class TestRankLeaderboard(unittest.TestCase):
    def test_build_and_format_sorted_by_percentile(self) -> None:
        scores = {
            "AAA": RankAIGateScore("AAA", 0.4, 0.9, True, "pass"),
            "BBB": RankAIGateScore("BBB", 0.5, 0.95, True, "pass"),
            "CCC": RankAIGateScore("CCC", 0.2, 0.4, False, "fail"),
        }
        buy_df = pd.DataFrame(
            [
                {
                    "ticker": "BBB",
                    "signal": "BUY",
                    "risk_allowed": True,
                    "would_submit_if_execute": True,
                }
            ]
        )
        frame = build_rank_leaderboard_frame(
            scores,
            open_symbols={"AAA"},
            buy_df=buy_df,
        )
        self.assertEqual(frame.iloc[0]["ticker"], "BBB")
        self.assertTrue(frame.iloc[0]["would_submit_if_execute"])
        self.assertTrue(frame[frame["ticker"] == "AAA"]["is_held"].iloc[0])

        display = format_rank_leaderboard_for_display(frame)
        self.assertIn("순위", display.columns)
        self.assertIn("상태", display.columns)
        self.assertEqual(display.iloc[0]["상태"], "매수후보")


if __name__ == "__main__":
    unittest.main()
