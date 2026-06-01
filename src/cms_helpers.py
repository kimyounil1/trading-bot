"""Pure helpers for the Streamlit CMS (unit-testable, no streamlit import)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from src.market_clock import MarketClock


def money(value: float) -> str:
    return f"${value:,.2f}"


def pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def order_is_filled(status: str) -> bool:
    normalized = str(status).upper()
    return "FILLED" in normalized and "PARTIALLY" not in normalized


def is_executable_buy_row(row: pd.Series, clock: "MarketClock") -> bool:
    if float(row.get("order_amount") or 0) <= 0:
        return False
    if not clock.orders_allowed:
        return False
    label = str(row.get("execution_label", ""))
    if label == "WOULD_SUBMIT_IF_EXECUTED":
        return True
    return bool(row.get("would_submit_if_execute", False))


def order_display_columns() -> dict[str, list[str]]:
    return {
        "open": [
            "symbol",
            "side",
            "type",
            "qty",
            "filled_qty",
            "fill_pct",
            "limit_price",
            "status_simple",
            "extended_hours",
            "submitted_at",
            "id",
        ],
        "filled": [
            "symbol",
            "side",
            "type",
            "qty",
            "filled_qty",
            "filled_avg_price",
            "filled_at",
            "submitted_at",
            "extended_hours",
            "id",
        ],
        "closed_other": [
            "symbol",
            "side",
            "type",
            "qty",
            "filled_qty",
            "status_simple",
            "submitted_at",
            "filled_at",
            "id",
        ],
    }


def orders_to_frame(orders: list[dict], columns: list[str]) -> pd.DataFrame:
    if not orders:
        return pd.DataFrame(columns=columns)
    frame = pd.DataFrame(orders)
    for column in columns:
        if column not in frame.columns:
            frame[column] = ""
    return frame[columns]


def count_filled_today(orders: list[dict], *, now: pd.Timestamp | None = None) -> int:
    today_utc = (now or pd.Timestamp.now(tz="UTC")).date()
    count = 0
    for order in orders:
        if not order_is_filled(order.get("status", "")):
            continue
        filled_at = order.get("filled_at")
        if not filled_at:
            continue
        filled_date = pd.to_datetime(filled_at, utc=True, errors="coerce")
        if pd.isna(filled_date):
            continue
        if filled_date.date() == today_utc:
            count += 1
    return count


def partition_alpaca_orders(
    open_orders: list[dict],
    closed_orders: list[dict],
) -> tuple[list[dict], list[dict], list[dict]]:
    filled_orders = [
        order for order in closed_orders if order_is_filled(order.get("status", ""))
    ]
    closed_other = [
        order for order in closed_orders if not order_is_filled(order.get("status", ""))
    ]
    partial_open = [
        order
        for order in open_orders
        if str(order.get("status_simple", "")).upper() == "PARTIALLY_FILLED"
    ]
    return filled_orders, closed_other, partial_open


def cache_age_minutes(generated_at: str | None, *, now: pd.Timestamp | None = None) -> float:
    if not generated_at:
        return float("inf")
    generated_dt = pd.to_datetime(generated_at, utc=True)
    if generated_dt.tzinfo is None:
        generated_dt = generated_dt.tz_localize("UTC")
    else:
        generated_dt = generated_dt.tz_convert("UTC")
    current = now or pd.Timestamp.now(tz="UTC")
    return (current - generated_dt).total_seconds() / 60


def classify_buy_candidates(
    buy_df: pd.DataFrame,
    clock: "MarketClock",
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if buy_df.empty:
        empty = buy_df.copy()
        return empty, empty, empty

    error_mask = (
        buy_df["error"].notna() & (buy_df["error"].astype(str).str.len() > 0)
        if "error" in buy_df.columns
        else pd.Series(False, index=buy_df.index)
    )
    if "execution_label" in buy_df.columns:
        executable_mask = buy_df.apply(
            lambda row: is_executable_buy_row(row, clock),
            axis=1,
        )
    else:
        executable_mask = pd.Series(False, index=buy_df.index)

    executable_df = buy_df[executable_mask & ~error_mask].copy()
    error_df = buy_df[error_mask].copy()
    blocked_df = buy_df[~executable_mask & ~error_mask].copy()
    return executable_df, blocked_df, error_df


def reconcile_cms_execute_with_alpaca(
    execute_rows: list[dict] | pd.DataFrame,
    open_orders: list[dict],
    closed_orders: list[dict] | None = None,
) -> list[dict[str, str]]:
    """Detect CMS submit vs Alpaca OPEN mismatches after paper execute."""
    if isinstance(execute_rows, pd.DataFrame):
        rows = execute_rows.to_dict(orient="records")
    else:
        rows = list(execute_rows)

    closed_orders = closed_orders or []
    closed_by_id = {str(order.get("id", "")): order for order in closed_orders}
    open_by_id = {str(order.get("id", "")): order for order in open_orders}

    alerts: list[dict[str, str]] = []

    for row in rows:
        order_id = str(row.get("order_id") or "").strip()
        if not order_id or str(row.get("status", "")).upper() in {"ERROR", "SKIPPED"}:
            continue
        if order_id in open_by_id:
            continue
        closed = closed_by_id.get(order_id)
        if closed is not None:
            continue
        alerts.append(
            {
                "kind": "cms_missing_on_alpaca",
                "severity": "warning",
                "message": (
                    f"CMS submitted {row.get('action')} {row.get('ticker')} "
                    f"(order_id={order_id}) but order is not OPEN or in recent closed list."
                ),
            }
        )

    cms_ids = {
        str(row.get("order_id"))
        for row in rows
        if row.get("order_id") and str(row.get("status", "")).upper() not in {"ERROR", "SKIPPED"}
    }
    for order in open_orders:
        client_id = str(order.get("client_order_id") or "")
        order_id = str(order.get("id") or "")
        if not client_id.startswith("cms_"):
            continue
        if order_id in cms_ids:
            continue
        alerts.append(
            {
                "kind": "alpaca_open_without_cms_log",
                "severity": "warning",
                "message": (
                    f"Alpaca OPEN {order.get('symbol')} {order.get('side')} "
                    f"(id={order_id}, client_order_id={client_id}) not in latest CMS execute batch."
                ),
            }
        )

    return alerts


def sort_buy_candidates(buy_df: pd.DataFrame) -> pd.DataFrame:
    if buy_df.empty:
        return buy_df
    sort_cols = [
        col
        for col in ["would_submit_if_execute", "risk_allowed", "ai_score"]
        if col in buy_df.columns
    ]
    if not sort_cols:
        return buy_df
    return buy_df.sort_values(sort_cols, ascending=[False] * len(sort_cols))
