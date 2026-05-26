import argparse

import pandas as pd

from src.settings import load_settings
from src.data_loader import load_price_data_batch
from src.strategy import add_indicators, generate_signal, is_bullish_market_regime
from src.logger import log_signal, log_order, log_order_status
from src.risk_manager import (
    apply_buy_safety_limits,
    check_buy_allowed,
    check_exit_allowed,
    get_recent_buy_symbols,
    get_today_buy_notional,
)
from src.alpaca_client import (
    get_account_summary,
    get_open_symbols,
    get_positions_summary,
    submit_market_buy_notional_order,
    close_position_by_symbol,
    wait_for_order_status,
)
from src.market_clock import get_market_clock
from src.notifier import notify_order, notify_error, notify_run_summary
from src.ml_model import load_ai_score_model, predict_ai_score_from_bundle


def _apply_volume_volatility_filters(signal: str, indicator_df, settings) -> str:
    if signal != "BUY":
        return signal

    latest = indicator_df.iloc[-1]

    if getattr(settings, "volume_filter_enabled", False):
        lookback = int(getattr(settings, "volume_lookback_days", 20))
        if lookback <= 0:
            raise ValueError("volume_lookback_days must be positive")
        volume_ma = indicator_df["volume"].rolling(lookback).mean().iloc[-1]
        if (
            pd.isna(volume_ma)
            or volume_ma <= 0
            or latest["volume"] / volume_ma < float(settings.min_volume_ratio)
        ):
            return "HOLD"

    if getattr(settings, "volatility_filter_enabled", False):
        lookback = int(getattr(settings, "volatility_lookback_days", 20))
        if lookback <= 0:
            raise ValueError("volatility_lookback_days must be positive")
        volatility = indicator_df["close"].pct_change().rolling(lookback).std().iloc[-1]
        if pd.isna(volatility) or volatility > float(settings.max_volatility):
            return "HOLD"

    return signal


def _offline_account_summary() -> dict:
    return {
        "status": "UNKNOWN",
        "currency": "USD",
        "cash": 0.0,
        "portfolio_value": 0.0,
        "buying_power": 0.0,
        "positions_count": 0,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AI trading bot MVP. Default mode is dry-run."
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Submit real paper orders to Alpaca. Without this flag, dry-run only.",
    )
    return parser.parse_args()


def get_signal_for_ticker(
    ticker: str,
    raw_df,
    settings,
    ai_model_bundle=None,
    market_regime_bullish: bool = True,
) -> tuple[str, object, float | None]:
    if raw_df.empty:
        raise ValueError(f"No price data available for {ticker}")

    df = add_indicators(
        raw_df,
        ma_fast=settings.ma_fast,
        ma_slow=settings.ma_slow,
    )
    if df.empty:
        raise ValueError(
            f"Not enough price history to generate signal for {ticker} "
            f"(rows={len(raw_df)}, ma_slow={settings.ma_slow})"
        )
    signal = generate_signal(df, rsi_buy_limit=settings.rsi_buy_limit)
    if (
        signal == "BUY"
        and getattr(settings, "market_regime_filter_enabled", False)
        and not market_regime_bullish
    ):
        signal = "HOLD"
    signal = _apply_volume_volatility_filters(signal, df, settings)
    latest = df.iloc[-1]

    ai_score = None
    if getattr(settings, "use_ai_score", False):
        try:
            if ai_model_bundle is None:
                raise ValueError("AI score model was not loaded")
            ai_score = predict_ai_score_from_bundle(raw_df, ai_model_bundle)
        except Exception:
            ai_score = None

    return signal, latest, ai_score


def main() -> None:
    args = parse_args()
    execute_orders = args.execute
    settings = load_settings()
    ai_model_bundle = None
    if getattr(settings, "use_ai_score", False):
        try:
            ai_model_bundle = load_ai_score_model()
        except Exception:
            ai_model_bundle = None

    market_clock = get_market_clock()
    try:
        account = get_account_summary()
        open_symbols = get_open_symbols()
        positions = get_positions_summary()
    except ConnectionError as exc:
        if execute_orders:
            raise
        print(f"Alpaca unavailable, using offline dry-run defaults: {exc}")
        account = _offline_account_summary()
        open_symbols = set()
        positions = []
    tickers_to_load = list(dict.fromkeys([*settings.tickers, *open_symbols]))
    if getattr(settings, "market_regime_filter_enabled", False):
        tickers_to_load.append(settings.market_regime_ticker)
        tickers_to_load = list(dict.fromkeys(tickers_to_load))
    ticker_data = load_price_data_batch(tickers_to_load, period="1y")
    market_regime_bullish = True
    if getattr(settings, "market_regime_filter_enabled", False):
        market_regime_bullish = is_bullish_market_regime(
            ticker_data[settings.market_regime_ticker],
            ma_fast=settings.market_regime_ma_fast,
            ma_slow=settings.market_regime_ma_slow,
        )

    cash = account["cash"]
    positions_count = account["positions_count"]
    orders_submitted = 0
    submitted_notional_today = get_today_buy_notional()
    recent_buy_symbols = get_recent_buy_symbols(
        int(getattr(settings, "buy_cooldown_days", 0))
    )
    exit_summary_rows = []
    buy_summary_rows = []

    print("Account loaded from Alpaca paper.")
    print(f"cash={cash:.2f}, positions_count={positions_count}")
    print(f"execute_orders={execute_orders}")
    if getattr(settings, "market_regime_filter_enabled", False):
        print(
            f"market_regime_ticker={settings.market_regime_ticker}, "
            f"market_regime_bullish={market_regime_bullish}"
        )
    print(
        f"market_is_open={market_clock.is_open}, "
        f"market_time={market_clock.timestamp}"
    )
    if not market_clock.is_open:
        print(f"next_open={market_clock.next_open}")

    if execute_orders and not market_clock.is_open:
        print("EXECUTION_BLOCKED: market is closed. Dry-run checks will continue.")

    can_submit_orders = execute_orders and market_clock.is_open

    print("-" * 80)

    # 1) 기존 보유 포지션 청산 조건 먼저 확인
    if positions:
        print("Checking open positions for exit conditions...")
        for position in positions:
            ticker = position["symbol"]

            try:
                signal, latest, ai_score = get_signal_for_ticker(
                    ticker,
                    ticker_data[ticker],
                    settings,
                    ai_model_bundle=ai_model_bundle,
                    market_regime_bullish=market_regime_bullish,
                )
                unrealized_plpc = float(position["unrealized_plpc"])

                exit_decision = check_exit_allowed(
                    signal=signal,
                    unrealized_plpc=unrealized_plpc,
                )

                print(
                    f"{ticker}: position_qty={position['qty']}, "
                    f"unrealized_plpc={unrealized_plpc * 100:.2f}%, "
                    f"signal={signal}, "
                    f"exit={exit_decision.should_exit}, "
                    f"reason='{exit_decision.reason}'"
                )

                exit_summary_rows.append(
                    f"{ticker}: pnl={unrealized_plpc * 100:.2f}%, "
                    f"signal={signal}, exit={exit_decision.should_exit}, "
                    f"reason={exit_decision.reason}"
                )

                if not exit_decision.should_exit:
                    continue

                if not can_submit_orders:
                    label = "DRY_RUN_ONLY" if not execute_orders else "MARKET_CLOSED"
                    print(
                        f"  {label}: would CLOSE {ticker} "
                        f"reason='{exit_decision.reason}'"
                    )
                    continue

                order = close_position_by_symbol(ticker)

                log_order(
                    ticker=ticker,
                    notional=0.0,
                    order_id=str(order.id),
                    status=str(order.status),
                    side=str(order.side),
                    order_type=str(order.type),
                    reason=exit_decision.reason,
                )

                print(
                    f"  PAPER_CLOSE_SUBMITTED: {ticker}, "
                    f"order_id={order.id}, status={order.status}"
                )

                checked_order = wait_for_order_status(str(order.id))
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

                notify_order(
                    action="CLOSE",
                    ticker=ticker,
                    status=checked_order["status"],
                    order_id=checked_order["id"],
                    reason=exit_decision.reason,
                    filled_qty=checked_order["filled_qty"],
                    filled_avg_price=checked_order["filled_avg_price"],
                )

                if ticker in open_symbols:
                    open_symbols.remove(ticker)
                    positions_count -= 1

            except Exception as exc:
                print(f"{ticker}: EXIT_CHECK_ERROR - {exc}")
                exit_summary_rows.append(f"{ticker}: EXIT_CHECK_ERROR - {exc}")
                notify_error(f"{ticker} exit check error", exc)

        print("-" * 80)

    # 2) 신규 매수 후보 확인
    for ticker in settings.tickers:
        try:
            signal, latest, ai_score = get_signal_for_ticker(
                ticker,
                ticker_data[ticker],
                settings,
                ai_model_bundle=ai_model_bundle,
                market_regime_bullish=market_regime_bullish,
            )

            if ticker in open_symbols:
                risk_allowed = False
                risk_reason = "already holding position"
                target_amount = 0.0
            else:
                risk = check_buy_allowed(
                    signal=signal,
                    cash=cash,
                    current_positions_count=positions_count,
                )
                risk_allowed = risk.allowed
                risk_reason = risk.reason
                target_amount = risk.target_amount

            if (
                risk_allowed
                and getattr(settings, "use_ai_score", False)
                and (
                    ai_score is None
                    or ai_score < float(settings.ai_score_buy_threshold)
                )
            ):
                risk_allowed = False
                risk_reason = (
                    f"ai score filter blocked "
                    f"(score={ai_score}, threshold={settings.ai_score_buy_threshold})"
                )
                target_amount = 0.0

            order_amount = min(target_amount, settings.max_test_order_amount)

            if risk_allowed:
                safety = apply_buy_safety_limits(
                    ticker=ticker,
                    order_amount=order_amount,
                    submitted_notional_today=submitted_notional_today,
                    recent_buy_symbols=recent_buy_symbols,
                )
                risk_allowed = safety.allowed
                risk_reason = safety.reason if not safety.allowed else risk_reason
                order_amount = safety.target_amount

            log_signal(
                ticker=ticker,
                signal=signal,
                close=latest["close"],
                ma20=latest["ma20"],
                ma50=latest["ma50"],
                rsi=latest["rsi"],
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

            buy_summary_rows.append(
                f"{ticker}: signal={signal}, allowed={risk_allowed}, "
                f"reason={risk_reason}, order=${order_amount:.2f}, "
                f"ai_score={ai_score}"
            )

            if not risk_allowed:
                continue

            if orders_submitted >= settings.max_orders_per_run:
                print("  SKIP_ORDER: max orders per run reached")
                buy_summary_rows.append(
                    f"{ticker}: SKIP_ORDER max orders per run reached, "
                    f"ai_score={ai_score}"
                )
                continue

            if not can_submit_orders:
                label = "DRY_RUN_ONLY" if not execute_orders else "MARKET_CLOSED"
                print(
                    f"  {label}: would BUY {ticker} "
                    f"notional=${order_amount:.2f}"
                )
                buy_summary_rows.append(
                    f"{ticker}: {label} would BUY ${order_amount:.2f}, "
                    f"ai_score={ai_score}"
                )
                orders_submitted += 1
                submitted_notional_today += order_amount
                continue

            order = submit_market_buy_notional_order(
                ticker=ticker,
                notional=order_amount,
            )
            orders_submitted += 1
            submitted_notional_today += order_amount

            log_order(
                ticker=ticker,
                notional=order_amount,
                order_id=str(order.id),
                status=str(order.status),
                side=str(order.side),
                order_type=str(order.type),
                reason=risk_reason,
            )

            print(
                f"  PAPER_ORDER_SUBMITTED: BUY {ticker} "
                f"notional=${order_amount:.2f}, "
                f"order_id={order.id}, status={order.status}"
            )

            checked_order = wait_for_order_status(str(order.id))
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

            notify_order(
                action="BUY",
                ticker=ticker,
                status=checked_order["status"],
                order_id=checked_order["id"],
                reason=risk_reason,
                filled_qty=checked_order["filled_qty"],
                filled_avg_price=checked_order["filled_avg_price"],
            )

            buy_summary_rows.append(
                f"{ticker}: BUY_SUBMITTED status={checked_order['status']}, "
                f"filled_qty={checked_order['filled_qty']}, "
                f"filled_avg_price={checked_order['filled_avg_price']}, "
                f"ai_score={ai_score}"
            )

            positions_count += 1
            cash -= order_amount

        except Exception as exc:
            print(f"{ticker}: ERROR - {exc}")
            buy_summary_rows.append(f"{ticker}: ERROR - {exc}")
            notify_error(f"{ticker} bot error", exc)


    exit_summary = compact_exit_summary(exit_summary_rows, limit=20)
    buy_summary = compact_buy_summary(buy_summary_rows, limit=10)

    try:
        notify_run_summary(
            market_is_open=market_clock.is_open,
            execute_orders=execute_orders,
            cash=account["cash"],
            portfolio_value=account["portfolio_value"],
            positions_count=account["positions_count"],
            exit_summary=exit_summary,
            buy_summary=buy_summary,
        )
    except Exception as exc:
        print(f"TELEGRAM_SUMMARY_ERROR - {exc}")



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



if __name__ == "__main__":
    main()
