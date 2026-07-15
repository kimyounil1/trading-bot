"""Tests for rank leaderboard helpers."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

from src.rank_ai_gate import RankAIGateScore
from src.rank_leaderboard import (
    build_rank_leaderboard_frame,
    build_rank_leaderboard_live,
    format_rank_leaderboard_for_display,
)


class TestRankLeaderboard(unittest.TestCase):
    def test_live_build_accepts_vix_dataframe_without_boolean_coercion(self) -> None:
        settings = SimpleNamespace(
            tickers=["AAPL"],
            use_ai_score=False,
            rank_ai_buy_gate_min_score_quantile=0.85,
            rank_ai_buy_gate_top_bucket_pct=0.15,
        )
        vix_df = pd.DataFrame({"close": [18.0, 19.0]})
        spy_df = pd.DataFrame({"close": [100.0, 101.0]})
        scores = {
            "AAPL": RankAIGateScore("AAPL", 0.5, 0.9, True, "pass")
        }

        with patch(
            "src.candidate_cache._load_cache_ticker_data",
            return_value={"^VIX": vix_df, "SPY": spy_df},
        ), patch(
            "src.rank_leaderboard.build_rank_ai_gate_scores",
            return_value=scores,
        ) as build_scores:
            frame = build_rank_leaderboard_live(settings)

        self.assertEqual(frame["ticker"].tolist(), ["AAPL"])
        self.assertIs(build_scores.call_args.kwargs["vix_df"], vix_df)

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
