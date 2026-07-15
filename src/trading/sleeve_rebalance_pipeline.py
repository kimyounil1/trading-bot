"""Execute sleeve drift trims and allocation rebalance (retag + sells)."""

from __future__ import annotations

from dataclasses import replace
from math import floor

from src.logger import log_order, log_order_status
from src.notifier import notify_error, notify_info, notify_order
from src.sleeve_rebalance import (
    SleeveAllocationRebalancePlan,
    SleeveRebalanceAction,
    SleeveRetagAction,
    build_sleeve_allocation_rebalance_plan,
    build_sleeve_rebalance_actions,
)
from src.sleeve_rebalance_state import (
    clear_allocation_rebalance_pending,
    should_run_allocation_rebalance,
)
from src.trading.bot_helpers import (
    audit_log,
    execution_block_label,
    execution_reference_price,
    order_is_filled,
)
from src.trading.run_context import TradingRunContext


def _find_open_sell_order(ctx: TradingRunContext, ticker: str) -> dict | None:
    symbol = str(ticker).upper()
    for order in getattr(ctx.sleeve_ctx, "open_orders", []) or []:
        order_symbol = str(order.get("symbol") or "").upper()
        order_side = str(order.get("side") or "").upper()
        if order_symbol == symbol and order_side.endswith("SELL"):
            return order
    return None


def _remember_open_sell_order(
    ctx: TradingRunContext,
    *,
    ticker: str,
    order_id: str,
    status: str,
) -> None:
    if _find_open_sell_order(ctx, ticker) is not None:
        return
    open_orders = getattr(ctx.sleeve_ctx, "open_orders", None)
    if open_orders is None:
        return
    open_orders.append(
        {
            "id": str(order_id),
            "symbol": str(ticker).upper(),
            "side": "SELL",
            "status": str(status),
        }
    )


def _coalesce_sell_actions(
    actions: list[SleeveRebalanceAction],
) -> list[SleeveRebalanceAction]:
    """Collapse overlapping plans without adding their quantities twice."""
    merged: dict[str, SleeveRebalanceAction] = {}
    for action in actions:
        ticker = str(action.ticker).upper()
        existing = merged.get(ticker)
        if existing is None:
            merged[ticker] = replace(action, ticker=ticker)
            continue
        reasons = list(dict.fromkeys([existing.reason, action.reason]))
        merged[ticker] = replace(
            existing,
            sell_qty=max(existing.sell_qty, action.sell_qty),
            reason="; ".join(reasons),
        )
    return list(merged.values())


def _apply_retag_actions(ctx: TradingRunContext, actions: list[SleeveRetagAction]) -> None:
    for action in actions:
        ctx.sleeve_ctx.record_retag(action.ticker, to_sleeve_id=action.to_sleeve_id)
        ctx.exit_summary_rows.append(
            f"{action.ticker}: SLEEVE_RETAG {action.from_sleeve_id}→{action.to_sleeve_id} "
            f"notional=${action.notional:.2f} reason={action.reason}"
        )
        audit_log(
            ctx.audit_ctx,
            event_type="SLEEVE_RETAG",
            ticker=action.ticker,
            action="RETAG",
            status="APPLIED",
            reason=action.reason,
            profile_name=ctx.profile_name,
            regime=ctx.current_regime,
            **ctx.sleeve_ctx.audit_fields(sleeve_id=action.to_sleeve_id),
        )


def _execute_sell_actions(
    ctx: TradingRunContext,
    actions: list[SleeveRebalanceAction],
    *,
    event_prefix: str,
) -> None:
    actions = _coalesce_sell_actions(actions)
    if not actions:
        return

    print(f"{event_prefix}: {len(actions)} trim action(s) planned")
    for action_index, action in enumerate(actions, start=1):
        ticker = action.ticker
        if action.sell_qty <= 0:
            continue

        pending_order = _find_open_sell_order(ctx, ticker)
        if pending_order is not None:
            pending_status = str(pending_order.get("status") or "OPEN")
            ctx.exit_summary_rows.append(
                f"{ticker}: {event_prefix}_SKIP existing sell order "
                f"status={pending_status}"
            )
            continue

        if not ctx.can_submit_orders:
            label = execution_block_label(ctx.execute_orders, ctx.market_clock)
            ctx.exit_summary_rows.append(
                f"{ticker}: {event_prefix}_{label} qty={action.sell_qty}"
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

        position = ctx.positions_by_symbol.get(ticker) or {}
        try:
            current_price = float(position.get("current_price") or 0.0)
            current_qty = float(position.get("qty") or 0.0)
        except (TypeError, ValueError):
            current_price = 0.0
            current_qty = 0.0
        if current_qty <= 0:
            ctx.exit_summary_rows.append(
                f"{ticker}: {event_prefix}_SKIP no position quantity"
            )
            continue
        if current_price <= 0:
            ctx.exit_summary_rows.append(
                f"{ticker}: {event_prefix}_SKIP no current price for limit order"
            )
            audit_log(
                ctx.audit_ctx,
                event_type="SKIP_SELL",
                ticker=ticker,
                action="SELL",
                status="SKIPPED",
                reason="no current price available for sleeve trim limit order",
                profile_name=ctx.profile_name,
                regime=ctx.current_regime,
                **ctx.sleeve_ctx.audit_fields(sleeve_id=action.sleeve_id),
            )
            continue

        try:
            sell_qty = min(float(action.sell_qty), current_qty)
            close_tolerance = max(1e-9, current_qty * 1e-9)
            close_all = sell_qty >= current_qty - close_tolerance
            if close_all:
                sell_qty = current_qty
            else:
                asset = ctx.broker_adapter.get_asset_info(ticker)
                if not bool(asset.get("fractionable", True)):
                    sell_qty = float(floor(sell_qty))
                    if sell_qty <= 0:
                        ctx.exit_summary_rows.append(
                            f"{ticker}: {event_prefix}_SKIP non-fractionable qty "
                            f"below one share"
                        )
                        continue

            submission = ctx.broker_adapter.submit_sell_qty(
                ticker=ticker,
                qty=sell_qty,
                limit_price=execution_reference_price(None, fallback=current_price),
                market_clock=ctx.market_clock,
                slippage_pct=ctx.extended_slippage,
                client_order_id=f"slev_{ctx.run_id}_{ticker}_{action_index}",
                close_all=close_all,
            )
            ctx.live_order_count += 1
            log_order(
                ticker=ticker,
                notional=round(sell_qty * current_price, 2),
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
                f"{ticker}: {event_prefix} status={checked['status']} "
                f"qty={sell_qty} reason={action.reason}"
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
                try:
                    filled_qty = float(checked.get("filled_qty") or sell_qty)
                except (TypeError, ValueError):
                    filled_qty = sell_qty
                remaining_qty = max(0.0, current_qty - filled_qty)
                position["qty"] = remaining_qty
                position["market_value"] = remaining_qty * current_price
                if remaining_qty <= close_tolerance:
                    ctx.sleeve_ctx.record_exit(ticker)
            else:
                _remember_open_sell_order(
                    ctx,
                    ticker=ticker,
                    order_id=str(checked["id"]),
                    status=str(checked["status"]),
                )
        except Exception as exc:
            if isinstance(exc, ConnectionError) and ctx.execute_orders:
                notify_error(
                    f"CRITICAL: Network error during sleeve rebalance for {ticker}",
                    exc,
                )
                raise
            ctx.api_error_count += 1
            ctx.exit_summary_rows.append(f"{ticker}: {event_prefix}_ERROR - {exc}")
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


def _run_allocation_rebalance(ctx: TradingRunContext, *, trigger_reason: str) -> bool:
    plan = build_sleeve_allocation_rebalance_plan(
        snapshot=ctx.sleeve_ctx.snapshot,
        positions=ctx.positions,
        sleeve_position_map=ctx.sleeve_ctx.sleeve_position_map,
        dust_min_usd=ctx.dust_min_usd,
        trigger_reason=trigger_reason,
    )
    if not plan.retag_actions and not plan.sell_actions:
        return False

    print(
        "SLEEVE_ALLOCATION_REBALANCE: "
        f"retags={len(plan.retag_actions)} sells={len(plan.sell_actions)} "
        f"trigger={trigger_reason}"
    )
    _apply_retag_actions(ctx, list(plan.retag_actions))
    if plan.retag_actions:
        ctx.sleeve_ctx.allocator.sleeve_position_map = dict(ctx.sleeve_ctx.sleeve_position_map)
        ctx.sleeve_ctx.refresh_snapshot()

    _execute_sell_actions(
        ctx,
        list(plan.sell_actions),
        event_prefix="SLEEVE_ALLOCATION_REBALANCE",
    )
    notify_info(
        "Sleeve allocation rebalance",
        f"trigger={trigger_reason}\n"
        f"retags={len(plan.retag_actions)}\n"
        f"sells={len(plan.sell_actions)}",
    )
    clear_allocation_rebalance_pending()
    return True


def run_sleeve_rebalance_pipeline(ctx: TradingRunContext) -> None:
    if not ctx.sleeve_ctx.enabled:
        return

    ctx.sleeve_ctx.refresh_snapshot()
    force = bool(getattr(ctx, "force_sleeve_allocation_rebalance", False))
    run_allocation, trigger_reason = should_run_allocation_rebalance(ctx.sleeve_ctx.snapshot)
    if force:
        run_allocation = True
        trigger_reason = "immediate_run"
    if run_allocation:
        ran = _run_allocation_rebalance(ctx, trigger_reason=trigger_reason)
        if not ran and trigger_reason == "pending_request":
            print("SLEEVE_ALLOCATION_REBALANCE: pending request cleared (no actions needed)")
            clear_allocation_rebalance_pending()
        if ran:
            ctx.sleeve_ctx.refresh_snapshot()
            return

    actions = build_sleeve_rebalance_actions(
        snapshot=ctx.sleeve_ctx.snapshot,
        positions=ctx.positions,
        sleeve_position_map=ctx.sleeve_ctx.sleeve_position_map,
        dust_min_usd=ctx.dust_min_usd,
    )
    _execute_sell_actions(ctx, actions, event_prefix="SLEEVE_REBALANCE")
