"""LLM advisory report parses execution_audit verdicts."""

from src.llm_advisory_impact_report import _parse_llm_verdict, build_llm_advisory_impact_report
from src.trading.bot_helpers import format_llm_verdict


def test_parse_llm_verdict():
    side, reason = _parse_llm_verdict("REJECT: [Fraud] risk noted")
    assert side == "REJECT"
    assert "Fraud" in reason


def test_format_llm_verdict_compacts_long_reason():
    long_reason = "line one\nline two  spaced\n" + "x" * 1000
    verdict = format_llm_verdict(False, long_reason)
    assert verdict.startswith("REJECT: line one line two spaced")
    assert "\n" not in verdict
    assert len(verdict) <= len("REJECT: ") + 501


def test_format_llm_verdict_none_and_plain():
    assert format_llm_verdict(None, "anything") == ""
    assert format_llm_verdict(True) == "ACCEPT"
    assert format_llm_verdict(True, "ok") == "ACCEPT: ok"


def test_advisory_report_empty_audit(tmp_path):
    report = build_llm_advisory_impact_report(tmp_path / "missing.csv")
    assert report["rows"] == 0
