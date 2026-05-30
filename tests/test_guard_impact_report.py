"""Guard impact report schema and delta helpers ([AGY])."""

from types import SimpleNamespace

from src.guard_impact_metrics import (
    GUARD_IMPACT_REPORT_KEYS,
    delta_metrics,
    result_metrics,
    validate_guard_impact_report,
)


def test_result_metrics_and_delta():
    baseline = SimpleNamespace(
        total_return=0.10,
        max_drawdown=-0.08,
        sharpe_ratio=1.1,
        trades=20,
        win_rate=0.55,
    )
    guarded = SimpleNamespace(
        total_return=0.08,
        max_drawdown=-0.07,
        sharpe_ratio=1.0,
        trades=17,
        win_rate=0.52,
    )
    base = result_metrics(baseline)
    guard = result_metrics(guarded)
    delta = delta_metrics(base, guard)
    assert delta["trade_count"] == -3
    assert base["total_return_pct"] == 10.0


def test_validate_guard_impact_report_keys():
    report = {
        "generated_at": "2026-05-30T00:00:00Z",
        "baseline": {},
        "with_crowding_guard": {},
        "delta": {},
        "crowding_guard_enabled_in_config": False,
    }
    validate_guard_impact_report(report)
    for key in GUARD_IMPACT_REPORT_KEYS:
        assert key in report
