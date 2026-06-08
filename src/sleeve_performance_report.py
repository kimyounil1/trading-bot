"""Sleeve-level NAV / return / turnover summary."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import EXECUTION_AUDIT_LOG_PATH
from src.daily_audit_summary import load_execution_audit
from src.portfolio_sleeves import (
    CORE_SLEEVE_ID,
    CASH_SLEEVE_ID,
    TOURNAMENT_SLEEVE_ID,
    PortfolioSleeveAllocator,
    sleeves_enabled,
)
from src.settings import load_settings

DEFAULT_OUTPUT_DIR = Path("logs/sleeves")
DEFAULT_HISTORY = DEFAULT_OUTPUT_DIR / "history.jsonl"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _audit_sleeve_stats(audit_df: pd.DataFrame, sleeve_id: str) -> dict[str, Any]:
    if audit_df.empty:
        return {"blocked_orders": 0, "submitted_orders": 0, "open_orders": 0}

    sleeve_col = audit_df.get("sleeve_id", pd.Series(dtype=str))
    if sleeve_col is not None and sleeve_col.notna().any():
        mask = sleeve_col.astype(str).str.lower().eq(str(sleeve_id).lower())
    else:
        mask = pd.Series([sleeve_id == CORE_SLEEVE_ID] * len(audit_df), index=audit_df.index)

    subset = audit_df[mask]
    event_types = subset.get("event_type", pd.Series(dtype=str)).astype(str)
    blocked = int(event_types.str.contains("SKIP", na=False).sum())
    submitted = int((event_types == "BUY_SUBMITTED").sum())
    return {
        "blocked_orders": blocked,
        "submitted_orders": submitted,
        "open_orders": 0,
    }


def build_sleeve_performance_report(
    *,
    account: dict[str, Any] | None = None,
    positions: list[dict[str, Any]] | None = None,
    open_orders: list[dict[str, Any]] | None = None,
    audit_path: Path = Path(EXECUTION_AUDIT_LOG_PATH),
) -> dict[str, Any]:
    settings = load_settings()
    account = account or {
        "portfolio_value": 0.0,
        "cash": 0.0,
        "buying_power": 0.0,
    }
    positions = positions or []
    open_orders = open_orders or []

    allocator = PortfolioSleeveAllocator(
        settings,
        account=account,
        positions=positions,
        open_orders=open_orders,
    )
    snapshot = allocator.build_snapshot()
    audit_df = load_execution_audit(audit_path)

    sleeves_out: dict[str, Any] = {}
    for sleeve_id in (CORE_SLEEVE_ID, TOURNAMENT_SLEEVE_ID, CASH_SLEEVE_ID):
        budget = snapshot.sleeves.get(sleeve_id)
        if budget is None and not snapshot.enabled:
            continue
        if budget is None:
            continue
        current_weight = (
            budget.current_notional / snapshot.portfolio_value
            if snapshot.portfolio_value > 0
            else 0.0
        )
        stats = _audit_sleeve_stats(audit_df, sleeve_id)
        sleeves_out[sleeve_id] = {
            "target_weight": budget.target_weight,
            "current_weight": round(current_weight, 4),
            "drift": round(current_weight - budget.target_weight, 4),
            "nav": round(budget.current_notional + (budget.available_cash if sleeve_id == CASH_SLEEVE_ID else 0.0), 2),
            "return_pct": None,
            "benchmark_return_pct": None,
            "excess_return_pct": None,
            "max_drawdown_pct": None,
            "turnover": stats["submitted_orders"],
            "win_rate": None,
            "open_orders": stats["open_orders"],
            "blocked_orders": stats["blocked_orders"],
            "order_budget": budget.order_budget,
            "rebalance_needed": budget.rebalance_needed,
            "risk_mode": budget.risk_mode,
        }

    return {
        "generated_at": _utc_now_iso(),
        "portfolio_sleeves_enabled": sleeves_enabled(settings),
        "portfolio_value": round(float(snapshot.portfolio_value), 2),
        "account_cash": round(float(snapshot.account_cash), 2),
        "implicit_cash_weight": round(float(snapshot.implicit_cash_weight), 4),
        "warnings": list(snapshot.warnings),
        "sleeves": sleeves_out,
        "sources": {"execution_audit": str(audit_path)},
    }


def write_sleeve_performance_report(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    **kwargs: Any,
) -> Path:
    report = build_sleeve_performance_report(**kwargs)
    output_dir.mkdir(parents=True, exist_ok=True)
    latest = output_dir / "latest_summary.json"
    latest.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    with (output_dir / "history.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(report, ensure_ascii=False) + "\n")
    return latest


def main() -> None:
    parser = argparse.ArgumentParser(description="Build sleeve performance summary")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    path = write_sleeve_performance_report(output_dir=Path(args.output_dir))
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
