"""Tests for consolidated research promotion gates."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.research_promotion_gates import (
    build_research_promotion_gates_report,
    scan_rank_label_experiments,
    validate_research_promotion_gates_report,
)


def _rank_summary(
    *,
    gap: float,
    passed: bool,
    horizon: int = 20,
    top: float = 0.15,
    q: float = 0.85,
) -> dict:
    return {
        "label": {
            "prediction_horizon": horizon,
            "top_bucket_pct": top,
            "min_score_quantile": q,
        },
        "portfolio_oos": {
            "gap_pct": gap,
            "sharpe_ratio": 1.5,
            "max_drawdown": -0.1,
            "turnover_proxy": 1.0,
        },
        "gate": {"passed": passed},
        "metrics": {"top_bucket_auc": 0.61},
        "recommendation": "ok",
    }


class ResearchPromotionGatesTest(unittest.TestCase):
    def test_scan_rank_label_experiments_sorts_passed_first(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ml = Path(tmp)
            (ml / "rank_label_experiment_h20_top15_q85").mkdir()
            (ml / "rank_label_experiment_h20_top10_q90").mkdir()
            (ml / "rank_label_experiment_h20_top15_q85" / "latest_summary.json").write_text(
                json.dumps(_rank_summary(gap=14.4, passed=True)),
                encoding="utf-8",
            )
            (ml / "rank_label_experiment_h20_top10_q90" / "latest_summary.json").write_text(
                json.dumps(_rank_summary(gap=6.6, passed=True, top=0.1, q=0.9)),
                encoding="utf-8",
            )
            (ml / "rank_label_experiment").mkdir()
            (ml / "rank_label_experiment" / "latest_summary.json").write_text(
                json.dumps(_rank_summary(gap=-5.0, passed=False, top=0.3)),
                encoding="utf-8",
            )
            rows = scan_rank_label_experiments(ml)
            self.assertTrue(rows[0]["gate_passed"])
            self.assertEqual(rows[0]["experiment_id"], "h20_top15_q85")

    def test_build_report_includes_guard_and_verdict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ml = root / "ml"
            ml.mkdir()
            exp = ml / "rank_label_experiment_h20_top15_q85"
            exp.mkdir()
            (exp / "latest_summary.json").write_text(
                json.dumps(_rank_summary(gap=14.4, passed=True)),
                encoding="utf-8",
            )
            guard = root / "guard_policy.json"
            guard.write_text(
                json.dumps(
                    {
                        "recommendations": {
                            "current_regime_hint": "bear",
                            "bull_market": {"preferred_scenario": "sector3_crowding3"},
                            "bear_market": {"preferred_scenario": "crowding_max_3"},
                            "do_not_relax_guards_when": ["rank paper active"],
                        }
                    }
                ),
                encoding="utf-8",
            )
            regime = root / "regime_stop.json"
            regime.write_text(
                json.dumps({"recommendations": {"verdict_ko": "baseline 유지"}}),
                encoding="utf-8",
            )
            report = build_research_promotion_gates_report(
                ml_dir=ml,
                guard_policy_path=guard,
                regime_stop_path=regime,
                intraday_path=root / "missing.json",
            )
            validate_research_promotion_gates_report(report)
            self.assertEqual(report["rank_label_sweep"]["passed_count"], 1)
            self.assertIn("baseline 유지", report["exit_timing_research"]["regime_stop_verdict"])
            self.assertFalse(report["paper_rank_gate"]["champion_promotion_allowed"])


if __name__ == "__main__":
    unittest.main()
