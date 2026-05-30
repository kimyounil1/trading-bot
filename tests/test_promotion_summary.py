"""Promotion summary CLI ([AGY])."""

import json
from pathlib import Path

from src.promotion_summary import (
    format_promotion_summary,
    load_promotion_report,
    promotion_gate_reference,
)


def test_promotion_gate_reference_has_defaults():
    gates = promotion_gate_reference()
    assert gates["ml_quality"]["min_avg_roc_auc"] == 0.51
    assert gates["portfolio_oos"]["max_drawdown_floor"] == -0.20


def test_format_promotion_summary_reject(tmp_path):
    report = {
        "decision": "RETAIN_CHAMPION",
        "auc_gate_passed": False,
        "ml_quality_gate_passed": True,
        "portfolio_gate_passed": True,
        "portfolio_vs_champion_passed": True,
        "reasons": ["challenger_avg_roc_auc=0.48 vs champion_avg_roc_auc=0.55"],
        "ml_quality_evaluation": {"failures": []},
        "portfolio_gate": {},
    }
    path = tmp_path / "model_promotion_report.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    loaded = load_promotion_report(path)
    text = format_promotion_summary(loaded)
    assert "RETAIN_CHAMPION" in text
    assert "0.48" in text
