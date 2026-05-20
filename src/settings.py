import json
from dataclasses import dataclass, asdict
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

    use_ai_score: bool
    ai_score_buy_threshold: float


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

    use_ai_score=False,
    ai_score_buy_threshold=0.55,
)


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

    return StrategySettings(**merged)


def print_settings() -> None:
    settings = load_settings()

    print("Strategy settings")
    print("-" * 80)

    for key, value in asdict(settings).items():
        print(f"{key}={value}")
