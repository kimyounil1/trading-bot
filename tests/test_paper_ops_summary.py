from pathlib import Path

from src.paper_ops_summary import build_paper_ops_summary


def test_paper_ops_summary_empty_paths(tmp_path):
    report = build_paper_ops_summary(
        audit_path=tmp_path / "missing.csv",
        llm_cache_path=tmp_path / "missing.json",
        llm_advisory_path=tmp_path / "missing_advisory.json",
        crowding_gate_path=tmp_path / "missing_gate.json",
        crowding_live_path=tmp_path / "missing_live.json",
        crowding_reassess_path=tmp_path / "missing_reassess.json",
    )
    assert report["execution_audit_rows"] == 0
    assert report["llm_cache_keys"] == 0
    assert report["crowding_decision"] is None
    assert isinstance(report["crowding_config_applied"], bool)
    assert report["crowding_live"]["crowding_skip_count"] == 0
    assert report["crowding_reassessment"]["recommendation"] is None
