import json

from src.paper_validation_trend import build_paper_validation_trend_report


def test_paper_validation_trend_alerts(tmp_path):
    history = tmp_path / "history.jsonl"
    rows = [
        {
            "date": "2026-06-01",
            "generated_at": "2026-06-01T09:00:00Z",
            "agreement_pct": 80.0,
            "skip_ai_score": 10,
            "skip_llm_block": 4,
            "skip_rank_gate": 10,
            "buy_submitted": 20,
            "rank_calendar_days": 3,
            "rank_gate_ready": False,
        },
        {
            "date": "2026-06-02",
            "generated_at": "2026-06-02T09:00:00Z",
            "agreement_pct": 65.0,
            "skip_ai_score": 11,
            "skip_llm_block": 12,
            "skip_rank_gate": 11,
            "buy_submitted": 18,
            "rank_calendar_days": 14,
            "rank_gate_ready": True,
        },
    ]
    history.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")

    report = build_paper_validation_trend_report(history_path=history, rolling_days=7)
    assert report["rows"] == 2
    assert report["latest"]["rank_gate_ready"] is True
    assert "rank_gate_ready_flip_true" in report["alerts"]
    assert "skip_llm_block_spike" in report["alerts"]


def test_paper_validation_trend_rank_gate_spike(tmp_path):
    history = tmp_path / "history.jsonl"
    rows = [
        {
            "date": "2026-06-01",
            "agreement_pct": 80.0,
            "skip_rank_gate": 40,
            "skip_llm_block": 4,
            "buy_submitted": 20,
            "rank_gate_ready": False,
        },
        {
            "date": "2026-06-02",
            "agreement_pct": 65.0,
            "skip_rank_gate": 152,
            "skip_llm_block": 12,
            "buy_submitted": 61,
            "rank_gate_ready": False,
        },
    ]
    history.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")

    report = build_paper_validation_trend_report(history_path=history, rolling_days=7)
    assert "skip_rank_gate_spike" in report["alerts"]


def test_paper_validation_trend_empty_history(tmp_path):
    report = build_paper_validation_trend_report(history_path=tmp_path / "missing.jsonl")
    assert report["rows"] == 0
    assert "No history rows yet." in report["notes"][0]
