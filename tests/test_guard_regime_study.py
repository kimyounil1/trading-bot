"""Tests for guard regime study report helpers."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from src.guard_regime_study import (
    derive_recommendations,
    format_llm_context_ko,
    validate_guard_regime_study_report,
)

FIXTURE = {
    "generated_at": "2026-06-11T00:00:00Z",
    "methodology": {"scenarios": ["baseline"]},
    "regimes": {
        "bull_recent": {
            "label_ko": "강세",
            "spy_return_pct": 9.9,
            "best_scenario": "crowding_max_3",
            "scenarios": [
                {"scenario_id": "baseline", "return_pct": 2.0},
                {"scenario_id": "crowding_max_3", "return_pct": 3.5},
            ],
            "audit_counterfactual": [
                {"block_type": "sector", "mean_forward_return_pct": 1.2},
            ],
        },
        "bear_recent": {
            "label_ko": "약세",
            "spy_return_pct": -1.8,
            "best_scenario": "baseline",
            "scenarios": [
                {"scenario_id": "baseline", "return_pct": 0.2},
                {"scenario_id": "sector3_crowding3", "return_pct": -0.1},
            ],
            "audit_counterfactual": [
                {"block_type": "sector", "mean_forward_return_pct": -2.5},
                {"block_type": "crowding", "mean_forward_return_pct": -5.1},
            ],
        },
        "bear_stress": {
            "label_ko": "급락",
            "spy_return_pct": -13.7,
            "best_scenario": "baseline",
            "scenarios": [{"scenario_id": "baseline", "return_pct": -4.0}],
            "audit_counterfactual": [],
        },
    },
    "recommendations": {},
    "llm_context_ko": "",
    "policy_path": "data/research/guard_regime_policy.json",
}


class GuardRegimeStudyTest(unittest.TestCase):
    def test_derive_recommendations_bear_prefers_baseline(self) -> None:
        rec = derive_recommendations(FIXTURE["regimes"])
        self.assertEqual(rec["bear_market"]["preferred_scenario"], "baseline")
        self.assertEqual(rec["bull_market"]["preferred_scenario"], "crowding_max_3")
        self.assertEqual(rec["current_regime_hint"], "bear")

    def test_format_llm_context_contains_regimes(self) -> None:
        report = dict(FIXTURE)
        report["recommendations"] = derive_recommendations(FIXTURE["regimes"])
        report["llm_context_ko"] = format_llm_context_ko(report)
        self.assertIn("강세", report["llm_context_ko"])
        self.assertIn("crowding_max_3", report["llm_context_ko"])

    def test_validate_report_keys(self) -> None:
        report = dict(FIXTURE)
        report["recommendations"] = derive_recommendations(FIXTURE["regimes"])
        report["llm_context_ko"] = format_llm_context_ko(report)
        validate_guard_regime_study_report(report)


if __name__ == "__main__":
    unittest.main()
