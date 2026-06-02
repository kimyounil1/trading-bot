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


def crowding_skip_kind(reason: str) -> str:
    lower = str(reason or "").lower()
    if "momentum crowding" in lower:
        return "momentum"
    if "trend crowding" in lower:
        return "trend"
    return "other"


def count_crowding_skips_from_audit_rows(reasons: list[str]) -> tuple[int, list[str]]:
    samples: list[str] = []
    count = 0
    for reason in reasons:
        if is_crowding_skip_reason(reason):
            count += 1
            if len(samples) < 5:
                samples.append(str(reason)[:120])
    return count, samples


def summarize_crowding_skips_from_audit_df(audit_df) -> dict[str, Any]:
    """Aggregate crowding SKIP_BUY rows from execution_audit (ticker + kind)."""
    import pandas as pd

    empty: dict[str, Any] = {
        "crowding_skip_count": 0,
        "skip_buy_count": 0,
        "crowding_skip_rate_of_skips": 0.0,
        "by_kind": {},
        "by_ticker": {},
        "sample_reasons": [],
        "window_start": None,
        "window_end": None,
    }
    if audit_df is None or audit_df.empty:
        return empty

    df = audit_df.copy()
    if "event_type" not in df.columns:
        return empty
    event_types = df["event_type"].astype(str)
    skip_mask = event_types == "SKIP_BUY"
    skip_df = df[skip_mask]
    reasons = skip_df["reason"].astype(str) if "reason" in skip_df.columns else pd.Series(dtype=str)
    crowding_mask = reasons.map(is_crowding_skip_reason)
    crowd_df = skip_df[crowding_mask]

    count, samples = count_crowding_skips_from_audit_rows(reasons[skip_mask].tolist())
    by_kind: dict[str, int] = {}
    for reason in crowd_df.get("reason", pd.Series(dtype=str)):
        kind = crowding_skip_kind(str(reason))
        by_kind[kind] = by_kind.get(kind, 0) + 1

    by_ticker: dict[str, int] = {}
    if "ticker" in crowd_df.columns:
        for ticker, n in crowd_df["ticker"].astype(str).str.upper().value_counts().items():
            by_ticker[str(ticker)] = int(n)

    window_start = window_end = None
    if "timestamp" in df.columns:
        ts = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
        if ts.notna().any():
            window_start = ts.min().strftime("%Y-%m-%dT%H:%M:%SZ")
            window_end = ts.max().strftime("%Y-%m-%dT%H:%M:%SZ")

    skip_buy_count = int(skip_mask.sum())
    rate = round(count / skip_buy_count, 4) if skip_buy_count else 0.0
    return {
        "crowding_skip_count": count,
        "skip_buy_count": skip_buy_count,
        "crowding_skip_rate_of_skips": rate,
        "by_kind": by_kind,
        "by_ticker": by_ticker,
        "sample_reasons": samples,
        "window_start": window_start,
        "window_end": window_end,
    }


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
