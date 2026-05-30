"""Leverage stress alert thresholds ([AGY])."""

from pathlib import Path

from src.leverage_stress_report import (
    LEVERAGE_STRESS_ALERT_KEYS,
    build_leverage_stress_report,
    evaluate_leverage_stress_alerts,
    load_equity_series,
)

FIXTURE_EQUITY = (
    Path(__file__).resolve().parent / "fixtures" / "portfolio_backtest" / "portfolio_equity.csv"
)


def test_leverage_stress_alerts_pass_on_fixture_equity():
    equity = load_equity_series(FIXTURE_EQUITY)
    report = build_leverage_stress_report(equity, leverage=1.0)
    alerts = evaluate_leverage_stress_alerts(
        report,
        leverage=1.0,
        config={
            "alert_if_stressed_drawdown_below_pct": -99.0,
            "alert_if_gap10_final_equity_loss_below_pct": -99.0,
        },
    )
    for key in LEVERAGE_STRESS_ALERT_KEYS:
        assert key in alerts
    assert alerts["passed"] is True


def test_leverage_stress_alerts_fail_on_strict_thresholds():
    equity = load_equity_series(FIXTURE_EQUITY)
    report = build_leverage_stress_report(equity, leverage=3.0)
    alerts = evaluate_leverage_stress_alerts(
        report,
        leverage=3.0,
        config={
            "alert_if_stressed_drawdown_below_pct": -5.0,
            "alert_if_gap10_final_equity_loss_below_pct": -1.0,
        },
    )
    assert alerts["passed"] is False
    assert alerts["failures"]
