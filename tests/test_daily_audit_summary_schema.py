"""Schema regression for daily audit artifacts ([AGY])."""

import json
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from src.daily_audit_summary import (
    DAILY_AUDIT_SUMMARY_KEYS,
    SKIP_REASONS_CSV_COLUMNS,
    aggregate_execution_audit,
    run_daily_audit_summary,
    validate_daily_audit_summary,
    validate_skip_reasons_csv,
    write_daily_audit_artifacts,
)

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "audit_daily"
GOLDEN_AUDIT_CSV = FIXTURE_DIR / "golden_execution_audit.csv"
GOLDEN_SUMMARY_JSON = FIXTURE_DIR / "golden_latest_summary.json"


@pytest.fixture(scope="module", autouse=True)
def build_golden_summary_fixture():
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(GOLDEN_AUDIT_CSV)
    report = aggregate_execution_audit(df)
    report["generated_at"] = "2026-05-30T12:00:00Z"
    validate_daily_audit_summary(report)
    GOLDEN_SUMMARY_JSON.write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    write_daily_audit_artifacts(
        report,
        FIXTURE_DIR / "golden_output",
        day=date(2026, 5, 30),
    )
    yield report


def test_golden_execution_audit_context_skip_rates():
    df = pd.read_csv(GOLDEN_AUDIT_CSV)
    report = aggregate_execution_audit(df)
    assert report["context_skip_counts"]["earnings"] == 1
    assert report["context_skip_counts"]["macro_event"] == 1
    assert report["context_skip_counts"]["stale"] == 1
    assert report["context_skip_counts"]["other"] == 1
    assert report["api_error_count"] == 1
    assert sum(report["context_skip_rate_of_skips"].values()) == pytest.approx(1.0, abs=1e-3)


def test_golden_latest_summary_schema():
    report = json.loads(GOLDEN_SUMMARY_JSON.read_text(encoding="utf-8"))
    validate_daily_audit_summary(report)
    for key in DAILY_AUDIT_SUMMARY_KEYS:
        assert key in report


def test_golden_skip_reasons_csv_schema():
    skip_csv = FIXTURE_DIR / "golden_output" / "skip_reasons_20260530.csv"
    frame = validate_skip_reasons_csv(skip_csv)
    assert list(frame.columns) == list(SKIP_REASONS_CSV_COLUMNS)


def test_run_daily_audit_summary_matches_golden_counts(tmp_path):
    out = tmp_path / "out"
    report = run_daily_audit_summary(
        audit_path=GOLDEN_AUDIT_CSV,
        output_dir=out,
        day=date(2026, 5, 30),
    )
    golden = json.loads(GOLDEN_SUMMARY_JSON.read_text(encoding="utf-8"))
    for key in (
        "row_count",
        "api_error_count",
        "stale_bar_count",
        "context_skip_counts",
        "skip_by_event",
    ):
        assert report[key] == golden[key]
