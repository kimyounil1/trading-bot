"""Pure helpers for the Streamlit CMS (unit-testable, no streamlit import)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from src.cms_reconcile import reconcile_cms_execute_with_alpaca

if TYPE_CHECKING:
    from src.market_clock import MarketClock

__all__ = [
    "money",
    "pct",
    "order_is_filled",
    "is_executable_buy_row",
    "order_display_columns",
    "orders_to_frame",
    "count_filled_today",
    "partition_alpaca_orders",
    "fetch_broker_order_book",
    "cache_age_minutes",
    "classify_buy_candidates",
    "reconcile_cms_execute_with_alpaca",
    "sort_buy_candidates",
]

from src.buy_skip_reason_ko import (
    explain_buy_skip_reason,
    explain_execution_label,
)
from src.cms_sleeve_panel import (
    build_sleeve_control_panel_rows,
    build_sleeves_config_dict,
    merge_sleeve_settings_into_strategy,
    save_sleeve_settings,
    validate_sleeve_target_weights,
)

__all__ += [
    "format_buy_candidates_for_display",
    "format_audit_skips_for_display",
    "validate_sleeve_target_weights",
    "build_sleeve_control_panel_rows",
    "build_sleeves_config_dict",
    "merge_sleeve_settings_into_strategy",
    "save_sleeve_settings",
]


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


def fetch_broker_order_book(broker: object, *, closed_limit: int = 50) -> tuple[list[dict], list[dict]]:
    """Open + recently closed orders via adapter, with alpaca_client fallback."""
    get_open = getattr(broker, "get_open_orders", None)
    get_closed = getattr(broker, "get_recent_closed_orders", None)
    if callable(get_open) and callable(get_closed):
        return get_open(), get_closed(limit=int(closed_limit))

    from src.alpaca_client import get_open_orders, get_recent_closed_orders

    return get_open_orders(), get_recent_closed_orders(limit=int(closed_limit))


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


def sort_buy_candidates(buy_df: pd.DataFrame) -> pd.DataFrame:
    if buy_df.empty:
        return buy_df
    if "rank_ai_percentile" in buy_df.columns and buy_df["rank_ai_percentile"].notna().any():
        sort_cols = ["rank_ai_percentile"]
        if "ai_score" in buy_df.columns:
            sort_cols.append("ai_score")
        return buy_df.sort_values(sort_cols, ascending=False, na_position="last")
    sort_cols = [
        col
        for col in ["would_submit_if_execute", "risk_allowed", "ai_score"]
        if col in buy_df.columns
    ]
    if not sort_cols:
        return buy_df
    return buy_df.sort_values(sort_cols, ascending=[False] * len(sort_cols))


def format_buy_candidates_for_display(buy_df: pd.DataFrame) -> pd.DataFrame:
    """Add Korean skip explanations for CMS tables."""
    if buy_df.empty:
        return buy_df

    out = buy_df.copy()
    reasons = out.get("reason", pd.Series("", index=out.index)).astype(str)
    explanations = [
        explain_buy_skip_reason(
            reason,
            row=out.iloc[i].to_dict() if i < len(out) else None,
        )
        for i, reason in enumerate(reasons)
    ]
    out["스킵분류"] = [e.category for e in explanations]
    out["한글요약"] = [e.summary for e in explanations]
    out["상세설명"] = [e.detail for e in explanations]
    if "reason" in out.columns:
        out["원본사유(영문)"] = out["reason"]
    if "execution_label" in out.columns:
        out["실행라벨"] = out["execution_label"].map(explain_execution_label)

    rename = {
        "ticker": "종목",
        "signal": "시그널",
        "ai_score": "AI점수",
        "rank_ai_score": "Rank점수",
        "rank_ai_percentile": "Rank백분위",
        "order_amount": "주문금액",
        "target_amount": "목표금액",
        "would_submit_if_execute": "execute시제출",
        "risk_allowed": "리스크허용",
        "close": "종가",
        "rsi": "RSI",
        "llm_verdict": "LLM판정",
        "error": "오류",
    }
    out = out.rename(columns={k: v for k, v in rename.items() if k in out.columns})

    preferred = [
        "종목",
        "시그널",
        "스킵분류",
        "한글요약",
        "상세설명",
        "실행라벨",
        "execute시제출",
        "AI점수",
        "Rank점수",
        "Rank백분위",
        "주문금액",
        "원본사유(영문)",
        "오류",
    ]
    cols = [c for c in preferred if c in out.columns]
    rest = [c for c in out.columns if c not in cols]
    return out[cols + rest]


def format_audit_skips_for_display(audit_df: pd.DataFrame) -> pd.DataFrame:
    """Add Korean explanations for execution audit skip rows."""
    if audit_df.empty:
        return audit_df

    out = audit_df.copy()
    reasons = out.get("reason", pd.Series("", index=out.index)).astype(str)
    explanations = [
        explain_buy_skip_reason(reason, row=out.iloc[i].to_dict())
        for i, reason in enumerate(reasons)
    ]
    out["스킵분류"] = [e.category for e in explanations]
    out["한글요약"] = [e.summary for e in explanations]
    out["상세설명"] = [e.detail for e in explanations]
    out["조치힌트"] = [e.action_hint for e in explanations]

    rename = {
        "timestamp": "시각",
        "ticker": "종목",
        "event_type": "이벤트",
        "reason": "원본사유(영문)",
        "rank_ai_score": "Rank점수",
        "rank_ai_percentile": "Rank백분위",
        "llm_verdict": "LLM판정",
        "signal": "시그널",
        "ai_score": "AI점수",
    }
    out = out.rename(columns={k: v for k, v in rename.items() if k in out.columns})

    preferred = [
        "시각",
        "종목",
        "이벤트",
        "스킵분류",
        "한글요약",
        "상세설명",
        "조치힌트",
        "Rank점수",
        "Rank백분위",
        "AI점수",
        "원본사유(영문)",
    ]
    cols = [c for c in preferred if c in out.columns]
    rest = [c for c in out.columns if c not in cols]
    return out[cols + rest]
