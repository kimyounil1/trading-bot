"""Pure helpers for guard impact report (no backtest imports)."""

from __future__ import annotations

from typing import Any

GUARD_IMPACT_REPORT_KEYS = (
    "generated_at",
    "baseline",
    "with_crowding_guard",
    "delta",
    "crowding_guard_enabled_in_config",
)


def result_metrics(result) -> dict[str, Any]:
    return {
        "total_return_pct": round(float(result.total_return) * 100.0, 4),
        "max_drawdown_pct": round(float(result.max_drawdown) * 100.0, 4),
        "sharpe_ratio": round(float(result.sharpe_ratio), 4),
        "trade_count": int(result.trades),
        "win_rate_pct": round(float(result.win_rate) * 100.0, 4),
    }


def delta_metrics(baseline: dict[str, Any], guarded: dict[str, Any]) -> dict[str, Any]:
    return {
        key: round(guarded[key] - baseline[key], 4)
        for key in ("total_return_pct", "max_drawdown_pct", "sharpe_ratio", "trade_count", "win_rate_pct")
    }


def validate_guard_impact_report(report: dict[str, Any]) -> dict[str, Any]:
    for key in GUARD_IMPACT_REPORT_KEYS:
        if key not in report:
            raise ValueError(f"Missing guard impact report key: {key}")
    return report
