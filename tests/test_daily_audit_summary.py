from datetime import date

import pandas as pd

from src.daily_audit_summary import (
    aggregate_execution_audit,
    format_daily_audit_report,
    load_execution_audit,
    run_daily_audit_summary,
)


def _sample_audit_rows() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "timestamp": "2026-05-30T10:00:00+00:00",
                "event_type": "SKIP_BUY",
                "ticker": "AAPL",
                "reason": "stale price data for AAPL",
            },
            {
                "timestamp": "2026-05-30T10:05:00+00:00",
                "event_type": "SKIP_EXIT",
                "ticker": "MSFT",
                "reason": "dry_run_only",
            },
            {
                "timestamp": "2026-05-30T10:10:00+00:00",
                "event_type": "BUY_ERROR",
                "ticker": "GOOG",
                "reason": "API rate limit",
            },
            {
                "timestamp": "2026-05-30T10:15:00+00:00",
                "event_type": "BUY_SUBMITTED",
                "ticker": "NVDA",
                "reason": "",
            },
        ]
    )


def test_aggregate_execution_audit_counts():
    report = aggregate_execution_audit(_sample_audit_rows())
    assert report["row_count"] == 4
    assert report["skip_by_event"] == {"SKIP_BUY": 1, "SKIP_EXIT": 1}
    assert report["skip_reason_counts"]["stale_price_data"] == 1
    assert report["api_error_count"] == 1
    assert report["stale_bar_count"] >= 1
    assert report["orders_submitted_count"] == 1
    assert "context_skip_counts" in report


def test_format_daily_audit_report_includes_key_lines():
    report = aggregate_execution_audit(_sample_audit_rows())
    text = format_daily_audit_report(report)
    assert "API errors: 1" in text
    assert "stale_price_data" in text or "Stale bar" in text


def test_load_execution_audit_filters_by_day(tmp_path):
    path = tmp_path / "execution_audit.csv"
    _sample_audit_rows().to_csv(path, index=False)
    df = load_execution_audit(path, day=date(2026, 5, 30))
    assert len(df) == 4
    df_empty = load_execution_audit(path, day=date(2026, 1, 1))
    assert df_empty.empty


def test_run_daily_audit_summary_writes_artifacts(tmp_path):
    audit = tmp_path / "audit.csv"
    out = tmp_path / "daily"
    _sample_audit_rows().to_csv(audit, index=False)
    report = run_daily_audit_summary(
        audit_path=audit,
        output_dir=out,
        day=date(2026, 5, 30),
    )
    assert report["row_count"] == 4
    assert (out / "latest_summary.json").is_file()
    assert list(out.glob("audit_*.json"))
