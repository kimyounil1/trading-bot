"""LLM advisory report parses execution_audit verdicts."""

from src.llm_advisory_impact_report import _parse_llm_verdict, build_llm_advisory_impact_report


def test_parse_llm_verdict():
    side, reason = _parse_llm_verdict("REJECT: [Fraud] risk noted")
    assert side == "REJECT"
    assert "Fraud" in reason


def test_advisory_report_empty_audit(tmp_path):
    report = build_llm_advisory_impact_report(tmp_path / "missing.csv")
    assert report["rows"] == 0
