import argparse

from src.settings import load_settings
from src.data_loader import load_price_data
from src.strategy import add_indicators, generate_signal
from src.logger import log_signal, log_order, log_order_status
from src.risk_manager import check_buy_allowed, check_exit_allowed
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
from src.ml_model import predict_ai_score


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


def get_signal_for_ticker(ticker: str, settings) -> tuple[str, object, float | None]:
    raw_df = load_price_data(ticker)
    df = add_indicators(
        raw_df,
        ma_fast=settings.ma_fast,
        ma_slow=settings.ma_slow,
    )
    signal = generate_signal(df, rsi_buy_limit=settings.rsi_buy_limit)
    latest = df.iloc[-1]

    ai_score = None
    if getattr(settings, "use_ai_score", False):
        try:
            ai_score = predict_ai_score(raw_df)
        except Exception:
            ai_score = None

    return signal, latest, ai_score


def main() -> None:
    args = parse_args()
    execute_orders = args.execute
    settings = load_settings()

    market_clock = get_market_clock()
    account = get_account_summary()
    open_symbols = get_open_symbols()
    positions = get_positions_summary()

    cash = account["cash"]
    positions_count = account["positions_count"]
    orders_submitted = 0
    exit_summary_rows = []
    buy_summary_rows = []

    print("Account loaded from Alpaca paper.")
    print(f"cash={cash:.2f}, positions_count={positions_count}")
    print(f"execute_orders={execute_orders}")
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
                signal, latest, ai_score = get_signal_for_ticker(ticker, settings)
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
            signal, latest, ai_score = get_signal_for_ticker(ticker, settings)

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
                continue

            if not can_submit_orders:
                label = "DRY_RUN_ONLY" if not execute_orders else "MARKET_CLOSED"
                print(
                    f"  {label}: would BUY {ticker} "
                    f"notional=${order_amount:.2f}"
                )
                orders_submitted += 1
                continue

            order = submit_market_buy_notional_order(
                ticker=ticker,
                notional=order_amount,
            )
            orders_submitted += 1

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

            positions_count += 1
            cash -= order_amount

        except Exception as exc:
            print(f"{ticker}: ERROR - {exc}")
            buy_summary_rows.append(f"{ticker}: ERROR - {exc}")
            notify_error(f"{ticker} bot error", exc)


    exit_summary = "\n".join(exit_summary_rows) if exit_summary_rows else "No open positions."
    buy_summary = "\n".join(buy_summary_rows) if buy_summary_rows else "No buy checks."

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



if __name__ == "__main__":
    main()
