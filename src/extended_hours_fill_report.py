"""Extended / overnight limit order fill-rate report for paper ops."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from src.alpaca_client import get_open_orders, get_recent_closed_orders, order_is_filled

DEFAULT_OUTPUT_DIR = Path("logs/paper_ops")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def _is_extended_limit_order(order: dict[str, Any]) -> bool:
    if not bool(order.get("extended_hours")):
        return False
    order_type = str(order.get("type", "")).upper()
    return "LIMIT" in order_type


def _order_in_lookback(order: dict[str, Any], *, since: datetime) -> bool:
    for key in ("submitted_at", "filled_at", "updated_at"):
        ts = _parse_ts(order.get(key))
        if ts is not None and ts >= since:
            return True
    return False


def build_extended_hours_fill_report(
    *,
    closed_orders: list[dict[str, Any]] | None = None,
    open_orders: list[dict[str, Any]] | None = None,
    lookback_days: int = 14,
) -> dict[str, Any]:
    since = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    closed_orders = closed_orders if closed_orders is not None else get_recent_closed_orders(limit=200)
    open_orders = open_orders if open_orders is not None else get_open_orders(limit=100)

    candidates: list[dict[str, Any]] = []
    for order in [*closed_orders, *open_orders]:
        if not _is_extended_limit_order(order):
            continue
        if not _order_in_lookback(order, since=since):
            continue
        candidates.append(order)

    filled = 0
    open_pending = 0
    canceled_or_other = 0
    partial = 0

    for order in candidates:
        status = str(order.get("status_simple") or order.get("status", "")).upper()
        if order_is_filled(status):
            filled += 1
        elif status in {"CANCELED", "CANCELLED", "EXPIRED", "REJECTED"}:
            canceled_or_other += 1
        elif status in {"NEW", "ACCEPTED", "PENDING_NEW", "OPEN"}:
            open_pending += 1
        elif "PARTIAL" in status:
            partial += 1
        else:
            canceled_or_other += 1

    total = len(candidates)
    terminal = filled + canceled_or_other
    fill_rate = (filled / terminal) if terminal > 0 else None

    return {
        "generated_at": _utc_now_iso(),
        "lookback_days": lookback_days,
        "extended_limit_orders": total,
        "filled": filled,
        "open_pending": open_pending,
        "partial": partial,
        "canceled_or_other": canceled_or_other,
        "fill_rate_terminal": round(fill_rate, 4) if fill_rate is not None else None,
        "status": "ok" if total else "no_data",
        "message": None if total else "no extended limit orders in lookback window",
    }


def write_extended_hours_fill_report(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    **kwargs: Any,
) -> Path:
    report = build_extended_hours_fill_report(**kwargs)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "extended_hours_fill_report.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Extended-hours limit fill-rate report")
    parser.add_argument("--lookback-days", type=int, default=14)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    path = write_extended_hours_fill_report(
        Path(args.output_dir),
        lookback_days=args.lookback_days,
    )
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
