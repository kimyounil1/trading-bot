"""Rank AI buy gate: floor cutoff + top-K new-buy selection (live/backtest aligned)."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

SKIP_RANK_TOP_K_REASON = "rank buy allocator: below top-K for this run"


def rank_buy_top_k_enabled(settings: Any) -> bool:
    """Top-K selection applies when rank gate is on (unless explicitly disabled)."""
    if not bool(getattr(settings, "rank_ai_buy_gate_enabled", False)):
        return False
    return bool(getattr(settings, "rank_ai_buy_top_k_enabled", True))


def max_rank_new_buys_per_run(
    settings: Any,
    *,
    meaningful_positions_count: int,
    orders_submitted: int = 0,
) -> int:
    """Cap for new positions selected by rank percentile in one run/day."""
    max_orders = int(getattr(settings, "max_orders_per_run", 1))
    max_positions = int(getattr(settings, "max_total_positions", max_orders))
    slots_left = max(0, max_positions - int(meaningful_positions_count))
    orders_left = max(0, max_orders - int(orders_submitted))
    return max(0, min(slots_left, orders_left))


def _percentile_key(row: Mapping[str, Any]) -> tuple[float, str]:
    pct = row.get("rank_ai_percentile")
    try:
        value = float(pct)
    except (TypeError, ValueError):
        value = -1.0
    ticker = str(row.get("ticker", "")).upper()
    return (-value, ticker)


def _ai_score_key(row: Mapping[str, Any]) -> tuple[float, str]:
    score = row.get("ai_score")
    try:
        value = float(score)
    except (TypeError, ValueError):
        value = -1.0
    ticker = str(row.get("ticker", "")).upper()
    return (-value, ticker)


def sort_approved_buys_for_execution(
    approved_buys: list[dict],
    *,
    settings: Any,
) -> list[dict]:
    """Order buys for sleeve trim/submit: highest rank percentile (or ai_score) first."""
    if not approved_buys:
        return approved_buys
    if bool(getattr(settings, "rank_ai_buy_gate_enabled", False)):
        return sorted(approved_buys, key=_percentile_key)
    return sorted(approved_buys, key=_ai_score_key)


def select_rank_top_k_new_buy_tickers(
    candidates: Sequence[Mapping[str, Any]],
    *,
    max_select: int,
) -> set[str]:
    """Return tickers allowed among new-buy candidates (sorted by rank percentile)."""
    if max_select <= 0:
        return set()

    new_buys = [
        row
        for row in candidates
        if bool(row.get("is_new_position", True))
        and row.get("rank_ai_percentile") is not None
        and row.get("risk_allowed", True)
    ]
    ordered = sorted(new_buys, key=_percentile_key)
    return {str(row["ticker"]).upper() for row in ordered[:max_select]}


def apply_rank_top_k_new_buy_selection(
    approved_buys: list[dict],
    *,
    settings: Any,
    meaningful_positions_count: int,
    orders_submitted: int = 0,
) -> tuple[list[dict], list[dict]]:
    """
    Keep add-on buys; for new positions keep only top-K by rank_ai_percentile.

    Returns (kept, skipped) where skipped rows are copies with allocator reason.
    """
    if not rank_buy_top_k_enabled(settings):
        return approved_buys, []

    max_select = max_rank_new_buys_per_run(
        settings,
        meaningful_positions_count=meaningful_positions_count,
        orders_submitted=orders_submitted,
    )
    eligible = [
        row
        for row in approved_buys
        if bool(row.get("is_new_position", True))
        and row.get("rank_ai_percentile") is not None
    ]
    selected = select_rank_top_k_new_buy_tickers(eligible, max_select=max_select)

    kept: list[dict] = []
    skipped: list[dict] = []
    for row in approved_buys:
        is_new = bool(row.get("is_new_position", True))
        ticker = str(row["ticker"]).upper()
        if not is_new:
            kept.append(row)
            continue
        if row.get("rank_ai_percentile") is None:
            kept.append(row)
            continue
        if ticker not in selected:
            skipped_row = dict(row)
            skipped_row["risk_reason"] = (
                f"{row.get('risk_reason', '')} | {SKIP_RANK_TOP_K_REASON} "
                f"(top {max_select}, pct={row.get('rank_ai_percentile')})"
            ).strip(" |")
            skipped.append(skipped_row)
            continue
        kept.append(row)
    return kept, skipped


def finalize_rank_buy_cache_execution_labels(
    buy_rows: list[dict],
    *,
    settings: Any,
    meaningful_positions_count: int,
    orders_allowed: bool,
) -> None:
    """Mutate candidate-cache buy rows: rank order + max_orders execution labels."""
    from src.buy_guards import execution_label_for_cache

    max_select = max_rank_new_buys_per_run(
        settings,
        meaningful_positions_count=meaningful_positions_count,
    )
    if rank_buy_top_k_enabled(settings):
        selected = select_rank_top_k_new_buy_tickers(buy_rows, max_select=max_select)
    else:
        selected = {
            str(row["ticker"]).upper()
            for row in buy_rows
            if row.get("risk_allowed") and row.get("is_new_position")
        }

    dry_run_orders_count = 0
    for row in buy_rows:
        if not row.get("risk_allowed"):
            row.setdefault("execution_label", "NOT_ALLOWED")
            row.setdefault("would_submit_if_execute", False)
            continue

        is_new = bool(row.get("is_new_position", True))
        ticker = str(row.get("ticker", "")).upper()
        if rank_buy_top_k_enabled(settings) and is_new and ticker not in selected:
            row["execution_label"] = "SKIP_RANK_TOP_K"
            row["would_submit_if_execute"] = False
            base_reason = str(row.get("reason", ""))
            row["reason"] = (
                f"{base_reason} | {SKIP_RANK_TOP_K_REASON} (top {max_select})"
            ).strip(" |")
            continue

        label, would_submit = execution_label_for_cache(
            risk_allowed=True,
            reason=str(row.get("reason", "")),
            dry_run_orders_count=dry_run_orders_count,
            max_orders_per_run=int(settings.max_orders_per_run),
            orders_allowed=orders_allowed,
        )
        row["execution_label"] = label
        row["would_submit_if_execute"] = would_submit
        if would_submit:
            dry_run_orders_count += 1


def truncate_ticker_frames_asof(
    ticker_data: dict[str, Any],
    asof,
    *,
    min_rows: int = 272,
) -> dict[str, Any]:
    """Point-in-time OHLC frames for rank gate inference."""
    import pandas as pd

    asof_ts = pd.Timestamp(asof)
    out: dict[str, Any] = {}
    for ticker, frame in ticker_data.items():
        if frame is None or getattr(frame, "empty", True):
            continue
        d = frame.copy()
        d["date"] = pd.to_datetime(d["date"])
        d = d[d["date"] <= asof_ts]
        if len(d) >= min_rows:
            out[str(ticker).upper()] = d
    return out


def attach_rank_gate_scores_to_day_df(
    day_df,
    *,
    scores: dict[str, Any],
    cutoff: float,
):
    """Add rank columns, apply floor cutoff, sort by percentile (desc)."""
    import pandas as pd

    if day_df.empty:
        return day_df

    out = day_df.copy()
    percentiles = []
    raw_scores = []
    for ticker in out["ticker"]:
        symbol = str(ticker).upper()
        score = scores.get(symbol)
        if score is None:
            percentiles.append(float("nan"))
            raw_scores.append(float("nan"))
        else:
            percentiles.append(float(score.percentile))
            raw_scores.append(float(score.score))
    out["rank_ai_percentile"] = percentiles
    out["rank_ai_score"] = raw_scores
    out = out[out["rank_ai_percentile"] >= cutoff].copy()
    return out.sort_values(
        ["rank_ai_percentile", "ticker"],
        ascending=[False, True],
    )
