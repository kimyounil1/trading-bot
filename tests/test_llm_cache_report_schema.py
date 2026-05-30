"""Schema regression for LLM cache monitoring ([AGY])."""

import json
from pathlib import Path

import pytest

from src.llm_cache_report import (
    LLM_CACHE_REPORT_KEYS,
    build_llm_cache_report,
    validate_llm_cache_report,
)

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "llm_monitoring"
GOLDEN_CACHE = FIXTURE_DIR / "golden_llm_cache.json"


def test_golden_llm_cache_report_schema():
    report = build_llm_cache_report(GOLDEN_CACHE)
    validate_llm_cache_report(report)
    for key in LLM_CACHE_REPORT_KEYS:
        assert key in report
    assert report["entry_count"] == 3
    assert report["unique_tickers"] == 2
    assert report["approved_count"] == 2
    assert report["rejected_count"] == 1


def test_empty_cache_report():
    report = build_llm_cache_report(FIXTURE_DIR / "missing_cache.json")
    assert report["entry_count"] == 0
    assert report["estimated_cache_hit_rate"] == 0.0
