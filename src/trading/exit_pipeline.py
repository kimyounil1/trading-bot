"""Open-position exit, trim, dust cleanup pipeline."""

from __future__ import annotations

from datetime import datetime, timezone

from src.alpaca_client import get_position_entry_date
from src.logger import log_order, log_order_status
from src.notifier import notify_error, notify_info, notify_order
from src.position_dust import is_dust_position
from src.risk_manager import ExitDecision
from src.trading.bot_helpers import (
    audit_log,
    execution_block_label,
    execution_reference_price,
    get_signal_for_ticker,
    resolve_full_exit_reason,
)
from src.regime_stop_policy import resolve_exit_stop_params_from_settings
from src.trading.run_context import TradingRunContext


def run_exit_pipeline(ctx: TradingRunContext) -> None:
    # 1) 기존 보유 포지션 청산 조건 먼저 확인
    if ctx.positions:
        print("-" * 80)
        print("Checking open positions for exit conditions...")
    
        for position in ctx.positions:
            ticker = str(position["symbol"]).upper()
            try:
                if is_dust_position(position, min_usd=ctx.dust_min_usd):
                    dust_reason = (
                        f"dust position cleanup (<${ctx.dust_min_usd:g} market value)"
                    )
                    dust_mv = float(position["market_value"])
                    print(
                        f"{ticker}: DUST position qty={position['qty']}, "
                        f"market_value={dust_mv:.6f} — scheduling close"
                    )
                    ctx.exit_summary_rows.append(
                        f"{ticker}: DUST exit, market_value=${dust_mv:.6f}"
                    )
                    audit_log(
                        ctx.audit_ctx,
                        event_type="DUST_EXIT",
                        ticker=ticker,
                        action="CLOSE",
                        status="SUBMITTED" if ctx.can_submit_orders else "DRY_RUN",
                        reason=dust_reason,
                        profile_name=ctx.profile_name,
                        regime=ctx.current_regime,
                    )
                    if ctx.can_submit_orders:
                        try:
                            dust_qty = float(position["qty"])
                            dust_submission = ctx.broker_adapter.submit_sell_qty(
                                ticker,
                                dust_qty,
                                limit_price=float(position.get("current_price") or 0.0),
                                market_clock=ctx.market_clock,
                                slippage_pct=ctx.extended_slippage,
                                client_order_id=f"dust_{ctx.run_id}_{ticker}",
                            )
                            ctx.live_order_count += 1
                            log_order(
                                ticker=ticker,
                                notional=0.0,
                                order_id=dust_submission.order_id,
                                status=dust_submission.status,
                                side=dust_submission.side,
                                order_type=dust_submission.order_type,
                                reason=dust_reason,
                            )
                            print(
                                f"  PAPER_DUST_CLOSE: {ticker}, "
                                f"order_id={dust_submission.order_id}, "
                                f"status={dust_submission.status}"
                            )
                            notify_info(
                                "🧹 Dust position closed",
                                f"{ticker}: closed negligible position (${dust_mv:.4f})",
                            )
                        except Exception as e:
                            print(f"  Dust close error for {ticker}: {e}")
                            ctx.api_error_count += 1
                            if isinstance(e, ConnectionError) and ctx.execute_orders:
                                notify_error(
                                    f"CRITICAL: Network error during dust close for {ticker}",
                                    e,
                                )
                    else:
                        print(f"  DRY_RUN: would close dust position {ticker}")
                    ctx.positions_by_symbol.pop(ticker, None)
                    ctx.open_symbols.discard(ticker)
                    ctx.guard_open_symbols.discard(ticker)
                    ctx.meaningful_positions_count = max(
                        0, ctx.meaningful_positions_count - 1
                    )
                    continue
    
                data_fresh, data_reason = ctx.price_data_freshness.get(
                    ticker,
                    (False, "price data not loaded"),
                )
                if not data_fresh:
                    print(f"{ticker}: SKIP_EXIT - {data_reason}")
                    ctx.exit_summary_rows.append(f"{ticker}: SKIP_EXIT {data_reason}")
                    ctx.skipped_reasons[f"exit:{data_reason}"] += 1
                    ctx.data_error_count += 1
                    audit_log(
                        ctx.audit_ctx,
                        event_type="SKIP_EXIT",
                        ticker=ticker,
                        action="CLOSE",
                        status="SKIPPED",
                        reason=data_reason,
                        profile_name=ctx.profile_name,
                        regime=ctx.current_regime,
                    )
                    continue
    
                # 최고가 갱신 (트레일링 스탑용)
                current_price = float(position["current_price"])
                old_peak = ctx.peaks.get(ticker, 0.0)
                if current_price > old_peak:
                    ctx.peaks[ticker] = current_price
    
                signal, latest, ai_score = get_signal_for_ticker(
                    ticker,
                    ctx.ticker_data[ticker],
                    ctx.settings,
                    ai_model_bundle=ctx.ai_model_bundle,
                    market_regime_bullish=ctx.market_regime_bullish,
                    vix_df=ctx.vix_df,
                    spy_df=ctx.spy_df,
                    macro_df=ctx.macro_df,
                    market_clock=ctx.market_clock,
                )
                unrealized_plpc = float(position["unrealized_plpc"])
    
                ai_exit_triggered = False
                exit_thr = None
    
                # 보유 기간 계산 (Phase 18-C)
                holding_days = 0
                entry_date = get_position_entry_date(ticker)
                if entry_date:
                    holding_days = (datetime.now(entry_date.tzinfo) - entry_date).days
                    # print(f"  {ticker} held for {holding_days} days (entered {entry_date.date()})")
    
                # AI exit candidate
                if (
                    getattr(ctx.settings, "ai_exit_enabled", False)
                    and signal != "SELL"
                    and ai_score is not None
                ):
                    exit_thr = float(getattr(ctx.settings, "ai_exit_threshold", 0.35))
                    if getattr(ctx.settings, "ai_exit_dynamic_enabled", False) and ctx.vix_df is not None and not ctx.vix_df.empty:
                        close_col = "adj_close" if "adj_close" in ctx.vix_df.columns else "close"
                        latest_vix = float(ctx.vix_df[close_col].iloc[-1])
                        vix_low = float(getattr(ctx.settings, "ai_exit_vix_low", 15.0))
                        vix_high = float(getattr(ctx.settings, "ai_exit_vix_high", 25.0))
                        if latest_vix < vix_low:
                            exit_thr = float(getattr(ctx.settings, "ai_exit_threshold_bull", 0.55))
                        elif latest_vix > vix_high:
                            exit_thr = float(getattr(ctx.settings, "ai_exit_threshold_bear", 0.28))
                    if ai_score < exit_thr:
                        ai_exit_triggered = True
    
                # Stop / trailing (Phase 14-A; optional SPY-regime adaptive; ATR override below)
                peak_price = ctx.peaks.get(ticker, 0.0)
                stop_loss_pct, trailing_pct, regime_label = resolve_exit_stop_params_from_settings(
                    ctx.settings,
                    ctx.spy_df,
                    datetime.now(timezone.utc),
                )
    
                if getattr(ctx.settings, "adaptive_trailing_stop_enabled", False) and "atr" in latest:
                    atr_val = float(latest["atr"])
                    if atr_val > 0 and peak_price > 0:
                        multiplier = float(getattr(ctx.settings, "atr_multiplier", 3.0))
                        # ATR 기반의 변동성을 백분율로 변환 (ATR * Multiplier 만큼 하락 시 스탑)
                        trailing_pct = (atr_val * multiplier) / peak_price
                        # 합리적 범위 내에서 제한 (예: 최소 2% ~ 최대 20%)
                        trailing_pct = max(0.02, min(0.20, trailing_pct))
    
                trailing_drawdown = None
                if peak_price > 0 and current_price < peak_price:
                    trailing_drawdown = (peak_price - current_price) / peak_price
    
                full_exit_reason = resolve_full_exit_reason(
                    unrealized_plpc=unrealized_plpc,
                    stop_loss_pct=stop_loss_pct,
                    take_profit_pct=float(getattr(ctx.settings, "take_profit_pct", 0.0)),
                    trailing_drawdown=trailing_drawdown,
                    trailing_stop_pct=trailing_pct,
                    signal=signal,
                    ai_exit_triggered=ai_exit_triggered,
                    holding_days=holding_days,
                    max_holding_days=int(getattr(ctx.settings, "max_holding_days", 30)),
                )
                exit_decision = ExitDecision(
                    should_exit=full_exit_reason is not None,
                    reason="",
                )
                if full_exit_reason == "trailing stop triggered" and trailing_drawdown is not None:
                    exit_decision.reason = (
                        f"trailing stop triggered ({trailing_drawdown*100:.1f}% drop from peak ${peak_price:.2f})"
                    )
                elif full_exit_reason is not None:
                    exit_decision.reason = full_exit_reason
    
                regime_note = (
                    f", regime_stop={regime_label}({stop_loss_pct*100:.1f}%/{trailing_pct*100:.1f}%)"
                    if getattr(ctx.settings, "regime_adaptive_stop_enabled", False)
                    else ""
                )
                print(
                    f"{ticker}: position_qty={position['qty']}, "
                    f"unrealized_plpc={unrealized_plpc * 100:.2f}%, "
                    f"signal={signal}, "
                    f"exit={exit_decision.should_exit}, "
                    f"reason='{exit_decision.reason}'{regime_note}"
                )
    
                ctx.exit_summary_rows.append(
                    f"{ticker}: pnl={unrealized_plpc * 100:.2f}%, "
                    f"signal={signal}, exit={exit_decision.should_exit}, "
                    f"reason={exit_decision.reason}"
                )
    
                # Partial Profit Taking (Phase 11-A)
                # 수익률이 take_profit_partial_pct 이상이면 비중의 절반을 매도 (분할 익절)
                partial_tp_thr = float(getattr(ctx.settings, "take_profit_partial_pct", 0.0))
                if not exit_decision.should_exit and partial_tp_thr > 0 and unrealized_plpc >= partial_tp_thr:
                    current_qty = float(position["qty"])
                    if current_qty > 0.1: 
                        sell_qty = round(current_qty * float(getattr(ctx.settings, "partial_exit_ratio", 0.5)), 4)
                        print(f"  PARTIAL_EXIT_TRIGGERED: {ticker} pnl={unrealized_plpc*100:.2f}% >= {partial_tp_thr*100:.2f}%. Selling {sell_qty}")
                        if ctx.can_submit_orders:
                            try:
                                partial_submission = ctx.broker_adapter.submit_sell_qty(
                                    ticker,
                                    sell_qty,
                                    limit_price=execution_reference_price(
                                        None,
                                        fallback=current_price,
                                    ),
                                    market_clock=ctx.market_clock,
                                    slippage_pct=ctx.extended_slippage,
                                    client_order_id=f"part_{ctx.run_id}_{ticker}",
                                )
                                ctx.live_order_count += 1
                                audit_log(
                                    ctx.audit_ctx,
                                    event_type="PARTIAL_EXIT",
                                    ticker=ticker,
                                    action="SELL",
                                    status=partial_submission.status,
                                    reason=f"partial take profit ({unrealized_plpc*100:.2f}%)",
                                    profile_name=ctx.profile_name,
                                    regime=ctx.current_regime,
                                    signal=signal,
                                    ai_score=ai_score,
                                    order_id=partial_submission.order_id,
                                    order_type=partial_submission.order_type,
                                    side=partial_submission.side,
                                    quantity=sell_qty,
                                )
                                notify_info("💰 Partial Profit Taken", f"{ticker}: Sold {sell_qty} shares at +{unrealized_plpc*100:.2f}% profit.")
                            except Exception as e:
                                print(f"  Partial exit error for {ticker}: {e}")
                                if isinstance(e, ConnectionError) and ctx.execute_orders:
                                    notify_error(f"CRITICAL: Network error during partial exit for {ticker}", e)
                                    raise
                                ctx.api_error_count += 1
                                audit_log(
                                    ctx.audit_ctx,
                                    event_type="PARTIAL_EXIT",
                                    ticker=ticker,
                                    action="SELL",
                                    status="ERROR",
                                    reason=str(e),
                                    profile_name=ctx.profile_name,
                                    regime=ctx.current_regime,
                                    signal=signal,
                                    ai_score=ai_score,
                                    quantity=sell_qty,
                                )
    
                # Position Trimming / Rebalancing (Phase 14-B)
                # 현재 비중이 목표치보다 너무 크면 일부 매도 (20% 초과 시)
                rebalance_thr = float(getattr(ctx.settings, "rebalance_threshold_pct", 0.20))
                portfolio_val = float(ctx.account["portfolio_value"])
                target_weight = float(ctx.settings.max_position_pct)
                current_weight = float(position["market_value"]) / portfolio_val if portfolio_val > 0 else 0
    
                if not exit_decision.should_exit and current_weight > target_weight * (1 + rebalance_thr):
                    excess_value = float(position["market_value"]) - (portfolio_val * target_weight)
                    if excess_value > 50: # 최소 50달러 이상일 때만 리밸런싱
                        trim_qty = round(excess_value / current_price, 4)
                        print(f"  REBALANCE_TRIM: {ticker} weight {current_weight*100:.1f}% > target {target_weight*100:.1f}%. Trimming {trim_qty}")
                        if ctx.can_submit_orders:
                            try:
                                trim_submission = ctx.broker_adapter.submit_sell_qty(
                                    ticker,
                                    trim_qty,
                                    limit_price=execution_reference_price(
                                        None,
                                        fallback=current_price,
                                    ),
                                    market_clock=ctx.market_clock,
                                    slippage_pct=ctx.extended_slippage,
                                    client_order_id=f"trim_{ctx.run_id}_{ticker}",
                                )
                                ctx.live_order_count += 1
                                audit_log(
                                    ctx.audit_ctx,
                                    event_type="REBALANCE_TRIM",
                                    ticker=ticker,
                                    action="SELL",
                                    status=trim_submission.status,
                                    reason=f"rebalance trim (weight={current_weight:.4f})",
                                    profile_name=ctx.profile_name,
                                    regime=ctx.current_regime,
                                    signal=signal,
                                    ai_score=ai_score,
                                    order_id=trim_submission.order_id,
                                    order_type=trim_submission.order_type,
                                    side=trim_submission.side,
                                    quantity=trim_qty,
                                )
                            except Exception as e:
                                print(f"  Trim error for {ticker}: {e}")
                                if isinstance(e, ConnectionError) and ctx.execute_orders:
                                    notify_error(f"CRITICAL: Network error during rebalance trim for {ticker}", e)
                                    raise
                                ctx.api_error_count += 1
                                audit_log(
                                    ctx.audit_ctx,
                                    event_type="REBALANCE_TRIM",
                                    ticker=ticker,
                                    action="SELL",
                                    status="ERROR",
                                    reason=str(e),
                                    profile_name=ctx.profile_name,
                                    regime=ctx.current_regime,
                                    signal=signal,
                                    ai_score=ai_score,
                                    quantity=trim_qty,
                                )
    
                if not exit_decision.should_exit:
                    continue
    
                if not ctx.can_submit_orders:
                    label = execution_block_label(ctx.execute_orders, ctx.market_clock)
                    print(
                        f"  {label}: would CLOSE {ticker} "
                        f"reason='{exit_decision.reason}'"
                    )
                    ctx.skipped_reasons[f"exit:{label.lower()}"] += 1
                    audit_log(
                        ctx.audit_ctx,
                        event_type="SKIP_EXIT",
                        ticker=ticker,
                        action="CLOSE",
                        status="SKIPPED",
                        reason=f"{label}: {exit_decision.reason}",
                        profile_name=ctx.profile_name,
                        regime=ctx.current_regime,
                        signal=signal,
                        ai_score=ai_score,
                    )
                    continue
    
                exit_qty = float(position["qty"])
                exit_submission = ctx.broker_adapter.submit_sell_qty(
                    ticker,
                    exit_qty,
                    limit_price=execution_reference_price(
                        None,
                        fallback=current_price,
                    ),
                    market_clock=ctx.market_clock,
                    slippage_pct=ctx.extended_slippage,
                    client_order_id=f"exit_{ctx.run_id}_{ticker}",
                )
                ctx.live_order_count += 1
    
                log_order(
                    ticker=ticker,
                    notional=0.0,
                    order_id=exit_submission.order_id,
                    status=exit_submission.status,
                    side=exit_submission.side,
                    order_type=exit_submission.order_type,
                    reason=exit_decision.reason,
                )
    
                print(
                    f"  PAPER_CLOSE_SUBMITTED: {ticker}, "
                    f"order_id={exit_submission.order_id}, status={exit_submission.status}"
                )
                audit_log(
                    ctx.audit_ctx,
                    event_type="FULL_EXIT",
                    ticker=ticker,
                    action="SELL",
                    status=exit_submission.status,
                    reason=exit_decision.reason,
                    profile_name=ctx.profile_name,
                    regime=ctx.current_regime,
                    signal=signal,
                    ai_score=ai_score,
                    order_id=exit_submission.order_id,
                    order_type=exit_submission.order_type,
                    side=exit_submission.side,
                )
    
                checked_order = ctx.broker_adapter.wait_for_order_status(exit_submission.order_id)
                log_order_status(
                    ticker=ticker,
                    order_id=checked_order["id"],
                    status=checked_order["status"],
                    side=checked_order["side"],
                    order_type=checked_order["type"],
                    filled_qty=checked_order["filled_qty"],
                    filled_avg_price=checked_order["filled_avg_price"],
                    reason=exit_decision.reason,
                )
                print(
                    f"  CLOSE_STATUS_CHECK: status={checked_order['status']}, "
                    f"filled_qty={checked_order['filled_qty']}, "
                    f"filled_avg_price={checked_order['filled_avg_price']}"
                )
                audit_log(
                    ctx.audit_ctx,
                    event_type="FULL_EXIT_STATUS",
                    ticker=ticker,
                    action="SELL",
                    status=str(checked_order["status"]),
                    reason=exit_decision.reason,
                    profile_name=ctx.profile_name,
                    regime=ctx.current_regime,
                    signal=signal,
                    ai_score=ai_score,
                    order_id=str(checked_order["id"]),
                    order_type=str(checked_order["type"]),
                    side=str(checked_order["side"]),
                    filled_qty=checked_order["filled_qty"],
                    filled_avg_price=checked_order["filled_avg_price"],
                )
    
                notify_order(
                    action="CLOSE",
                    ticker=ticker,
                    status=checked_order["status"],
                    order_id=checked_order["id"],
                    reason=exit_decision.reason,
                    filled_qty=checked_order["filled_qty"],
                    filled_avg_price=checked_order["filled_avg_price"],
                )
    
                if ticker in ctx.open_symbols:
                    ctx.open_symbols.remove(ticker)
                    ctx.positions_by_symbol.pop(ticker, None)
                    ctx.positions_count -= 1
                    ctx.sleeve_ctx.record_exit(ticker)
    
            except Exception as exc:
                if isinstance(exc, ConnectionError) and ctx.execute_orders:
                    notify_error("CRITICAL: Network error during exit loop", exc)
                    raise
                print(f"{ticker}: EXIT_CHECK_ERROR - {exc}")
                ctx.exit_summary_rows.append(f"{ticker}: EXIT_CHECK_ERROR - {exc}")
                ctx.api_error_count += 1
                audit_log(
                    ctx.audit_ctx,
                    event_type="EXIT_ERROR",
                    ticker=ticker,
                    action="CLOSE",
                    status="ERROR",
                    reason=str(exc),
                    profile_name=ctx.profile_name,
                    regime=ctx.current_regime,
                )
                notify_error(f"{ticker} exit check error", exc)
    
