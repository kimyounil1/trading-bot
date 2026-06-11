"""Tests for regime stop backtest recommendation helpers."""

from __future__ import annotations

import unittest

from src.regime_stop_backtest import derive_stop_recommendations


class RegimeStopBacktestTest(unittest.TestCase):
    def test_derive_stop_recommendations_baseline_wins(self) -> None:
        rows = [
            {
                "window_id": "full_2y",
                "scenario_id": "1_baseline_current",
                "return_pct": 61.5,
                "mdd_pct": -9.4,
                "sharpe": 2.3,
            },
            {
                "window_id": "full_2y",
                "scenario_id": "7_regime_adaptive_standard",
                "return_pct": 48.3,
                "mdd_pct": -8.3,
                "sharpe": 1.9,
            },
            {
                "window_id": "bull_recent",
                "scenario_id": "1_baseline_current",
                "return_pct": 3.5,
                "mdd_pct": -1.7,
                "sharpe": 4.8,
            },
            {
                "window_id": "bull_recent",
                "scenario_id": "8_regime_adaptive_conservative",
                "return_pct": 3.2,
                "mdd_pct": -1.3,
                "sharpe": 5.4,
            },
        ]
        rec = derive_stop_recommendations(rows)
        self.assertEqual(rec["window_winners"]["full_2y"]["best_scenario"], "1_baseline_current")
        self.assertEqual(rec["regime_adaptive_best_in_windows"], 0)
        self.assertIn("baseline", rec["verdict_ko"])

    def test_derive_stop_recommendations_adaptive_wins_majority(self) -> None:
        rows = [
            {
                "window_id": "w1",
                "scenario_id": "1_baseline_current",
                "return_pct": 1.0,
                "mdd_pct": -2.0,
                "sharpe": 1.0,
            },
            {
                "window_id": "w1",
                "scenario_id": "7_regime_adaptive_standard",
                "return_pct": 2.0,
                "mdd_pct": -1.5,
                "sharpe": 1.5,
            },
            {
                "window_id": "w2",
                "scenario_id": "1_baseline_current",
                "return_pct": 1.0,
                "mdd_pct": -2.0,
                "sharpe": 1.0,
            },
            {
                "window_id": "w2",
                "scenario_id": "8_regime_adaptive_conservative",
                "return_pct": 3.0,
                "mdd_pct": -1.0,
                "sharpe": 2.0,
            },
        ]
        rec = derive_stop_recommendations(rows)
        self.assertEqual(rec["regime_adaptive_best_in_windows"], 2)
        self.assertIn("유의미", rec["verdict_ko"])


if __name__ == "__main__":
    unittest.main()
