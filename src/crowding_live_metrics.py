"""Pure helpers: live audit crowding skips vs backtest guard-impact deltas."""

from __future__ import annotations

from typing import Any

CROWDING_LIVE_REPORT_KEYS = (
    "generated_at",
    "guard_impact_available",
    "audit_available",
    "backtest",
    "live",
    "alignment",
)


def is_crowding_skip_reason(reason: str) -> bool:
    lower = str(reason or "").lower()
    return "crowding" in lower


def count_crowding_skips_from_reasons(skip_reason_counts: dict[str, int] | None) -> int:
    if not skip_reason_counts:
        return 0
    total = 0
    for reason, count in skip_reason_counts.items():
        if is_crowding_skip_reason(reason) or reason == "factor_crowding":
            total += int(count)
    return total


def count_crowding_skips_from_audit_rows(reasons: list[str]) -> tuple[int, list[str]]:
    samples: list[str] = []
    count = 0
    for reason in reasons:
        if is_crowding_skip_reason(reason):
            count += 1
            if len(samples) < 5:
                samples.append(str(reason)[:120])
    return count, samples


def build_alignment_notes(
    *,
    backtest_delta_trades: int | None,
    live_crowding_skips: int,
    guard_enabled_in_config: bool,
) -> dict[str, Any]:
    backtest_reduces_trades = (
        backtest_delta_trades is not None and backtest_delta_trades < 0
    )
    live_observes = live_crowding_skips > 0
    notes: list[str] = []
    if not guard_enabled_in_config and live_observes:
        notes.append(
            "Live audit shows crowding skips but config has crowding_guard_enabled=false; "
            "skips may be from risk_reason text on other paths or historical runs."
        )
    if guard_enabled_in_config and not live_observes and backtest_reduces_trades:
        notes.append(
            "Backtest shows fewer trades with guard on, but no crowding-tagged skips in audit window."
        )
    if backtest_reduces_trades and live_observes:
        notes.append("Backtest trade reduction aligns with live crowding skip activity.")
    if not notes:
        notes.append("Insufficient signal for strong alignment; extend audit window or enable guard in paper.")
    return {
        "backtest_reduces_trades": backtest_reduces_trades,
        "live_observes_crowding_skips": live_observes,
        "notes": notes,
    }


def validate_crowding_live_report(report: dict[str, Any]) -> dict[str, Any]:
    for key in CROWDING_LIVE_REPORT_KEYS:
        if key not in report:
            raise ValueError(f"Missing crowding live report key: {key}")
    return report
