"""Tournament sleeve buy path — tournament_paper profile + alpha model."""

from __future__ import annotations

from src.order_intent import build_buy_intent
from src.portfolio_sleeves import TOURNAMENT_SLEEVE_ID, load_sleeve_definitions
from src.position_dust import effective_position
from src.position_sizing import cap_single_order_amount
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

        if signal != "BUY":
            ctx.buy_summary_rows.append(
                f"{ticker}: TOURNAMENT_SKIP signal={signal} alpha={alpha.alpha_score:.3f}"
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
        target_amount = min(sleeve_cash, portfolio_value * position_pct)
        if target_amount < 10.0:
            ctx.buy_summary_rows.append(
                f"{ticker}: TOURNAMENT_NOT_ALLOWED target amount below minimum"
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

        limit_price = execution_reference_price(
            latest.to_dict() if hasattr(latest, "to_dict") else None,
            fallback=float(latest["close"]),
        )
        budget_before = ctx.sleeve_ctx.budget_remaining.get(TOURNAMENT_SLEEVE_ID)
        buy_intent = build_buy_intent(
            run_id=ctx.run_id,
            ticker=ticker,
            notional=order_amount,
            signal=signal,
            ai_score=ai_score,
            risk_reason=alpha.reason,
            client_order_id=f"tour_{ctx.run_id}_{ticker}",
            **ctx.sleeve_ctx.buy_intent_sleeve_kwargs(
                order_amount,
                sleeve_id=TOURNAMENT_SLEEVE_ID,
                budget_before_submit=budget_before,
            ),
        )

        try:
            submission = ctx.broker_adapter.submit_buy_notional(
                ticker=ticker,
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
            ctx.sleeve_ctx.consume_submit_budget(
                order_amount,
                sleeve_id=TOURNAMENT_SLEEVE_ID,
            )
            audit_log(
                ctx.audit_ctx,
                event_type="BUY_SUBMITTED",
                ticker=ticker,
                action="BUY",
                status=submission.status,
                reason=alpha.reason,
                profile_name=ctx.profile_name,
                regime=ctx.current_regime,
                signal=signal,
                ai_score=ai_score,
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
            if order_is_filled(checked["status"]):
                ctx.sleeve_ctx.record_fill(ticker, sleeve_id=TOURNAMENT_SLEEVE_ID)
                filled = filled_notional(checked, order_amount)
                if filled > 0:
                    ctx.cash -= filled
                    ctx.current_gross_exposure += filled
                    ctx.guard_open_symbols.add(ticker)
                    ctx.open_symbols.add(ticker)
            ctx.buy_summary_rows.append(
                f"{ticker}: TOURNAMENT_BUY status={checked['status']} "
                f"alpha={alpha.alpha_score:.3f} notional=${order_amount:.2f}"
            )
        except Exception as exc:
            ctx.api_error_count += 1
            ctx.buy_summary_rows.append(f"{ticker}: TOURNAMENT_BUY_ERROR {exc}")
