"""Execute sleeve drift rebalance trims after strategy exits."""

from __future__ import annotations

from src.logger import log_order, log_order_status
from src.notifier import notify_error, notify_order
from src.sleeve_rebalance import build_sleeve_rebalance_actions
from src.trading.bot_helpers import (
    audit_log,
    execution_block_label,
    order_is_filled,
)
from src.trading.run_context import TradingRunContext


def run_sleeve_rebalance_pipeline(ctx: TradingRunContext) -> None:
    if not ctx.sleeve_ctx.enabled:
        return

    ctx.sleeve_ctx.refresh_snapshot()
    actions = build_sleeve_rebalance_actions(
        snapshot=ctx.sleeve_ctx.snapshot,
        positions=ctx.positions,
        sleeve_position_map=ctx.sleeve_ctx.sleeve_position_map,
        dust_min_usd=ctx.dust_min_usd,
    )
    if not actions:
        return

    print(f"SLEEVE_REBALANCE: {len(actions)} trim action(s) planned")
    for action in actions:
        ticker = action.ticker
        if action.sell_qty <= 0:
            continue

        if not ctx.can_submit_orders:
            label = execution_block_label(ctx.execute_orders, ctx.market_clock)
            ctx.exit_summary_rows.append(
                f"{ticker}: SLEEVE_REBALANCE_{label} qty={action.sell_qty}"
            )
            audit_log(
                ctx.audit_ctx,
                event_type="SKIP_SELL",
                ticker=ticker,
                action="SELL",
                status="SKIPPED",
                reason=f"{label}: {action.reason}",
                profile_name=ctx.profile_name,
                regime=ctx.current_regime,
                **ctx.sleeve_ctx.audit_fields(sleeve_id=action.sleeve_id),
            )
            continue

        try:
            submission = ctx.broker_adapter.submit_sell_qty(
                ticker=ticker,
                qty=action.sell_qty,
                market_clock=ctx.market_clock,
                slippage_pct=ctx.extended_slippage,
                client_order_id=f"slev_{ctx.run_id}_{ticker}",
            )
            ctx.live_order_count += 1
            log_order(
                ticker=ticker,
                qty=action.sell_qty,
                order_id=submission.order_id,
                status=submission.status,
                side=submission.side,
                order_type=submission.order_type,
                reason=action.reason,
            )
            audit_log(
                ctx.audit_ctx,
                event_type="SELL_SUBMITTED",
                ticker=ticker,
                action="SELL",
                status=submission.status,
                reason=action.reason,
                profile_name=ctx.profile_name,
                regime=ctx.current_regime,
                order_id=submission.order_id,
                **ctx.sleeve_ctx.audit_fields(sleeve_id=action.sleeve_id),
            )
            checked = ctx.broker_adapter.wait_for_order_status(submission.order_id)
            log_order_status(
                ticker=ticker,
                order_id=checked["id"],
                status=checked["status"],
                side=checked["side"],
                order_type=checked["type"],
                filled_qty=checked["filled_qty"],
                filled_avg_price=checked["filled_avg_price"],
                reason=action.reason,
            )
            ctx.exit_summary_rows.append(
                f"{ticker}: SLEEVE_REBALANCE status={checked['status']} "
                f"qty={action.sell_qty} reason={action.reason}"
            )
            if order_is_filled(checked["status"]):
                notify_order(
                    action="SELL",
                    ticker=ticker,
                    status=checked["status"],
                    order_id=checked["id"],
                    reason=action.reason,
                    filled_qty=checked["filled_qty"],
                    filled_avg_price=checked["filled_avg_price"],
                )
                remaining_qty = float(ctx.positions_by_symbol.get(ticker, {}).get("qty") or 0.0)
                if remaining_qty <= action.sell_qty + 1e-6:
                    ctx.sleeve_ctx.record_exit(ticker)
        except Exception as exc:
            if isinstance(exc, ConnectionError) and ctx.execute_orders:
                notify_error(
                    f"CRITICAL: Network error during sleeve rebalance for {ticker}",
                    exc,
                )
                raise
            ctx.api_error_count += 1
            ctx.exit_summary_rows.append(f"{ticker}: SLEEVE_REBALANCE_ERROR - {exc}")
            audit_log(
                ctx.audit_ctx,
                event_type="SELL_ERROR",
                ticker=ticker,
                action="SELL",
                status="ERROR",
                reason=str(exc),
                profile_name=ctx.profile_name,
                regime=ctx.current_regime,
                **ctx.sleeve_ctx.audit_fields(sleeve_id=action.sleeve_id),
            )
