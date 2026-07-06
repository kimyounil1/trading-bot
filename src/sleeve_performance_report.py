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
from src.sleeve_position_registry import load_sleeve_position_map

DEFAULT_OUTPUT_DIR = Path("logs/sleeves")
DEFAULT_HISTORY = DEFAULT_OUTPUT_DIR / "history.jsonl"
REALIZED_BY_TICKER_PATH = Path("logs/portfolio_pnl/realized_by_ticker.csv")
REALIZED_EVENTS_PATH = Path("logs/portfolio_pnl/realized_events.csv")


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


def _fetch_live_account() -> tuple[dict[str, Any] | None, list[dict[str, Any]] | None, str]:
    try:
        from src.alpaca_client import get_account_summary, get_positions_summary

        return get_account_summary(), get_positions_summary(), ""
    except Exception as exc:
        return None, None, f"broker unreachable; NAV/weights zeroed ({exc})"


def _build_ticker_sleeve_map(audit_df: pd.DataFrame) -> dict[str, str]:
    """Registry first; audit sleeve tags as fallback for already-closed tickers."""
    mapping: dict[str, str] = {}
    if not audit_df.empty and "sleeve_id" in audit_df.columns:
        tagged = audit_df[
            audit_df["sleeve_id"].notna()
            & (audit_df["sleeve_id"].astype(str) != "")
            & (audit_df.get("profile_name", pd.Series(dtype=str)).astype(str) != "TEST_PROFILE")
        ]
        if not tagged.empty:
            mapping.update(
                tagged.groupby("ticker")["sleeve_id"]
                .agg(lambda s: s.value_counts().index[0])
                .to_dict()
            )
    try:
        mapping.update(load_sleeve_position_map())
    except Exception:
        pass
    return {str(t).upper(): str(s) for t, s in mapping.items()}


def _sleeve_pnl_stats(
    sleeve_id: str,
    ticker_sleeve: dict[str, str],
    positions: list[dict[str, Any]],
) -> dict[str, Any]:
    def _is_sleeve(ticker: str) -> bool:
        return ticker_sleeve.get(str(ticker).upper()) == sleeve_id

    realized_pl = None
    closed_trades = None
    if REALIZED_BY_TICKER_PATH.is_file():
        try:
            realized = pd.read_csv(REALIZED_BY_TICKER_PATH)
            subset = realized[realized["ticker"].map(_is_sleeve)]
            realized_pl = round(float(subset["realized_pl"].sum()), 2)
            closed_trades = int(subset["closed_trades"].sum())
        except Exception:
            pass

    win_rate = None
    if REALIZED_EVENTS_PATH.is_file():
        try:
            events = pd.read_csv(REALIZED_EVENTS_PATH)
            subset = events[events["ticker"].map(_is_sleeve)]
            if len(subset):
                win_rate = round(float((subset["realized_pl"] > 0).mean()), 4)
        except Exception:
            pass

    open_positions = [p for p in positions if _is_sleeve(p.get("symbol", ""))]
    unrealized_pl = round(sum(float(p.get("unrealized_pl", 0.0)) for p in open_positions), 2)
    cost_basis = round(sum(float(p.get("cost_basis", 0.0)) for p in open_positions), 2)
    total_pl = None if realized_pl is None else round(realized_pl + unrealized_pl, 2)
    return {
        "realized_pl": realized_pl,
        "closed_trades": closed_trades,
        "unrealized_pl": unrealized_pl,
        "open_cost_basis": cost_basis,
        "open_roi_pct": round(unrealized_pl / cost_basis * 100.0, 2) if cost_basis > 0 else None,
        "total_pl": total_pl,
        "win_rate": win_rate,
        "open_positions": len(open_positions),
    }


def build_sleeve_performance_report(
    *,
    account: dict[str, Any] | None = None,
    positions: list[dict[str, Any]] | None = None,
    open_orders: list[dict[str, Any]] | None = None,
    audit_path: Path = Path(EXECUTION_AUDIT_LOG_PATH),
) -> dict[str, Any]:
    settings = load_settings()
    fetch_warning = ""
    if account is None and positions is None:
        account, positions, fetch_warning = _fetch_live_account()
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
    ticker_sleeve = _build_ticker_sleeve_map(audit_df)

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
        pnl = _sleeve_pnl_stats(sleeve_id, ticker_sleeve, positions)
        sleeves_out[sleeve_id] = {
            "target_weight": budget.target_weight,
            "current_weight": round(current_weight, 4),
            "drift": round(current_weight - budget.target_weight, 4),
            "nav": round(budget.current_notional + (budget.available_cash if sleeve_id == CASH_SLEEVE_ID else 0.0), 2),
            "realized_pl": pnl["realized_pl"],
            "closed_trades": pnl["closed_trades"],
            "unrealized_pl": pnl["unrealized_pl"],
            "total_pl": pnl["total_pl"],
            "open_cost_basis": pnl["open_cost_basis"],
            "open_roi_pct": pnl["open_roi_pct"],
            "open_positions": pnl["open_positions"],
            "turnover": stats["submitted_orders"],
            "win_rate": pnl["win_rate"],
            "open_orders": stats["open_orders"],
            "blocked_orders": stats["blocked_orders"],
            "order_budget": budget.order_budget,
            "rebalance_needed": budget.rebalance_needed,
            "risk_mode": budget.risk_mode,
        }

    warnings = list(snapshot.warnings)
    if fetch_warning:
        warnings.append(fetch_warning)
    return {
        "generated_at": _utc_now_iso(),
        "portfolio_sleeves_enabled": sleeves_enabled(settings),
        "portfolio_value": round(float(snapshot.portfolio_value), 2),
        "account_cash": round(float(snapshot.account_cash), 2),
        "implicit_cash_weight": round(float(snapshot.implicit_cash_weight), 4),
        "warnings": warnings,
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
