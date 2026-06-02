"""Ops dashboard human summaries."""

import json
from pathlib import Path

from src.ops_report_presenter import summarize_report

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "crowding_live"


def test_summarize_guard_impact():
    data = json.loads((FIXTURES / "guard_impact_summary.json").read_text(encoding="utf-8"))
    lines = summarize_report("guard_impact", data, source_path="fixture")
    assert any("수익" in line for line in lines)
    assert any("샤프" in line for line in lines)
