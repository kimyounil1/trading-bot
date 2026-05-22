import json
from dataclasses import dataclass, asdict, fields
from pathlib import Path


CONFIG_PATH = Path("config/strategy_config.json")


@dataclass
class StrategySettings:
    tickers: list[str]

    ma_fast: int
    ma_slow: int
    rsi_buy_limit: float

    max_position_pct: float
    max_total_positions: int
    stop_loss_pct: float
    take_profit_pct: float

    max_test_order_amount: float
    max_orders_per_run: int
    max_daily_order_amount: float
    buy_cooldown_days: int

    use_ai_score: bool
    ai_score_buy_threshold: float

    market_regime_filter_enabled: bool
    market_regime_ticker: str
    market_regime_ma_fast: int
    market_regime_ma_slow: int

    relative_strength_filter_enabled: bool = False
    relative_strength_benchmark_ticker: str = "SPY"
    relative_strength_lookback_days: int = 20
    relative_strength_min_excess_return: float = 0.0


DEFAULT_SETTINGS = StrategySettings(
    tickers=["NVDA", "MSFT", "GOOGL", "AMZN", "AMD"],

    ma_fast=10,
    ma_slow=50,
    rsi_buy_limit=65,

    max_position_pct=0.40,
    max_total_positions=2,
    stop_loss_pct=0.05,
    take_profit_pct=0.10,

    max_test_order_amount=10.0,
    max_orders_per_run=1,
    max_daily_order_amount=1000.0,
    buy_cooldown_days=1,

    use_ai_score=False,
    ai_score_buy_threshold=0.55,

    market_regime_filter_enabled=False,
    market_regime_ticker="SPY",
    market_regime_ma_fast=50,
    market_regime_ma_slow=200,

    relative_strength_filter_enabled=False,
    relative_strength_benchmark_ticker="SPY",
    relative_strength_lookback_days=20,
    relative_strength_min_excess_return=0.0,
)


def validate_settings(settings: StrategySettings) -> StrategySettings:
    if not isinstance(settings.tickers, list) or not settings.tickers:
        raise ValueError("settings.tickers must be a non-empty list")

    normalized_tickers = []
    for ticker in settings.tickers:
        if not isinstance(ticker, str) or not ticker.strip():
            raise ValueError("settings.tickers must contain non-empty strings")
        normalized_tickers.append(ticker.strip().upper())

    if len(set(normalized_tickers)) != len(normalized_tickers):
        raise ValueError("settings.tickers must not contain duplicates")

    if settings.ma_fast <= 0 or settings.ma_slow <= 0:
        raise ValueError("ma_fast and ma_slow must be positive")
    if settings.ma_fast >= settings.ma_slow:
        raise ValueError("ma_fast must be smaller than ma_slow")
    if not 0 <= settings.rsi_buy_limit <= 100:
        raise ValueError("rsi_buy_limit must be between 0 and 100")

    if not 0 < settings.max_position_pct <= 1:
        raise ValueError("max_position_pct must be between 0 and 1")
    if settings.max_total_positions <= 0:
        raise ValueError("max_total_positions must be positive")
    if not 0 <= settings.stop_loss_pct < 1:
        raise ValueError("stop_loss_pct must be between 0 and 1")
    if settings.take_profit_pct < 0:
        raise ValueError("take_profit_pct must be non-negative")

    if settings.max_test_order_amount <= 0:
        raise ValueError("max_test_order_amount must be positive")
    if settings.max_orders_per_run <= 0:
        raise ValueError("max_orders_per_run must be positive")
    if settings.max_daily_order_amount < 0:
        raise ValueError("max_daily_order_amount must be non-negative")
    if settings.buy_cooldown_days < 0:
        raise ValueError("buy_cooldown_days must be non-negative")

    if not 0 <= settings.ai_score_buy_threshold <= 1:
        raise ValueError("ai_score_buy_threshold must be between 0 and 1")
    if not isinstance(settings.market_regime_ticker, str) or not settings.market_regime_ticker.strip():
        raise ValueError("market_regime_ticker must be a non-empty string")
    if settings.market_regime_ma_fast <= 0 or settings.market_regime_ma_slow <= 0:
        raise ValueError("market_regime_ma_fast and market_regime_ma_slow must be positive")
    if settings.market_regime_ma_fast >= settings.market_regime_ma_slow:
        raise ValueError("market_regime_ma_fast must be smaller than market_regime_ma_slow")
    if (
        not isinstance(settings.relative_strength_benchmark_ticker, str)
        or not settings.relative_strength_benchmark_ticker.strip()
    ):
        raise ValueError("relative_strength_benchmark_ticker must be a non-empty string")
    if settings.relative_strength_lookback_days <= 0:
        raise ValueError("relative_strength_lookback_days must be positive")

    settings.tickers = normalized_tickers
    settings.market_regime_ticker = settings.market_regime_ticker.strip().upper()
    settings.relative_strength_benchmark_ticker = (
        settings.relative_strength_benchmark_ticker.strip().upper()
    )
    return settings


def save_settings(settings: StrategySettings = DEFAULT_SETTINGS) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(asdict(settings), f, indent=2)


def load_settings() -> StrategySettings:
    if not CONFIG_PATH.exists():
        save_settings(DEFAULT_SETTINGS)

    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    merged = asdict(DEFAULT_SETTINGS)
    merged.update(raw)
    valid_keys = {field.name for field in fields(StrategySettings)}
    merged = {key: value for key, value in merged.items() if key in valid_keys}

    return validate_settings(StrategySettings(**merged))


def print_settings() -> None:
    settings = load_settings()

    print("Strategy settings")
    print("-" * 80)

    for key, value in asdict(settings).items():
        print(f"{key}={value}")
