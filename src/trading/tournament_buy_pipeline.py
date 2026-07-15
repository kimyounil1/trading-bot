"""Tournament sleeve buy path — tournament_paper profile + alpha model."""

from __future__ import annotations

from src.instrument_meta import (
    adjust_position_cap_for_instrument,
    check_instrument_buy_allowed,
)
from src.order_intent import build_buy_intent
from src.rank_ai_gate import rank_ai_entry_signal
from src.rank_quality_risk import evaluate_rank_quality_risk
from src.portfolio_sleeves import TOURNAMENT_SLEEVE_ID, load_sleeve_definitions
from src.position_dust import effective_position
from src.position_sizing import cap_single_order_amount
from src.risk_manager import apply_effective_leverage_exposure_limits
from src.settings import merge_settings_overlay
from src.tournament_alpha_model import select_tournament_candidates
from src.trading.bot_helpers import (
    audit_log,
    execution_block_label,
    execution_reference_price,
    filled_notional,
    get_signal_for_ticker,
    order_is_filled,
)
from src.trading.run_context import TradingRunContext
from src.trading.leveraged_product_routing import resolve_leveraged_product_route
from src.trading_config_guard import load_named_profile_overlay


def _tournament_settings(ctx: TradingRunContext):
    overlay = load_named_profile_overlay("tournament_paper")
    return merge_settings_overlay(ctx.settings, overlay)


def _tournament_open_position_count(ctx: TradingRunContext) -> int:
    count = 0
    for symbol, position in ctx.positions_by_symbol.items():
        sleeve_id = ctx.sleeve_ctx.sleeve_position_map.get(str(symbol).upper(), "")
        if sleeve_id != TOURNAMENT_SLEEVE_ID:
            continue
        if effective_position(position, min_usd=ctx.dust_min_usd):
            count += 1
    return count


def _rank_audit_fields(payload) -> tuple[float | None, float | None]:
    if payload is None:
        return None, None
    if isinstance(payload, dict):
        return payload.get("score"), payload.get("percentile")
    return getattr(payload, "score", None), getattr(payload, "percentile", None)


def run_tournament_buy_pipeline(ctx: TradingRunContext) -> None:
    if not ctx.sleeve_ctx.enabled or not ctx.sleeve_ctx.recon_ok:
        return

    definitions = load_sleeve_definitions(ctx.settings)
    tournament_def = definitions.get(TOURNAMENT_SLEEVE_ID)
    if tournament_def is None or not tournament_def.enabled:
        return

    budget = ctx.sleeve_ctx.snapshot.sleeves.get(TOURNAMENT_SLEEVE_ID)
    tour_budget = float(
        ctx.sleeve_ctx.budget_remaining.get(
            TOURNAMENT_SLEEVE_ID,
            budget.order_budget if budget else 0.0,
        )
    )
    if tour_budget < 10.0:
        print(f"Tournament sleeve: skip buys (order_budget=${tour_budget:.2f})")
        return

    tournament_settings = _tournament_settings(ctx)
    ai_scores: dict[str, float | None] = {}
    for ticker in ctx.settings.tickers:
        try:
            _, _, ai_score = get_signal_for_ticker(
                ticker,
                ctx.ticker_data[ticker],
                tournament_settings,
                ai_model_bundle=ctx.ai_model_bundle,
                market_regime_bullish=ctx.market_regime_bullish,
                vix_df=ctx.vix_df,
                spy_df=ctx.spy_df,
                macro_df=ctx.macro_df,
                market_clock=ctx.market_clock,
            )
            ai_scores[str(ticker).upper()] = ai_score
        except Exception:
            ai_scores[str(ticker).upper()] = None

    picks = select_tournament_candidates(
        list(ctx.settings.tickers),
        rank_scores=ctx.rank_ai_gate_scores,
        ai_scores=ai_scores,
        settings=tournament_settings,
        max_picks=int(getattr(tournament_settings, "max_total_positions", 5)),
    )
    if not picks:
        print("Tournament sleeve: no alpha candidates")
        return

    print(f"Tournament sleeve: {len(picks)} candidate(s) from alpha model")
    portfolio_value = float(ctx.account["portfolio_value"])
    pending_tournament_buys = 0

    for ticker, alpha in picks.items():
        if ctx.orders_submitted >= ctx.settings.max_orders_per_run:
            break

        if ticker not in ctx.ticker_data:
            continue
        if effective_position(ctx.positions_by_symbol.get(ticker), min_usd=ctx.dust_min_usd):
            continue

        data_fresh, data_reason = ctx.price_data_freshness.get(
            ticker,
            (False, "price data not loaded"),
        )
        if not data_fresh:
            ctx.buy_summary_rows.append(f"{ticker}: TOURNAMENT_SKIP {data_reason}")
            continue

        try:
            signal, latest, ai_score = get_signal_for_ticker(
                ticker,
                ctx.ticker_data[ticker],
                tournament_settings,
                ai_model_bundle=ctx.ai_model_bundle,
                market_regime_bullish=ctx.market_regime_bullish,
                vix_df=ctx.vix_df,
                spy_df=ctx.spy_df,
                macro_df=ctx.macro_df,
                market_clock=ctx.market_clock,
            )
        except Exception as exc:
            ctx.buy_summary_rows.append(f"{ticker}: TOURNAMENT_ERROR {exc}")
            continue

        entry_signal = rank_ai_entry_signal(signal, tournament_settings)
        if entry_signal != "BUY":
            ctx.buy_summary_rows.append(
                f"{ticker}: TOURNAMENT_SKIP signal={signal} alpha={alpha.alpha_score:.3f}"
            )
            continue

        quality_risk = evaluate_rank_quality_risk(
            ctx.ticker_data[ticker],
            tournament_settings,
        )

        route = resolve_leveraged_product_route(
            ctx,
            ticker,
            signal=entry_signal,
            fallback_price=float(latest["close"]),
            allow_leveraged=quality_risk.allow_leveraged,
        )
        if not route.route_allowed:
            ctx.buy_summary_rows.append(
                f"{ticker}: TOURNAMENT_NOT_ALLOWED {route.reason}"
            )
            continue
        execution_ticker = route.execution_ticker
        if effective_position(
            ctx.positions_by_symbol.get(execution_ticker),
            min_usd=ctx.dust_min_usd,
        ):
            continue
        if route.leveraged:
            print(
                f"{ticker}: tournament leveraged product route -> "
                f"{execution_ticker}"
            )
        elif bool(getattr(ctx.settings, "auto_discover_leveraged_products", False)):
            print(f"{ticker}: tournament ordinary-stock fallback ({route.reason})")

        instrument_ok, instrument_reason = check_instrument_buy_allowed(
            execution_ticker,
            ctx.guard_open_symbols,
            allow_leveraged_etfs=bool(
                getattr(tournament_settings, "allow_leveraged_etfs", False)
            ),
            leveraged_etf_allowlist=list(
                getattr(tournament_settings, "leveraged_etf_allowlist", [])
            ),
            max_leveraged_etf_positions=int(
                getattr(tournament_settings, "max_leveraged_etf_positions", 1)
            ),
            block_leveraged_etfs_vix_above=float(
                getattr(
                    tournament_settings,
                    "block_leveraged_etfs_vix_above",
                    0.0,
                )
            ),
            vix_df=ctx.vix_df,
        )
        if not instrument_ok:
            ctx.buy_summary_rows.append(
                f"{ticker}: TOURNAMENT_NOT_ALLOWED {instrument_reason}"
            )
            continue

        sleeve_cash = float(
            ctx.sleeve_ctx.budget_remaining.get(TOURNAMENT_SLEEVE_ID, 0.0)
        )
        max_positions = int(getattr(tournament_settings, "max_total_positions", 12))
        if _tournament_open_position_count(ctx) + pending_tournament_buys >= max_positions:
            ctx.buy_summary_rows.append(
                f"{ticker}: TOURNAMENT_NOT_ALLOWED max tournament positions reached"
            )
            continue
        if sleeve_cash < 10.0:
            ctx.buy_summary_rows.append(
                f"{ticker}: TOURNAMENT_NOT_ALLOWED tournament sleeve budget exhausted"
            )
            continue

        position_pct = float(getattr(tournament_settings, "max_position_pct", 0.35))
        position_pct = adjust_position_cap_for_instrument(
            position_pct,
            execution_ticker,
        )
        target_amount = min(sleeve_cash, portfolio_value * position_pct)
        target_amount *= quality_risk.notional_multiplier
        if target_amount < 10.0:
            ctx.buy_summary_rows.append(
                f"{ticker}: TOURNAMENT_NOT_ALLOWED target amount below minimum "
                f"({quality_risk.reason})"
            )
            continue

        order_amount = min(
            float(target_amount),
            portfolio_value * float(alpha.max_position_pct),
            sleeve_cash,
        )
        order_amount = cap_single_order_amount(
            order_amount,
            portfolio_value,
            tournament_settings,
        )
        leverage_cap = apply_effective_leverage_exposure_limits(
            ticker=execution_ticker,
            order_amount=order_amount,
            portfolio_value=portfolio_value,
            positions_by_symbol=ctx.positions_by_symbol,
            settings=ctx.settings,
        )
        if not leverage_cap.allowed:
            ctx.buy_summary_rows.append(
                f"{ticker}: TOURNAMENT_NOT_ALLOWED {leverage_cap.reason}"
            )
            continue
        order_amount = leverage_cap.target_amount
        if order_amount < 10.0:
            continue

        _, _, _, order_amount = ctx.sleeve_ctx.apply_pre_candidate_gate(
            sleeve_id=TOURNAMENT_SLEEVE_ID,
            risk_allowed=True,
            risk_reason=alpha.reason,
            target_amount=order_amount,
            order_amount=order_amount,
        )
        if order_amount < 10.0:
            continue

        rank_score, rank_percentile = _rank_audit_fields(
            ctx.rank_ai_gate_scores.get(ticker)
        )
        plan_budget_before = ctx.sleeve_ctx.budget_remaining.get(
            TOURNAMENT_SLEEVE_ID
        )
        plan_budget_after = (
            max(0.0, float(plan_budget_before) - order_amount)
            if plan_budget_before is not None
            else None
        )
        audit_log(
            ctx.audit_ctx,
            event_type="BUY_PLAN",
            ticker=ticker,
            action="BUY",
            status="PLANNED",
            reason=f"{quality_risk.reason}; {route.reason}",
            profile_name=ctx.profile_name,
            regime=ctx.current_regime,
            signal=entry_signal,
            ai_score=ai_score,
            rank_ai_score=rank_score,
            rank_ai_percentile=rank_percentile,
            notional=order_amount,
            signal_ticker=ticker,
            execution_ticker=execution_ticker,
            decision_market_date=quality_risk.market_date,
            quality_notional_multiplier=quality_risk.notional_multiplier,
            quality_allow_leveraged=quality_risk.allow_leveraged,
            quality_high_drawdown=quality_risk.high_drawdown,
            quality_downtrend=quality_risk.downtrend,
            route_leveraged=route.leveraged,
            portfolio_value=portfolio_value,
            planned_notional_pct=(
                order_amount / portfolio_value if portfolio_value > 0 else None
            ),
            reference_price=route.reference_price,
            **ctx.sleeve_ctx.audit_fields(
                sleeve_id=TOURNAMENT_SLEEVE_ID,
                budget_before=plan_budget_before,
                budget_after=plan_budget_after,
            ),
        )

        submit_ok, submit_reason = ctx.sleeve_ctx.check_submit_budget(
            order_amount,
            sleeve_id=TOURNAMENT_SLEEVE_ID,
        )
        if not submit_ok:
            ctx.buy_summary_rows.append(f"{ticker}: TOURNAMENT_SKIP {submit_reason}")
            continue

        if not ctx.can_submit_orders:
            label = execution_block_label(ctx.execute_orders, ctx.market_clock)
            ctx.buy_summary_rows.append(
                f"{ticker}: TOURNAMENT_{label} ${order_amount:.2f}"
            )
            continue

        limit_price = route.reference_price
        budget_before = ctx.sleeve_ctx.budget_remaining.get(TOURNAMENT_SLEEVE_ID)
        buy_intent = build_buy_intent(
            run_id=ctx.run_id,
            ticker=execution_ticker,
            notional=order_amount,
            signal=entry_signal,
            ai_score=ai_score,
            risk_reason=alpha.reason,
            client_order_id=f"tour_{ctx.run_id}_{execution_ticker}",
            **ctx.sleeve_ctx.buy_intent_sleeve_kwargs(
                order_amount,
                sleeve_id=TOURNAMENT_SLEEVE_ID,
                budget_before_submit=budget_before,
            ),
        )

        try:
            submission = ctx.broker_adapter.submit_buy_notional(
                ticker=execution_ticker,
                notional=order_amount,
                limit_price=limit_price,
                market_clock=ctx.market_clock,
                slippage_pct=ctx.extended_slippage,
                client_order_id=buy_intent.client_order_id,
            )
            ctx.live_order_count += 1
            ctx.orders_submitted += 1
            pending_tournament_buys += 1
            ctx.submitted_notional_today += order_amount
            ctx.guard_open_symbols.add(execution_ticker)
            ctx.sleeve_ctx.consume_submit_budget(
                order_amount,
                sleeve_id=TOURNAMENT_SLEEVE_ID,
            )
            audit_log(
                ctx.audit_ctx,
                event_type="BUY_SUBMITTED",
                ticker=execution_ticker,
                action="BUY",
                status=submission.status,
                reason=alpha.reason,
                profile_name=ctx.profile_name,
                regime=ctx.current_regime,
                signal=entry_signal,
                ai_score=ai_score,
                rank_ai_score=rank_score,
                rank_ai_percentile=rank_percentile,
                order_id=submission.order_id,
                notional=order_amount,
                order_intent_id=buy_intent.intent_id,
                **ctx.sleeve_ctx.audit_fields(
                    sleeve_id=TOURNAMENT_SLEEVE_ID,
                    budget_before=buy_intent.sleeve_budget_before,
                    budget_after=buy_intent.sleeve_budget_after,
                ),
            )
            checked = ctx.broker_adapter.wait_for_order_status(submission.order_id)
            audit_log(
                ctx.audit_ctx,
                event_type="BUY_STATUS",
                ticker=execution_ticker,
                action="BUY",
                status=str(checked["status"]),
                reason=alpha.reason,
                profile_name=ctx.profile_name,
                regime=ctx.current_regime,
                signal=entry_signal,
                ai_score=ai_score,
                order_id=str(checked["id"]),
                order_type=str(checked["type"]),
                side=str(checked["side"]),
                notional=order_amount,
                filled_qty=checked["filled_qty"],
                filled_avg_price=checked["filled_avg_price"],
                reference_price=route.reference_price,
                **ctx.sleeve_ctx.audit_fields(
                    sleeve_id=TOURNAMENT_SLEEVE_ID,
                ),
            )
            if order_is_filled(checked["status"]):
                ctx.sleeve_ctx.record_fill(
                    execution_ticker,
                    sleeve_id=TOURNAMENT_SLEEVE_ID,
                )
                filled = filled_notional(checked, order_amount)
                if filled > 0:
                    ctx.cash -= filled
                    ctx.current_gross_exposure += filled
                    ctx.guard_open_symbols.add(execution_ticker)
                    ctx.open_symbols.add(execution_ticker)
            ctx.buy_summary_rows.append(
                f"{ticker}->{execution_ticker}: TOURNAMENT_BUY "
                f"status={checked['status']} "
                f"alpha={alpha.alpha_score:.3f} notional=${order_amount:.2f}"
            )
        except Exception as exc:
            ctx.api_error_count += 1
            ctx.buy_summary_rows.append(f"{ticker}: TOURNAMENT_BUY_ERROR {exc}")
