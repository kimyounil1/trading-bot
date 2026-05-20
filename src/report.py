from pathlib import Path

import pandas as pd

from src.config import LOG_PATH, ORDER_LOG_PATH
from src.settings import load_settings
from src.alpaca_client import get_account_summary, get_positions_summary
from src.market_clock import get_market_clock


def money(value: float) -> str:
    return f"${value:,.2f}"


def pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def print_section(title: str) -> None:
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def print_market() -> None:
    clock = get_market_clock()

    print_section("Market")
    print(f"is_open={clock.is_open}")
    print(f"timestamp={clock.timestamp}")
    print(f"next_open={clock.next_open}")
    print(f"next_close={clock.next_close}")


def print_account() -> None:
    account = get_account_summary()

    print_section("Account")
    print(f"status={account['status']}")
    print(f"currency={account['currency']}")
    print(f"cash={money(account['cash'])}")
    print(f"portfolio_value={money(account['portfolio_value'])}")
    print(f"buying_power={money(account['buying_power'])}")
    print(f"positions_count={account['positions_count']}")


def print_positions() -> None:
    positions = get_positions_summary()

    print_section("Positions")

    if not positions:
        print("No open positions.")
        return

    for position in positions:
        print(
            f"{position['symbol']}: "
            f"qty={position['qty']:.8f}, "
            f"market_value={money(position['market_value'])}, "
            f"cost_basis={money(position['cost_basis'])}, "
            f"unrealized_pl={money(position['unrealized_pl'])}, "
            f"unrealized_plpc={pct(position['unrealized_plpc'])}"
        )


def print_strategy_config() -> None:
    settings = load_settings()

    print_section("Strategy Config")
    print(f"TICKERS={settings.tickers}")
    print(f"MA_FAST={settings.ma_fast}")
    print(f"MA_SLOW={settings.ma_slow}")
    print(f"RSI_BUY_LIMIT={settings.rsi_buy_limit}")
    print(f"MAX_POSITION_PCT={pct(settings.max_position_pct)}")
    print(f"MAX_TOTAL_POSITIONS={settings.max_total_positions}")
    print(f"STOP_LOSS_PCT={pct(settings.stop_loss_pct)}")
    print(f"TAKE_PROFIT_PCT={pct(settings.take_profit_pct)}")
    print(f"MAX_TEST_ORDER_AMOUNT={money(settings.max_test_order_amount)}")
    print(f"MAX_ORDERS_PER_RUN={settings.max_orders_per_run}")
    print(f"USE_AI_SCORE={getattr(settings, 'use_ai_score', False)}")
    print(f"AI_SCORE_BUY_THRESHOLD={getattr(settings, 'ai_score_buy_threshold', None)}")


def print_recent_csv(path: str, title: str, limit: int = 10) -> None:
    print_section(title)

    file_path = Path(path)

    if not file_path.exists():
        print(f"No file found: {path}")
        return

    try:
        df = pd.read_csv(file_path)

        if df.empty:
            print("No rows.")
            return

        print(df.tail(limit).to_string(index=False))

    except Exception as exc:
        print(f"Could not read {path}: {exc}")


def main() -> None:
    print_market()
    print_account()
    print_positions()
    print_strategy_config()
    print_recent_csv(LOG_PATH, "Recent Signals", limit=10)
    print_recent_csv(ORDER_LOG_PATH, "Recent Orders", limit=10)


if __name__ == "__main__":
    main()
