import pandas as pd

from src.paper_buy_validation_report import (
    build_audit_buy_path_comparison,
    build_rank_gate_paper_tracker,
)


def test_audit_buy_path_comparison_layers():
    audit = pd.DataFrame(
        [
            {
                "event_type": "SKIP_BUY",
                "reason": "ai score filter blocked (score=0.3, threshold=0.55)",
                "ai_score": 0.3,
                "llm_verdict": "",
            },
            {
                "event_type": "SKIP_BUY",
                "reason": "LLM Reject: macro risk",
                "ai_score": 0.7,
                "llm_verdict": "REJECT: macro",
            },
            {
                "event_type": "SKIP_BUY",
                "reason": "rank ai gate blocked (pct=0.50, cutoff=0.85)",
                "ai_score": 0.8,
                "llm_verdict": "ACCEPT: ok",
            },
            {
                "event_type": "BUY_SUBMITTED",
                "reason": "ok",
                "ai_score": 0.75,
                "llm_verdict": "ACCEPT: ok",
            },
        ]
    )
    report = build_audit_buy_path_comparison(
        audit, ai_threshold=0.55, llm_advisory_only=False
    )
    assert report["skip_buy_total"] == 3
    assert report["skip_ai_score_layer"] == 1
    assert report["skip_llm_block_layer"] == 1
    assert report["skip_rank_gate_layer"] == 1
    assert report["ai_pass_llm_block"] == 1
    assert report["buy_submitted"] == 1
    assert report["buy_submitted_llm_accept"] == 1


def test_rank_gate_paper_tracker_span():
    audit = pd.DataFrame(
        {
            "timestamp": [
                "2026-05-20T10:00:00Z",
                "2026-05-21T10:00:00Z",
                "2026-06-01T10:00:00Z",
            ],
            "event_type": ["SKIP_BUY", "BUY_SUBMITTED", "SKIP_BUY"],
            "reason": [
                "rank ai gate blocked (pct=0.1, cutoff=0.85)",
                "rank ai gate passed",
                "signal is HOLD",
            ],
        }
    )
    report = build_rank_gate_paper_tracker(audit, min_calendar_days=14)
    assert report["calendar_days_with_rank_events"] == 2
    assert report["total_skip_buy_rank_blocked"] == 1
    assert report["gate_ready"] is False
