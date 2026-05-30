"""Weekly alignment: paper slippage vs execution audit skip patterns."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_OUTPUT_DIR = Path("logs/execution_alignment")
AUDIT_LATEST = Path("logs/audit_daily/latest_summary.json")
SLIPPAGE_LATEST = Path("logs/slippage_reports/latest_summary.json")

EXECUTION_ALIGNMENT_REPORT_KEYS = (
    "generated_at",
    "current",
    "previous",
    "week_over_week",
    "notes",
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _skip_total(context_counts: dict[str, Any] | None) -> int:
    if not context_counts:
        return 0
    return int(sum(int(v) for v in context_counts.values()))


def _alignment_snapshot(
    audit: dict[str, Any] | None,
    slippage: dict[str, Any] | None,
) -> dict[str, Any]:
    audit = audit or {}
    slippage = slippage or {}
    return {
        "audit_row_count": int(audit.get("row_count", 0)),
        "audit_api_errors": int(audit.get("api_error_count", 0)),
        "audit_stale_bars": int(audit.get("stale_bar_count", 0)),
        "context_skip_total": _skip_total(audit.get("context_skip_counts")),
        "context_skip_counts": audit.get("context_skip_counts") or {},
        "slippage_status": slippage.get("status"),
        "slippage_matched_trades": int(slippage.get("matched_trades", 0) or 0),
        "slippage_avg_pct": float(slippage.get("overall_avg_slippage_pct", 0.0) or 0.0),
        "slippage_total_usd": float(slippage.get("total_slippage_usd", 0.0) or 0.0),
    }


def build_execution_alignment_report(
    *,
    audit_path: Path = AUDIT_LATEST,
    slippage_path: Path = SLIPPAGE_LATEST,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    previous_path = output_dir / "previous_snapshot.json"

    current = _alignment_snapshot(_load_json(audit_path), _load_json(slippage_path))
    previous = _load_json(previous_path) or {}

    wow: dict[str, Any] = {}
    if previous:
        for key in (
            "audit_row_count",
            "audit_api_errors",
            "audit_stale_bars",
            "context_skip_total",
            "slippage_matched_trades",
            "slippage_avg_pct",
        ):
            wow[key] = round(float(current.get(key, 0)) - float(previous.get(key, 0)), 4)

    notes: list[str] = []
    if not previous:
        notes.append("No previous snapshot; week-over-week diff starts next run.")
    if current.get("slippage_status") == "no_data":
        notes.append("Slippage report has no_data; run weekly slippage after paper fills.")
    if current.get("audit_row_count", 0) == 0:
        notes.append("Execution audit empty; bot may not have run or log path differs.")

    report = {
        "generated_at": _utc_now_iso(),
        "current": current,
        "previous": previous,
        "week_over_week": wow,
        "notes": notes,
    }
    validate_execution_alignment_report(report)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    (output_dir / f"alignment_{stamp}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    previous_path.write_text(json.dumps(current, indent=2, sort_keys=True), encoding="utf-8")
    (output_dir / "latest_summary.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return report


def validate_execution_alignment_report(report: dict[str, Any]) -> dict[str, Any]:
    for key in EXECUTION_ALIGNMENT_REPORT_KEYS:
        if key not in report:
            raise ValueError(f"Missing execution alignment report key: {key}")
    return report


def format_execution_alignment_report(report: dict[str, Any]) -> str:
    cur = report["current"]
    lines = [
        "=== Execution alignment (audit vs paper slippage) ===",
        f"Audit rows: {cur.get('audit_row_count')} | API errors: {cur.get('audit_api_errors')} | Stale: {cur.get('audit_stale_bars')}",
        f"Context skips: {cur.get('context_skip_total')} {cur.get('context_skip_counts')}",
        f"Slippage: status={cur.get('slippage_status')} matched={cur.get('slippage_matched_trades')} "
        f"avg={cur.get('slippage_avg_pct')}% total_usd={cur.get('slippage_total_usd')}",
    ]
    if report.get("week_over_week"):
        lines.append("Week-over-week:")
        for key, value in report["week_over_week"].items():
            lines.append(f"  {key}: {value:+}")
    for note in report.get("notes") or []:
        lines.append(f"Note: {note}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Weekly execution audit vs slippage alignment")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    report = build_execution_alignment_report(output_dir=Path(args.output_dir))
    print(format_execution_alignment_report(report))


if __name__ == "__main__":
    main()
