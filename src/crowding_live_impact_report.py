"""Compare factor/crowding guard backtest impact with live execution_audit skips."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import EXECUTION_AUDIT_LOG_PATH
from src.crowding_live_metrics import (
    build_alignment_notes,
    count_crowding_skips_from_audit_rows,
    count_crowding_skips_from_reasons,
    summarize_crowding_skips_from_audit_df,
    validate_crowding_live_report,
)
from src.daily_audit_summary import SKIP_EVENT_TYPES, load_execution_audit
from src.settings import load_settings

DEFAULT_OUTPUT_DIR = Path("logs/crowding_live")
GUARD_IMPACT_PATH = Path("logs/guard_impact/latest_summary.json")
AUDIT_SUMMARY_PATH = Path("logs/audit_daily/latest_summary.json")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return payload if isinstance(payload, dict) else None


def build_crowding_live_impact_report(
    *,
    guard_impact: dict[str, Any] | None,
    audit_summary: dict[str, Any] | None,
    audit_df: pd.DataFrame | None,
    lookback_days: int = 7,
) -> dict[str, Any]:
    backtest_block: dict[str, Any] = {
        "available": guard_impact is not None,
        "delta_trade_count": None,
        "delta_total_return_pct": None,
        "crowding_guard_enabled_in_config": None,
    }
    if guard_impact:
        delta = guard_impact.get("delta") or {}
        backtest_block["delta_trade_count"] = delta.get("trade_count")
        backtest_block["delta_total_return_pct"] = delta.get("total_return_pct")
        backtest_block["crowding_guard_enabled_in_config"] = guard_impact.get(
            "crowding_guard_enabled_in_config"
        )
        backtest_block["baseline_trades"] = (guard_impact.get("baseline") or {}).get(
            "trade_count"
        )
        backtest_block["guarded_trades"] = (guard_impact.get("with_crowding_guard") or {}).get(
            "trade_count"
        )

    live_block: dict[str, Any] = {
        "lookback_days": lookback_days,
        "crowding_skip_count": 0,
        "skip_buy_count": 0,
        "crowding_skip_rate_of_skips": 0.0,
        "sample_reasons": [],
    }

    if audit_df is not None and not audit_df.empty:
        summary = summarize_crowding_skips_from_audit_df(audit_df)
        live_block.update(summary)
        if live_block["skip_buy_count"] == 0:
            event_types = audit_df["event_type"].astype(str)
            skip_mask = event_types.isin(SKIP_EVENT_TYPES)
            skip_reasons = audit_df.loc[skip_mask, "reason"].astype(str).tolist()
            crowding_count, samples = count_crowding_skips_from_audit_rows(skip_reasons)
            live_block["crowding_skip_count"] = crowding_count
            live_block["sample_reasons"] = samples
            live_block["skip_buy_count"] = int(skip_mask.sum())
            if live_block["skip_buy_count"] > 0:
                live_block["crowding_skip_rate_of_skips"] = round(
                    crowding_count / live_block["skip_buy_count"], 4
                )
    elif audit_summary:
        skip_counts = audit_summary.get("skip_reason_counts") or {}
        live_block["crowding_skip_count"] = count_crowding_skips_from_reasons(skip_counts)
        skip_by_event = audit_summary.get("skip_by_event") or {}
        live_block["skip_buy_count"] = int(skip_by_event.get("SKIP_BUY", 0))
        total_skips = sum(int(v) for v in skip_by_event.values()) or max(
            live_block["skip_buy_count"], 1
        )
        live_block["crowding_skip_rate_of_skips"] = round(
            live_block["crowding_skip_count"] / total_skips, 4
        )

    settings = load_settings()
    guard_enabled_now = bool(getattr(settings, "crowding_guard_enabled", False))
    backtest_block["crowding_guard_enabled_in_config"] = guard_enabled_now

    alignment = build_alignment_notes(
        backtest_delta_trades=backtest_block.get("delta_trade_count"),
        live_crowding_skips=int(live_block["crowding_skip_count"]),
        guard_enabled_in_config=guard_enabled_now,
    )

    return validate_crowding_live_report(
        {
            "generated_at": _utc_now_iso(),
            "guard_impact_available": guard_impact is not None,
            "audit_available": audit_summary is not None
            or (audit_df is not None and not audit_df.empty),
            "backtest": backtest_block,
            "live": live_block,
            "alignment": alignment,
        }
    )


def write_crowding_live_artifacts(
    report: dict[str, Any],
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    (output_dir / f"crowding_live_{stamp}.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    latest = output_dir / "latest_summary.json"
    latest.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return latest


def run_crowding_live_impact_report(
    *,
    lookback_days: int = 7,
    audit_path: str | Path = EXECUTION_AUDIT_LOG_PATH,
) -> dict[str, Any]:
    guard_impact = _load_json(GUARD_IMPACT_PATH)
    audit_summary = _load_json(AUDIT_SUMMARY_PATH)
    audit_df = load_execution_audit(audit_path, lookback_days=lookback_days)
    if audit_df.empty and audit_summary is None:
        audit_df = load_execution_audit(audit_path)

    report = build_crowding_live_impact_report(
        guard_impact=guard_impact,
        audit_summary=audit_summary,
        audit_df=audit_df,
        lookback_days=lookback_days,
    )
    write_crowding_live_artifacts(report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Crowding guard live vs backtest alignment")
    parser.add_argument("--lookback-days", type=int, default=7)
    parser.add_argument("--audit-path", default=str(EXECUTION_AUDIT_LOG_PATH))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    report = run_crowding_live_impact_report(
        lookback_days=args.lookback_days,
        audit_path=args.audit_path,
    )
    write_crowding_live_artifacts(report, Path(args.output_dir))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
