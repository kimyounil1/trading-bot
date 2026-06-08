"""Post-pipeline run finalization: peaks save, metrics, telegram summary."""

from __future__ import annotations

from src.notifier import notify_run_summary
from src.trading.bot_helpers import save_peaks, summarize_run_metrics
from src.trading.run_context import TradingRunContext


def compact_buy_summary(rows: list[str], limit: int = 10) -> str:
    if not rows:
        return "No buy checks."

    priority_rows = []
    blocked_count = 0
    skipped_count = 0
    not_allowed_count = 0
    error_rows = []

    for row in rows:
        lower = row.lower()

        if "error" in lower:
            error_rows.append(row)
        elif "allowed=true" in lower:
            priority_rows.append(row)
        elif "skip_order" in lower or "max orders" in lower:
            skipped_count += 1
        elif "allowed=false" in lower:
            not_allowed_count += 1
        else:
            blocked_count += 1

    selected = []

    if error_rows:
        selected.extend(error_rows[:limit])

    remaining = max(0, limit - len(selected))
    selected.extend(priority_rows[:remaining])

    summary_lines = selected[:limit]

    hidden_allowed = max(0, len(priority_rows) - max(0, limit - len(error_rows)))
    hidden_total = hidden_allowed + blocked_count + skipped_count + not_allowed_count

    summary_lines.append("")
    summary_lines.append(
        f"Summary: allowed_candidates={len(priority_rows)}, "
        f"errors={len(error_rows)}, "
        f"not_allowed={not_allowed_count}, "
        f"skipped_or_blocked={skipped_count + blocked_count}, "
        f"hidden={hidden_total}"
    )

    return "\n".join(summary_lines)


def compact_exit_summary(rows: list[str], limit: int = 20) -> str:
    if not rows:
        return "No open positions."

    if len(rows) <= limit:
        return "\n".join(rows)

    shown = rows[:limit]
    shown.append(f"... hidden_exit_rows={len(rows) - limit}")
    return "\n".join(shown)


def finalize_trading_run(ctx: TradingRunContext) -> None:
    save_peaks(ctx.peaks)

    metrics_summary = summarize_run_metrics(
        live_order_count=ctx.live_order_count,
        skipped_reasons=ctx.skipped_reasons,
        data_error_count=ctx.data_error_count,
        api_error_count=ctx.api_error_count,
    )
    exit_summary = (
        f"{metrics_summary}\n"
        f"{compact_exit_summary(ctx.exit_summary_rows, limit=20)}"
    )
    buy_summary = (
        f"{metrics_summary}\n"
        f"{compact_buy_summary(ctx.buy_summary_rows, limit=10)}"
    )

    try:
        notify_run_summary(
            market_is_open=ctx.market_clock.orders_allowed,
            execute_orders=ctx.execute_orders,
            cash=ctx.account["cash"],
            portfolio_value=ctx.account["portfolio_value"],
            positions_count=ctx.account["positions_count"],
            exit_summary=exit_summary,
            buy_summary=buy_summary,
        )
    except Exception as exc:
        print(f"TELEGRAM_SUMMARY_ERROR - {exc}")
