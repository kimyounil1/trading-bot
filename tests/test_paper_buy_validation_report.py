import json

import pandas as pd

from src.paper_buy_validation_report import (
    append_paper_validation_history,
    build_audit_buy_path_comparison,
    build_rank_gate_paper_tracker,
    paper_validation_history_row,
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


def test_paper_validation_history_upserts_same_day(tmp_path):
    report = {
        "generated_at": "2026-06-02T12:00:00Z",
        "llm_ai_agreement": {"agreement_pct": 70.0},
        "audit_buy_paths": {
            "skip_ai_score_layer": 1,
            "skip_llm_block_layer": 2,
            "skip_rank_gate_layer": 3,
            "buy_submitted": 4,
        },
        "rank_gate_paper_tracker": {
            "calendar_days_with_rank_events": 5,
            "gate_ready": False,
        },
    }
    row = paper_validation_history_row(report)
    assert row["date"] == "2026-06-02"
    assert row["agreement_pct"] == 70.0
    assert row["skip_rank_gate"] == 3

    path = append_paper_validation_history(report, output_dir=tmp_path)
    report["llm_ai_agreement"]["agreement_pct"] = 75.0
    append_paper_validation_history(report, output_dir=tmp_path)
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1
    assert json.loads(lines[0])["agreement_pct"] == 75.0


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
