"""Leverage stress scenario math ([AGY])."""

from pathlib import Path

import pandas as pd
import pytest

from src.leverage_stress_report import (
    LEVERAGE_STRESS_REPORT_KEYS,
    build_leverage_stress_report,
    load_equity_series,
    validate_leverage_stress_report,
)

FIXTURE_EQUITY = (
    Path(__file__).resolve().parent / "fixtures" / "portfolio_backtest" / "portfolio_equity.csv"
)


def test_load_equity_series_from_fixture():
    series = load_equity_series(FIXTURE_EQUITY)
    assert len(series) > 10
    assert series.iloc[-1] > series.iloc[0]


def test_leverage_stress_report_schema_and_worsens_under_gap():
    equity = load_equity_series(FIXTURE_EQUITY)
    report = build_leverage_stress_report(equity, leverage=2.0)
    validate_leverage_stress_report(report)
    for key in LEVERAGE_STRESS_REPORT_KEYS:
        assert key in report
    gap10 = next(row for row in report["scenarios"] if row["name"] == "gap_down_10pct")
    assert gap10["max_drawdown_pct"] <= report["input"]["baseline_max_drawdown_pct"]


def test_leverage_must_be_positive():
    equity = pd.Series([100.0, 101.0, 99.0])
    with pytest.raises(ValueError, match="leverage"):
        build_leverage_stress_report(equity, leverage=0.0)
