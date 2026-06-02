"""Crowding live vs backtest alignment report ([AGY])."""

import json
from pathlib import Path

import pandas as pd
import pytest

from src.crowding_live_impact_report import build_crowding_live_impact_report
from src.crowding_live_metrics import (
    count_crowding_skips_from_reasons,
    crowding_skip_kind,
    is_crowding_skip_reason,
    summarize_crowding_skips_from_audit_df,
    validate_crowding_live_report,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "crowding_live"


def test_is_crowding_skip_reason():
    assert is_crowding_skip_reason("momentum crowding limit reached (peers=2)")
    assert not is_crowding_skip_reason("earnings filter: window")


def test_crowding_skip_kind():
    assert crowding_skip_kind("momentum crowding limit reached") == "momentum"
    assert crowding_skip_kind("trend crowding limit reached") == "trend"


def test_count_crowding_skips_from_reasons():
    counts = {"factor_crowding": 3, "stale_price_data": 1, "cooldown": 2}
    assert count_crowding_skips_from_reasons(counts) == 3


def test_build_report_with_fixtures():
    guard = json.loads((FIXTURES / "guard_impact_summary.json").read_text(encoding="utf-8"))
    audit = json.loads((FIXTURES / "audit_summary.json").read_text(encoding="utf-8"))
    report = build_crowding_live_impact_report(
        guard_impact=guard,
        audit_summary=audit,
        audit_df=None,
        lookback_days=7,
    )
    validate_crowding_live_report(report)
    assert report["live"]["crowding_skip_count"] >= 1
    assert report["alignment"]["live_observes_crowding_skips"] is True


def test_build_report_from_audit_rows():
    df = pd.read_csv(FIXTURES / "execution_audit_sample.csv")
    report = build_crowding_live_impact_report(
        guard_impact=None,
        audit_summary=None,
        audit_df=df,
        lookback_days=30,
    )
    assert report["live"]["crowding_skip_count"] == 2
    assert report["guard_impact_available"] is False


def test_summarize_crowding_skips_from_audit_df():
    df = pd.read_csv(FIXTURES / "execution_audit_sample.csv")
    summary = summarize_crowding_skips_from_audit_df(df)
    assert summary["crowding_skip_count"] == 2
    assert summary["by_kind"].get("momentum", 0) + summary["by_kind"].get("trend", 0) >= 1
