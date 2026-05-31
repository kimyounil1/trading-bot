"""Aggregate daily execution audit logs (skips, API errors, stale data)."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import EXECUTION_AUDIT_LOG_PATH

DEFAULT_OUTPUT_DIR = Path("logs/audit_daily")

SKIP_EVENT_TYPES = frozenset({"SKIP_BUY", "SKIP_EXIT"})
API_ERROR_EVENT_TYPES = frozenset({"BUY_ERROR", "EXIT_ERROR"})
ORDER_SUBMITTED_EVENT_TYPES = frozenset({"BUY_SUBMITTED", "FULL_EXIT", "PARTIAL_EXIT"})

DAILY_AUDIT_SUMMARY_KEYS = (
    "generated_at",
    "row_count",
    "event_type_counts",
    "skip_by_event",
    "skip_reason_counts",
    "api_error_count",
    "api_error_samples",
    "stale_bar_count",
    "orders_submitted_count",
    "unique_tickers",
    "context_skip_counts",
    "context_skip_rate_of_skips",
)

SKIP_REASONS_CSV_COLUMNS = ("reason", "count")

CONTEXT_SKIP_BUCKETS = ("earnings", "macro_event", "stale", "other")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_audit_timestamps(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce", utc=True)


def load_execution_audit(
    audit_path: str | Path = EXECUTION_AUDIT_LOG_PATH,
    *,
    day: date | None = None,
    lookback_days: int | None = None,
) -> pd.DataFrame:
    path = Path(audit_path)
    if not path.is_file():
        return pd.DataFrame()

    df = pd.read_csv(path)
    if df.empty or "timestamp" not in df.columns:
        return df

    df = df.copy()
    df["_ts"] = _parse_audit_timestamps(df["timestamp"])
    df = df.dropna(subset=["_ts"])

    if day is not None:
        start = pd.Timestamp(day, tz="UTC")
        end = start + pd.Timedelta(days=1)
        df = df[(df["_ts"] >= start) & (df["_ts"] < end)]
    elif lookback_days is not None and lookback_days > 0:
        cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=lookback_days)
        df = df[df["_ts"] >= cutoff]

    return df.drop(columns=["_ts"])


def _normalize_skip_reason(reason: str) -> str:
    text = str(reason or "").strip()
    if not text:
        return "unknown"
    lower = text.lower()
    if "stale" in lower:
        return "stale_price_data"
    if "dry_run" in lower or "dry-run" in lower:
        return "dry_run_only"
    if "cooldown" in lower:
        return "cooldown"
    if "crowding" in lower:
        return "factor_crowding"
    if "max orders" in lower:
        return "max_orders"
    if "regime" in lower or "bear" in lower:
        return "regime_or_signal"
    if "llm" in lower or "reject" in lower:
        return "llm_or_policy"
    return text[:80]


def _classify_context_skip(reason: str) -> str:
    lower = str(reason or "").lower()
    if "earnings" in lower:
        return "earnings"
    if "macro event" in lower or "macro_event" in lower:
        return "macro_event"
    if "stale" in lower:
        return "stale"
    return "other"


def aggregate_context_skips(df: pd.DataFrame) -> tuple[dict[str, int], dict[str, float]]:
    if df is None or df.empty or "event_type" not in df.columns:
        empty = {bucket: 0 for bucket in CONTEXT_SKIP_BUCKETS}
        return empty, {bucket: 0.0 for bucket in CONTEXT_SKIP_BUCKETS}

    event_types = df["event_type"].astype(str)
    reasons = df["reason"].astype(str) if "reason" in df.columns else pd.Series(dtype=str)
    skip_mask = event_types.isin(SKIP_EVENT_TYPES)
    skip_reasons = reasons[skip_mask].tolist()
    counts = Counter(_classify_context_skip(r) for r in skip_reasons)
    total_skips = max(len(skip_reasons), 1)
    context_counts = {bucket: int(counts.get(bucket, 0)) for bucket in CONTEXT_SKIP_BUCKETS}
    context_rates = {
        bucket: round(context_counts[bucket] / total_skips, 4) for bucket in CONTEXT_SKIP_BUCKETS
    }
    return context_counts, context_rates


def validate_daily_audit_summary(report: dict[str, Any]) -> dict[str, Any]:
    for key in DAILY_AUDIT_SUMMARY_KEYS:
        if key not in report:
            raise ValueError(f"Missing daily audit summary key: {key}")
    if not isinstance(report["row_count"], int) or report["row_count"] < 0:
        raise ValueError("row_count must be a non-negative int")
    if not isinstance(report["api_error_count"], int) or report["api_error_count"] < 0:
        raise ValueError("api_error_count must be a non-negative int")
    for bucket in CONTEXT_SKIP_BUCKETS:
        if bucket not in report["context_skip_counts"]:
            raise ValueError(f"Missing context skip bucket: {bucket}")
    return report


def validate_skip_reasons_csv(path: str | Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    missing = [col for col in SKIP_REASONS_CSV_COLUMNS if col not in frame.columns]
    if missing:
        raise ValueError(f"skip_reasons CSV missing columns: {missing}")
    if (frame["count"] < 0).any():
        raise ValueError("skip_reasons count must be non-negative")
    return frame


def aggregate_execution_audit(df: pd.DataFrame) -> dict[str, Any]:
    if df is None or df.empty:
        return {
            "generated_at": _utc_now_iso(),
            "row_count": 0,
            "event_type_counts": {},
            "skip_by_event": {},
            "skip_reason_counts": {},
            "api_error_count": 0,
            "api_error_samples": [],
            "stale_bar_count": 0,
            "orders_submitted_count": 0,
            "unique_tickers": 0,
            "context_skip_counts": {bucket: 0 for bucket in CONTEXT_SKIP_BUCKETS},
            "context_skip_rate_of_skips": {bucket: 0.0 for bucket in CONTEXT_SKIP_BUCKETS},
        }

    event_types = df["event_type"].astype(str) if "event_type" in df.columns else pd.Series(dtype=str)
    reasons = df["reason"].astype(str) if "reason" in df.columns else pd.Series(dtype=str)

    skip_mask = event_types.isin(SKIP_EVENT_TYPES)
    skip_reasons = Counter(
        _normalize_skip_reason(r) for r in reasons[skip_mask].tolist()
    )
    skip_by_event = Counter(event_types[skip_mask].tolist())

    api_mask = event_types.isin(API_ERROR_EVENT_TYPES)
    api_error_count = int(api_mask.sum())

    stale_mask = reasons.str.contains("stale", case=False, na=False)
    stale_bar_count = int(stale_mask.sum())

    orders_submitted = int(event_types.isin(ORDER_SUBMITTED_EVENT_TYPES).sum())
    tickers = df["ticker"].astype(str).nunique() if "ticker" in df.columns else 0

    api_samples = (
        df.loc[api_mask, ["timestamp", "event_type", "ticker", "reason"]]
        .head(10)
        .to_dict(orient="records")
        if api_mask.any()
        else []
    )
    context_counts, context_rates = aggregate_context_skips(df)

    return {
        "generated_at": _utc_now_iso(),
        "row_count": int(len(df)),
        "event_type_counts": dict(Counter(event_types.tolist())),
        "skip_by_event": dict(skip_by_event),
        "skip_reason_counts": dict(skip_reasons.most_common()),
        "api_error_count": api_error_count,
        "api_error_samples": api_samples,
        "stale_bar_count": stale_bar_count,
        "orders_submitted_count": orders_submitted,
        "unique_tickers": int(tickers),
        "context_skip_counts": context_counts,
        "context_skip_rate_of_skips": context_rates,
    }


def format_daily_audit_report(report: dict[str, Any]) -> str:
    lines = [
        "=== Daily Execution Audit Summary ===",
        f"Rows: {report.get('row_count', 0)} | Tickers: {report.get('unique_tickers', 0)}",
        f"Orders submitted (buy/exit events): {report.get('orders_submitted_count', 0)}",
        f"API errors: {report.get('api_error_count', 0)} | Stale bar mentions: {report.get('stale_bar_count', 0)}",
    ]
    skip_by = report.get("skip_by_event") or {}
    if skip_by:
        lines.append("Skips by event: " + ", ".join(f"{k}={v}" for k, v in sorted(skip_by.items())))
    skip_reasons = report.get("skip_reason_counts") or {}
    if skip_reasons:
        top = ", ".join(f"{k}={v}" for k, v in list(skip_reasons.items())[:8])
        lines.append(f"Top skip reasons: {top}")
    context = report.get("context_skip_counts") or {}
    if any(context.values()):
        lines.append(
            "Context skips: "
            + ", ".join(f"{k}={v}" for k, v in sorted(context.items()) if v)
        )
    return "\n".join(lines)


def write_daily_audit_artifacts(
    report: dict[str, Any],
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    *,
    day: date | None = None,
) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = (day or date.today()).strftime("%Y%m%d")
    day_path = output_dir / f"audit_{stamp}.json"
    day_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    latest = output_dir / "latest_summary.json"
    latest.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    if report.get("skip_reason_counts"):
        pd.DataFrame(
            [{"reason": k, "count": v} for k, v in report["skip_reason_counts"].items()]
        ).to_csv(output_dir / f"skip_reasons_{stamp}.csv", index=False)
    return day_path


def run_daily_audit_summary(
    *,
    audit_path: str | Path = EXECUTION_AUDIT_LOG_PATH,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    day: date | None = None,
    lookback_days: int | None = None,
) -> dict[str, Any]:
    df = load_execution_audit(audit_path, day=day, lookback_days=lookback_days)
    report = aggregate_execution_audit(df)
    validate_daily_audit_summary(report)
    write_daily_audit_artifacts(report, output_dir, day=day or date.today())
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Daily execution audit aggregation")
    parser.add_argument("--audit-path", default=EXECUTION_AUDIT_LOG_PATH)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--date", help="UTC date YYYY-MM-DD (default: today)")
    parser.add_argument("--days", type=int, help="Lookback days instead of single day")
    args = parser.parse_args()

    day = None
    if args.date:
        day = date.fromisoformat(args.date)
    lookback = args.days if not args.date else None

    report = run_daily_audit_summary(
        audit_path=args.audit_path,
        output_dir=args.output_dir,
        day=day,
        lookback_days=lookback,
    )
    print(format_daily_audit_report(report))
    print(f"\nWrote summary under {args.output_dir}")


if __name__ == "__main__":
    main()
