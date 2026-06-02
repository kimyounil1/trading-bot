import json
from pathlib import Path

from src.paper_ops_summary import build_paper_ops_summary


def _rank_gate_fixture() -> dict:
    return {
        "generated_at": "2026-06-01T12:00:00Z",
        "gate": {
            "enabled": True,
            "min_score_quantile": 0.85,
        },
        "execution_audit": {
            "skip_buy_rank_blocked": 3,
            "buy_submitted": 7,
        },
        "candidate_cache": {
            "rank_blocked_rows": 2,
            "rank_passed_rows": 5,
        },
    }


def test_paper_ops_summary_includes_rank_ai_gate_block(tmp_path: Path) -> None:
    rank_path = tmp_path / "rank_ai_gate.json"
    rank_path.write_text(json.dumps(_rank_gate_fixture()), encoding="utf-8")

    report = build_paper_ops_summary(
        audit_path=tmp_path / "missing_audit.csv",
        llm_cache_path=tmp_path / "missing_cache.json",
        llm_advisory_path=tmp_path / "missing_advisory.json",
        crowding_gate_path=tmp_path / "missing_gate.json",
        crowding_live_path=tmp_path / "missing_live.json",
        rank_ai_gate_path=rank_path,
    )

    assert report["rank_ai_gate_path"] == str(rank_path)
    rank = report["rank_ai_gate"]
    assert rank["enabled"] is True
    assert rank["min_score_quantile"] == 0.85
    assert rank["skip_buy_rank_blocked"] == 3
    assert rank["buy_submitted"] == 7
    assert rank["cache_rank_blocked_rows"] == 2
    assert rank["cache_rank_passed_rows"] == 5


def test_paper_ops_summary_rank_ai_gate_defaults_when_missing(tmp_path: Path) -> None:
    report = build_paper_ops_summary(
        audit_path=tmp_path / "missing_audit.csv",
        llm_cache_path=tmp_path / "missing_cache.json",
        llm_advisory_path=tmp_path / "missing_advisory.json",
        crowding_gate_path=tmp_path / "missing_gate.json",
        crowding_live_path=tmp_path / "missing_live.json",
        rank_ai_gate_path=tmp_path / "missing_rank.json",
    )

    rank = report["rank_ai_gate"]
    assert rank["skip_buy_rank_blocked"] == 0
    assert rank["buy_submitted"] == 0
    assert rank["cache_rank_blocked_rows"] == 0
    assert rank["cache_rank_passed_rows"] == 0
