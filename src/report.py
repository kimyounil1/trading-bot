from pathlib import Path
import json

import pandas as pd

from src.config import LOG_PATH, ORDER_LOG_PATH
from src.brokers import broker_account_snapshot
from src.settings import load_settings
from src.market_clock import get_market_clock


BASELINE_SNAPSHOT_PATH = Path("logs/baselines/current_strategy/baseline_snapshot.json")


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
    print_section("Market")
    try:
        clock = get_market_clock()
    except Exception as exc:
        print(f"Unavailable: {exc}")
        return

    print(f"is_open={clock.is_open}")
    print(f"timestamp={clock.timestamp}")
    print(f"next_open={clock.next_open}")
    print(f"next_close={clock.next_close}")


def print_account() -> None:
    print_section("Account")
    try:
        settings = load_settings()
        account, _ = broker_account_snapshot(settings.broker_provider)
    except Exception as exc:
        print(f"Unavailable: {exc}")
        return

    print(f"status={account['status']}")
    print(f"currency={account['currency']}")
    print(f"cash={money(account['cash'])}")
    print(f"portfolio_value={money(account['portfolio_value'])}")
    print(f"buying_power={money(account['buying_power'])}")
    print(f"positions_count={account['positions_count']}")


def print_positions() -> None:
    print_section("Positions")
    try:
        _, positions = broker_account_snapshot(settings.broker_provider)
    except Exception as exc:
        print(f"Unavailable: {exc}")
        return

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
    print(f"MAX_DAILY_ORDER_AMOUNT={money(settings.max_daily_order_amount)}")
    print(f"BUY_COOLDOWN_DAYS={settings.buy_cooldown_days}")
    print(f"USE_AI_SCORE={getattr(settings, 'use_ai_score', False)}")
    print(f"AI_SCORE_BUY_THRESHOLD={getattr(settings, 'ai_score_buy_threshold', None)}")
    print(f"RELATIVE_STRENGTH_FILTER_ENABLED={getattr(settings, 'relative_strength_filter_enabled', False)}")
    print(f"VOLUME_FILTER_ENABLED={getattr(settings, 'volume_filter_enabled', False)}")
    print(f"VOLUME_LOOKBACK_DAYS={getattr(settings, 'volume_lookback_days', None)}")
    print(f"MIN_VOLUME_RATIO={getattr(settings, 'min_volume_ratio', None)}")
    print(f"VOLATILITY_FILTER_ENABLED={getattr(settings, 'volatility_filter_enabled', False)}")
    print(f"VOLATILITY_LOOKBACK_DAYS={getattr(settings, 'volatility_lookback_days', None)}")
    print(f"MAX_VOLATILITY={getattr(settings, 'max_volatility', None)}")
    print(f"RANK_TREND_WEIGHT={getattr(settings, 'rank_trend_weight', None)}")
    print(f"RANK_AI_WEIGHT={getattr(settings, 'rank_ai_weight', None)}")
    print(f"RANK_MOMENTUM_WEIGHT={getattr(settings, 'rank_momentum_weight', None)}")
    print(f"RANK_VOLATILITY_WEIGHT={getattr(settings, 'rank_volatility_weight', None)}")


def print_current_baseline() -> None:
    print_section("Current Baseline")

    if not BASELINE_SNAPSHOT_PATH.exists():
        print(f"No file found: {BASELINE_SNAPSHOT_PATH}")
        return

    try:
        payload = json.loads(BASELINE_SNAPSHOT_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"Could not read {BASELINE_SNAPSHOT_PATH}: {exc}")
        return

    settings = payload.get("settings", {})
    result = payload.get("result", {})

    print(f"snapshot_path={BASELINE_SNAPSHOT_PATH}")
    print(f"generated_at_utc={payload.get('generated_at_utc')}")
    print(f"period={payload.get('period')}")
    print(f"tickers={len(payload.get('tickers', []))}")
    print(f"total_return={pct(float(result.get('total_return', 0.0)))}")
    print(f"max_drawdown={pct(float(result.get('max_drawdown', 0.0)))}")
    print(f"trades={result.get('trades')}")
    print(f"win_rate={pct(float(result.get('win_rate', 0.0)))}")
    print(f"final_equity={money(float(result.get('final_equity', 0.0)))}")
    print(f"volume_filter_enabled={settings.get('volume_filter_enabled')}")
    print(f"volume_lookback_days={settings.get('volume_lookback_days')}")
    print(f"min_volume_ratio={settings.get('min_volume_ratio')}")
    print(f"rank_trend_weight={settings.get('rank_trend_weight')}")
    print(f"rank_ai_weight={settings.get('rank_ai_weight')}")
    print(f"rank_momentum_weight={settings.get('rank_momentum_weight')}")
    print(f"rank_volatility_weight={settings.get('rank_volatility_weight')}")


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
    print_current_baseline()
    print_market()
    print_account()
    print_positions()
    print_strategy_config()
    print_recent_csv(LOG_PATH, "Recent Signals", limit=10)
    print_recent_csv(ORDER_LOG_PATH, "Recent Orders", limit=10)


if __name__ == "__main__":
    main()
