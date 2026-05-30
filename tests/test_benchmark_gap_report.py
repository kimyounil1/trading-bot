"""Benchmark gap decomposition ([AGY])."""

from pathlib import Path

from src.benchmark_gap_report import (
    BENCHMARK_GAP_REPORT_KEYS,
    build_benchmark_gap_report,
    validate_benchmark_gap_report,
)

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "portfolio_backtest"


def test_benchmark_gap_report_from_fixture():
    report = build_benchmark_gap_report(FIXTURE_DIR)
    validate_benchmark_gap_report(report)
    for key in BENCHMARK_GAP_REPORT_KEYS:
        assert key in report
    assert report["gap_pct"] < 0
    assert len(report["by_sector"]) >= 1
    assert len(report["by_ticker"]) >= 1
