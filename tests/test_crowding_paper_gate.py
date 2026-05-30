from pathlib import Path

from src.crowding_paper_gate import (
    evaluate_crowding_paper_gate,
    load_guard_impact_summary,
    validate_crowding_gate_report,
)

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "guard_impact" / "latest_summary.json"


def test_crowding_paper_gate_go():
    report = validate_crowding_gate_report(
        evaluate_crowding_paper_gate(load_guard_impact_summary(FIXTURE))
    )
    assert report["decision"] == "GO_PAPER"
    assert all(item["pass"] for item in report["checklist"])
