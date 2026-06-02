from pathlib import Path

from src.ops_report_presenter import summarize_report


def test_summarize_paper_validation_report():
    data = {
        "llm_ai_agreement": {"agreement_pct": 77.8, "comparable_with_ai_score": 81},
        "audit_buy_paths": {
            "skip_ai_score_layer": 16,
            "skip_llm_block_layer": 9,
            "skip_rank_gate_layer": 33,
            "ai_pass_llm_block": 9,
            "buy_submitted": 41,
        },
        "rank_gate_paper_tracker": {
            "calendar_days_with_rank_events": 4,
            "min_calendar_days_required": 14,
            "gate_ready": False,
        },
    }
    lines = summarize_report("paper_validation", data, source_path="logs/paper_validation/latest_summary.json")
    assert any("77.8" in line for line in lines)
    assert any("rank 33" in line.lower() or "rank 33" in line for line in lines)
    assert any("ready=False" in line for line in lines)
