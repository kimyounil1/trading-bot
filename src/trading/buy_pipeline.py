"""Buy candidate collection, MVO allocation, and order submission."""

from __future__ import annotations

from src.buy_guards import apply_sector_score_bonus, apply_shared_buy_guards
from src.instrument_meta import format_audit_reason
from src.llm_analyst import llm_cache_only_for_run
from src.logger import log_order, log_order_status, log_signal
from src.macro_events import get_macro_event_risk
from src.notifier import notify_error, notify_info, notify_order
from src.order_intent import build_buy_intent
from src.portfolio_optimizer import compute_weights_from_ticker_data
from src.position_dust import effective_position
from src.position_sizing import cap_single_order_amount, conviction_adjustments
from src.rank_ai_gate import apply_rank_ai_buy_gate
from src.risk_manager import (
    apply_buy_safety_limits,
    apply_effective_leverage_exposure_limits,
    apply_portfolio_exposure_limits,
    check_additional_buy_allowed,
    check_buy_allowed,
)
from src.trading.bot_helpers import (
    audit_log,
    execution_block_label,
    filled_notional,
    format_llm_verdict,
    get_signal_for_ticker,
    order_is_filled,
)
from src.trading.run_context import TradingRunContext
from src.trading.tournament_buy_pipeline import run_tournament_buy_pipeline


def run_buy_pipeline(ctx: TradingRunContext) -> None:
    # 2) 신규 매수 후보 수집 (Pass 1: 신호 생성 + 리스크 검사, 주문 미제출)
    approved_buys: list[dict] = []
    
    # 매크로 이벤트 리스크 체크 (Phase 18-B)
    macro_risk_active = False
    macro_risk_reason = ""
    if getattr(ctx.settings, "macro_event_risk_enabled", False):
        macro_risk_active, macro_risk_reason = get_macro_event_risk(
            lookforward_days=int(getattr(ctx.settings, "macro_event_lookahead_days", 2)),
            lookback_days=int(getattr(ctx.settings, "macro_event_lookback_days", 1))
        )
        if macro_risk_active:
            print(f"MACRO_EVENT_RISK_ACTIVE: {macro_risk_reason}. New buys will be restricted.")
    
    if ctx.margin_leverage_block_active:
        print("New buys blocked until margin leverage stress gate passes (see runbook).")
    
    for ticker in ctx.settings.tickers:
        try:
            data_fresh, data_reason = ctx.price_data_freshness.get(
                ticker,
                (False, "price data not loaded"),
            )
            if not data_fresh:
                print(f"{ticker}: SKIP_BUY - {data_reason}")
                ctx.buy_summary_rows.append(f"{ticker}: SKIP_BUY {data_reason}")
                ctx.skipped_reasons[f"buy:{data_reason}"] += 1
                ctx.data_error_count += 1
                audit_log(
                    ctx.audit_ctx,
                    event_type="SKIP_BUY",
                    ticker=ticker,
                    action="BUY",
                    status="SKIPPED",
                    reason=data_reason,
                    profile_name=ctx.profile_name,
                    regime=ctx.current_regime,
                )
                continue
    
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
    
            ai_score = apply_sector_score_bonus(ticker, ai_score, ctx.top_sectors)
            conviction = conviction_adjustments(ctx.settings, ai_score)
            if conviction.label != "neutral":
                print(f"{ticker}: sizing {conviction.label}")
    
            llm_is_ok = None
            llm_reason = ""
    
            held_position = effective_position(
                ctx.positions_by_symbol.get(ticker), min_usd=ctx.dust_min_usd
            )
            if held_position is not None:
                # 13-A: 이미 보유 중인 종목이라도 목표 비중에 미달하면 추가 매수 (Averaging up/down)
                risk = check_additional_buy_allowed(
                    signal=signal,
                    cash=ctx.cash,
                    portfolio_value=float(ctx.account["portfolio_value"]),
                    current_position_value=float(held_position["market_value"]),
                    position_mult=conviction.position_mult,
                    cash_buffer_mult=conviction.cash_buffer_mult,
                )
                risk_allowed = risk.allowed
                risk_reason = risk.reason
                target_amount = risk.target_amount
                
                # 추가 매수 시에도 최소 금액(예: 10달러) 이상일 때만 진행
                if risk_allowed and target_amount < 10.0:
                    risk_allowed = False
                    risk_reason = f"additional buy amount too small (${target_amount:.2f})"
                    target_amount = 0.0
            else:
                risk = check_buy_allowed(
                    signal=signal,
                    cash=ctx.cash,
                    current_positions_count=ctx.meaningful_positions_count,
                    portfolio_value=float(ctx.account["portfolio_value"]),
                    ticker=ticker,
                    position_mult=conviction.position_mult,
                    cash_buffer_mult=conviction.cash_buffer_mult,
                )
                risk_allowed = risk.allowed
                risk_reason = risk.reason
                target_amount = risk.target_amount
    
            if (
                risk_allowed
                and getattr(ctx.settings, "use_ai_score", False)
                and (
                    ai_score is None
                    or ai_score < float(ctx.settings.ai_score_buy_threshold)
                )
            ):
                risk_allowed = False
                risk_reason = (
                    f"ai score filter blocked "
                    f"(score={ai_score}, threshold={ctx.settings.ai_score_buy_threshold})"
                )
                target_amount = 0.0
    
            guard = apply_shared_buy_guards(
                ticker=ticker,
                position=held_position,
                settings=ctx.settings,
                risk_allowed=risk_allowed,
                risk_reason=risk_reason,
                target_amount=target_amount,
                ai_score=ai_score,
                open_symbols=ctx.guard_open_symbols,
                ticker_data=ctx.ticker_data,
                vix_df=ctx.vix_df,
                macro_risk_active=macro_risk_active,
                macro_risk_reason=macro_risk_reason,
                margin_leverage_block_active=ctx.margin_leverage_block_active,
                margin_leverage_block_reason=ctx.margin_leverage_block_reason,
                llm_cache_only=llm_cache_only_for_run(execute_orders=ctx.execute_orders),
            )
            risk_allowed = guard.risk_allowed
            risk_reason = guard.risk_reason
            target_amount = guard.target_amount
            llm_is_ok = guard.llm_is_ok
            llm_reason = guard.llm_reason
    
            rank_gate = apply_rank_ai_buy_gate(
                ticker=ticker,
                settings=ctx.settings,
                risk_allowed=risk_allowed,
                risk_reason=risk_reason,
                target_amount=target_amount,
                scores=ctx.rank_ai_gate_scores,
            )
            risk_allowed = rank_gate.risk_allowed
            risk_reason = rank_gate.risk_reason
            target_amount = rank_gate.target_amount
    
            if risk_allowed and held_position is None and llm_is_ok is False:
                llm_advisory_only = bool(getattr(ctx.settings, "llm_advisory_only", True))
                if llm_advisory_only:
                    audit_log(
                        ctx.audit_ctx,
                        event_type="LLM_ADVISORY",
                        ticker=ticker,
                        action="BUY",
                        status="WOULD_REJECT",
                        reason=format_audit_reason(llm_reason, ticker),
                        profile_name=ctx.profile_name,
                        regime=ctx.current_regime,
                        signal=signal,
                        ai_score=ai_score,
                        llm_verdict=format_llm_verdict(llm_is_ok, llm_reason),
                        notional=target_amount,
                    )
    
            order_amount = cap_single_order_amount(
                target_amount,
                float(ctx.account["portfolio_value"]),
                ctx.settings,
            )
    
            if risk_allowed:
                safety = apply_buy_safety_limits(
                    ticker=ticker,
                    order_amount=order_amount,
                    submitted_notional_today=ctx.submitted_notional_today,
                    recent_buy_symbols=ctx.recent_buy_symbols,
                    portfolio_value=float(ctx.account["portfolio_value"]),
                )
                risk_allowed = safety.allowed
                risk_reason = safety.reason if not safety.allowed else risk_reason
                order_amount = safety.target_amount
    
            if risk_allowed:
                exposure = apply_portfolio_exposure_limits(
                    ticker=ticker,
                    order_amount=order_amount,
                    cash=float(ctx.cash),
                    portfolio_value=float(ctx.account["portfolio_value"]) * float(getattr(ctx.settings, "leverage_factor", 1.0)),
                    buying_power=float(ctx.account.get("buying_power", 0.0)),
                    current_gross_exposure=ctx.current_gross_exposure,
                    current_position_value=float(held_position["market_value"]) if held_position is not None else 0.0,
                    cash_buffer_mult=conviction.cash_buffer_mult,
                )
                risk_allowed = exposure.allowed
                risk_reason = exposure.reason if not exposure.allowed else risk_reason
                order_amount = exposure.target_amount
    
            if risk_allowed:
                leverage_cap = apply_effective_leverage_exposure_limits(
                    ticker=ticker,
                    order_amount=order_amount,
                    portfolio_value=float(ctx.account["portfolio_value"]),
                    positions_by_symbol=ctx.positions_by_symbol,
                )
                risk_allowed = leverage_cap.allowed
                risk_reason = leverage_cap.reason if not leverage_cap.allowed else risk_reason
                order_amount = leverage_cap.target_amount
    
            risk_allowed, risk_reason, target_amount, order_amount = (
                ctx.sleeve_ctx.apply_pre_candidate_gate(
                    risk_allowed=risk_allowed,
                    risk_reason=risk_reason,
                    target_amount=target_amount,
                    order_amount=order_amount,
                )
            )
    
            log_signal(
                ticker=ticker,
                signal=signal,
                close=latest["close"],
                ma20=latest["ma20"],
                ma50=latest["ma50"],
                rsi=latest["rsi"],
                ai_score=ai_score,
            )
    
            print(
                f"{ticker}: signal={signal}, "
                f"risk_allowed={risk_allowed}, "
                f"reason='{risk_reason}', "
                f"target_amount={target_amount:.2f}, "
                f"order_amount={order_amount:.2f}, "
                f"ai_score={ai_score}, "
                f"close={latest['close']:.2f}, "
                f"rsi={latest['rsi']:.2f}"
            )
    
            ctx.buy_summary_rows.append(
                f"{ticker}: signal={signal}, allowed={risk_allowed}, "
                f"reason={risk_reason}, order=${order_amount:.2f}, "
                f"ai_score={ai_score}"
            )
            if not risk_allowed:
                ctx.skipped_reasons[f"buy:{risk_reason}"] += 1
                audit_log(
                    ctx.audit_ctx,
                    event_type="SKIP_BUY",
                    ticker=ticker,
                    action="BUY",
                    status="SKIPPED",
                    reason=format_audit_reason(risk_reason, ticker),
                    profile_name=ctx.profile_name,
                    regime=ctx.current_regime,
                    signal=signal,
                    ai_score=ai_score,
                    rank_ai_score=rank_gate.score,
                    rank_ai_percentile=rank_gate.percentile,
                    llm_verdict=format_llm_verdict(llm_is_ok, llm_reason),
                    notional=order_amount,
                    **ctx.sleeve_ctx.audit_fields(
                        budget_after=0.0 if not risk_allowed else order_amount
                    ),
                )
    
            if risk_allowed:
                approved_buys.append({
                    "ticker": ticker,
                    "order_amount": order_amount,
                    "ai_score": ai_score,
                    "rank_ai_score": rank_gate.score,
                    "rank_ai_percentile": rank_gate.percentile,
                    "risk_reason": risk_reason,
                    "signal": signal,
                    "llm_verdict": format_llm_verdict(llm_is_ok, llm_reason),
                    "limit_price": float(latest["close"]),
                })
    
        except Exception as exc:
            print(f"{ticker}: ERROR - {exc}")
            ctx.buy_summary_rows.append(f"{ticker}: ERROR - {exc}")
            ctx.api_error_count += 1
            audit_log(
                ctx.audit_ctx,
                event_type="BUY_ERROR",
                ticker=ticker,
                action="BUY",
                status="ERROR",
                reason=str(exc),
                profile_name=ctx.profile_name,
                regime=ctx.current_regime,
            )
            notify_error(f"{ticker} bot error", exc)
    
    # 3) MVO 가중치 적용 (Pass 2: allocation_method에 따라 주문 금액 조정)
    allocation_method = getattr(ctx.settings, "allocation_method", "equal_weight")
    if allocation_method != "equal_weight" and len(approved_buys) > 1:
        candidate_tickers = [c["ticker"] for c in approved_buys]
        candidate_ai_scores = {
            c["ticker"]: float(c["ai_score"]) if c["ai_score"] is not None else 0.5
            for c in approved_buys
        }
        mvo_weights = compute_weights_from_ticker_data(
            candidate_tickers=candidate_tickers,
            ticker_data=ctx.ticker_data,
            ai_scores=candidate_ai_scores,
            allocation_method=allocation_method,
        )
        portfolio_value = float(ctx.account["portfolio_value"])
        for candidate in approved_buys:
            t = candidate["ticker"]
            mvo_amount = portfolio_value * mvo_weights.get(t, 1.0 / len(approved_buys))
            # Respect individual order cap
            candidate["order_amount"] = cap_single_order_amount(
                mvo_amount, portfolio_value, ctx.settings
            )
        print(
            f"MVO weights: "
            + ", ".join(
                f"{c['ticker']}={mvo_weights.get(c['ticker'], 0):.3f}"
                for c in approved_buys
            )
        )
    
    approved_buys = ctx.sleeve_ctx.trim_approved_buys(approved_buys)
    
    # 4) 주문 제출 (Pass 3)
    for candidate in approved_buys:
        ticker = candidate["ticker"]
        order_amount = candidate["order_amount"]
        risk_reason = candidate["risk_reason"]
        ai_score = candidate["ai_score"]
        signal = candidate["signal"]
        llm_verdict = candidate["llm_verdict"]
    
        if ctx.orders_submitted >= ctx.settings.max_orders_per_run:
            print("  SKIP_ORDER: max orders per run reached")
            ctx.buy_summary_rows.append(
                f"{ticker}: SKIP_ORDER max orders per run reached, "
                f"ai_score={ai_score}"
            )
            ctx.skipped_reasons["buy:max orders per run reached"] += 1
            audit_log(
                ctx.audit_ctx,
                event_type="SKIP_BUY",
                ticker=ticker,
                action="BUY",
                status="SKIPPED",
                reason="max orders per run reached",
                profile_name=ctx.profile_name,
                regime=ctx.current_regime,
                signal=signal,
                ai_score=ai_score,
                llm_verdict=llm_verdict,
                notional=order_amount,
            )
            continue
    
        if not ctx.can_submit_orders:
            label = execution_block_label(ctx.execute_orders, ctx.market_clock)
            print(
                f"  {label}: would BUY {ticker} "
                f"notional=${order_amount:.2f}"
            )
            ctx.buy_summary_rows.append(
                f"{ticker}: {label} would BUY ${order_amount:.2f}, "
                f"ai_score={ai_score}"
            )
            ctx.skipped_reasons[f"buy:{label.lower()}"] += 1
            audit_log(
                ctx.audit_ctx,
                event_type="SKIP_BUY",
                ticker=ticker,
                action="BUY",
                status="SKIPPED",
                reason=label,
                profile_name=ctx.profile_name,
                regime=ctx.current_regime,
                signal=signal,
                ai_score=ai_score,
                llm_verdict=llm_verdict,
                notional=order_amount,
            )
            ctx.orders_submitted += 1
            ctx.submitted_notional_today += order_amount
            continue
    
        safety_check = ctx.live_safety_guard.check_new_buy(
            notional=order_amount,
            open_positions_count=ctx.meaningful_positions_count,
        )
        if not safety_check.allowed:
            print(f"  LIVE_SAFETY_BLOCK: would BUY {ticker} — {safety_check.reason}")
            ctx.buy_summary_rows.append(
                f"{ticker}: LIVE_SAFETY_BLOCK {safety_check.reason}, ai_score={ai_score}"
            )
            ctx.skipped_reasons["buy:live_safety"] += 1
            buy_intent = build_buy_intent(
                run_id=ctx.run_id,
                ticker=ticker,
                notional=order_amount,
                signal=signal,
                ai_score=ai_score,
                rank_ai_score=candidate.get("rank_ai_score"),
                rank_ai_percentile=candidate.get("rank_ai_percentile"),
                llm_verdict=llm_verdict,
                risk_reason=risk_reason,
            )
            audit_log(
                ctx.audit_ctx,
                event_type="SKIP_BUY",
                ticker=ticker,
                action="BUY",
                status="SKIPPED",
                reason=f"live safety: {safety_check.reason}",
                profile_name=ctx.profile_name,
                regime=ctx.current_regime,
                signal=signal,
                ai_score=ai_score,
                llm_verdict=llm_verdict,
                notional=order_amount,
                risk_block_reason=safety_check.reason,
                order_intent_id=buy_intent.intent_id,
            )
            continue
    
        submit_ok, submit_reason = ctx.sleeve_ctx.check_submit_budget(order_amount)
        if not submit_ok:
            ctx.skipped_reasons["buy:core sleeve budget exhausted"] += 1
            audit_log(
                ctx.audit_ctx,
                event_type="SKIP_BUY",
                ticker=ticker,
                action="BUY",
                status="SKIPPED",
                reason=submit_reason,
                profile_name=ctx.profile_name,
                regime=ctx.current_regime,
                signal=signal,
                ai_score=ai_score,
                llm_verdict=llm_verdict,
                notional=order_amount,
                **ctx.sleeve_ctx.audit_fields(
                    budget_before=ctx.sleeve_ctx.core_budget_remaining
                ),
            )
            continue
    
        sleeve_budget_before_submit = ctx.sleeve_ctx.core_budget_remaining
        buy_intent = build_buy_intent(
            run_id=ctx.run_id,
            ticker=ticker,
            notional=order_amount,
            signal=signal,
            ai_score=ai_score,
            rank_ai_score=candidate.get("rank_ai_score"),
            rank_ai_percentile=candidate.get("rank_ai_percentile"),
            llm_verdict=llm_verdict,
            risk_reason=risk_reason,
            client_order_id=f"buy_{ctx.run_id}_{ticker}",
            **ctx.sleeve_ctx.buy_intent_sleeve_kwargs(
                order_amount,
                budget_before_submit=sleeve_budget_before_submit,
            ),
        )
        try:
            buy_submission = ctx.broker_adapter.submit_buy_notional(
                ticker=ticker,
                notional=order_amount,
                limit_price=float(candidate["limit_price"]),
                market_clock=ctx.market_clock,
                slippage_pct=ctx.extended_slippage,
                client_order_id=buy_intent.client_order_id,
            )
            ctx.live_safety_guard.record_order_success()
            ctx.live_order_count += 1
            ctx.orders_submitted += 1
            ctx.submitted_notional_today += order_amount
            ctx.sleeve_ctx.consume_submit_budget(order_amount)
    
            log_order(
                ticker=ticker,
                notional=order_amount,
                order_id=buy_submission.order_id,
                status=buy_submission.status,
                side=buy_submission.side,
                order_type=buy_submission.order_type,
                reason=risk_reason,
            )
    
            print(
                f"  PAPER_ORDER_SUBMITTED: BUY {ticker} "
                f"notional=${order_amount:.2f}, "
                f"session={ctx.market_clock.session.value}, "
                f"order_id={buy_submission.order_id}, status={buy_submission.status}"
            )
            audit_log(
                ctx.audit_ctx,
                event_type="BUY_SUBMITTED",
                ticker=ticker,
                action="BUY",
                status=buy_submission.status,
                reason=risk_reason,
                profile_name=ctx.profile_name,
                regime=ctx.current_regime,
                signal=signal,
                ai_score=ai_score,
                rank_ai_score=candidate.get("rank_ai_score"),
                rank_ai_percentile=candidate.get("rank_ai_percentile"),
                llm_verdict=llm_verdict,
                order_id=buy_submission.order_id,
                order_type=buy_submission.order_type,
                side=buy_submission.side,
                notional=order_amount,
                order_intent_id=buy_intent.intent_id,
                broker_order_id=buy_submission.order_id,
                **ctx.sleeve_ctx.audit_fields(
                    budget_before=buy_intent.sleeve_budget_before,
                    budget_after=buy_intent.sleeve_budget_after,
                ),
            )
    
            checked_order = ctx.broker_adapter.wait_for_order_status(buy_submission.order_id)
            log_order_status(
                ticker=ticker,
                order_id=checked_order["id"],
                status=checked_order["status"],
                side=checked_order["side"],
                order_type=checked_order["type"],
                filled_qty=checked_order["filled_qty"],
                filled_avg_price=checked_order["filled_avg_price"],
                reason=risk_reason,
            )
            print(
                f"  BUY_STATUS_CHECK: status={checked_order['status']}, "
                f"filled_qty={checked_order['filled_qty']}, "
                f"filled_avg_price={checked_order['filled_avg_price']}"
            )
            audit_log(
                ctx.audit_ctx,
                event_type="BUY_STATUS",
                ticker=ticker,
                action="BUY",
                status=str(checked_order["status"]),
                reason=risk_reason,
                profile_name=ctx.profile_name,
                regime=ctx.current_regime,
                signal=signal,
                ai_score=ai_score,
                llm_verdict=llm_verdict,
                order_id=str(checked_order["id"]),
                order_type=str(checked_order["type"]),
                side=str(checked_order["side"]),
                notional=order_amount,
                filled_qty=checked_order["filled_qty"],
                filled_avg_price=checked_order["filled_avg_price"],
            )
    
            if order_is_filled(checked_order["status"]):
                notify_order(
                    action="BUY",
                    ticker=ticker,
                    status=checked_order["status"],
                    order_id=checked_order["id"],
                    reason=risk_reason,
                    filled_qty=checked_order["filled_qty"],
                    filled_avg_price=checked_order["filled_avg_price"],
                )
            else:
                print(
                    f"  BUY_PENDING: {ticker} limit order remains "
                    f"{checked_order['status']} (overnight/extended hours)"
                )
    
            ctx.buy_summary_rows.append(
                f"{ticker}: BUY_SUBMITTED status={checked_order['status']}, "
                f"filled_qty={checked_order['filled_qty']}, "
                f"filled_avg_price={checked_order['filled_avg_price']}, "
                f"ai_score={ai_score}"
            )
    
            filled_notional = filled_notional(checked_order, order_amount)
            if filled_notional > 0:
                if ticker not in ctx.guard_open_symbols:
                    ctx.guard_open_symbols.add(ticker)
                    ctx.open_symbols.add(ticker)
                    ctx.positions_count += 1
                ctx.cash -= filled_notional
                ctx.current_gross_exposure += filled_notional
                ctx.sleeve_ctx.record_fill(ticker, sleeve_id="core")
        except Exception as exc:
            ctx.live_safety_guard.record_order_failure()
            if isinstance(exc, ConnectionError) and ctx.execute_orders:
                notify_error(f"CRITICAL: Network error during buy execution for {ticker}", exc)
                raise
            print(f"  Buy order error for {ticker}: {exc}")
            ctx.api_error_count += 1
            audit_log(
                ctx.audit_ctx,
                event_type="BUY_ERROR",
                ticker=ticker,
                action="BUY",
                status="ERROR",
                reason=str(exc),
                profile_name=ctx.profile_name,
                regime=ctx.current_regime,
                signal=signal,
                ai_score=ai_score,
                notional=order_amount,
            )

    run_tournament_buy_pipeline(ctx)

