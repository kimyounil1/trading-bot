import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Union

# 경로 설정
CONFIG_PATH = Path("config/strategy_config.json")


class AllocationType(Enum):
    EQUAL_WEIGHT = "equal_weight"
    FIXED_WEIGHT = "fixed_weight"
    RISK_PARITY = "risk_parity"


@dataclass
class StrategyProfile:
    """개별 전략의 기술적 지표 및 필터 설정"""

    name: str
    tickers: List[str]

    # 기술적 지표 (MA, RSI 등)
    ma_fast: int
    ma_slow: int
    rsi_buy_limit: float

    # 필터 설정
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
    volume_filter_enabled: bool = False
    volume_lookback_days: int = 20
    min_volume_ratio: float = 1.0
    volatility_filter_enabled: bool = False
    volatility_lookback_days: int = 20
    max_volatility: float = 0.04

    # 랭킹 가중치
    rank_trend_weight: float = 1.0
    rank_ai_weight: float = 0.0
    rank_momentum_weight: float = 0.0
    rank_volatility_weight: float = 0.0


@dataclass
class StrategySettings(StrategyProfile):
    """Legacy single-strategy settings used by backtests and tests."""

    name: str = "default"
    tickers: List[str] = field(default_factory=lambda: ["NVDA", "MSFT", "GOOGL", "AMZN", "AMD"])
    ma_fast: int = 10
    ma_slow: int = 50
    rsi_buy_limit: float = 65.0
    use_ai_score: bool = False
    ai_score_buy_threshold: float = 0.55
    market_regime_filter_enabled: bool = False
    market_regime_ticker: str = "SPY"
    market_regime_ma_fast: int = 50
    market_regime_ma_slow: int = 200

    max_position_pct: float = 0.4
    max_total_positions: int = 2
    max_sector_positions: int = 2
    stop_loss_pct: float = 0.05
    take_profit_pct: float = 0.1
    trailing_stop_pct: Optional[float] = None
    max_test_order_amount: float = 10.0
    max_orders_per_run: int = 1
    max_daily_order_amount: float = 1000.0
    buy_cooldown_days: int = 1
    allocation_method: str = "equal_weight"
    ai_exit_enabled: bool = False
    ai_exit_threshold: float = 0.30
    ai_exit_dynamic_enabled: bool = False
    ai_exit_vix_low: float = 15.0
    ai_exit_vix_high: float = 25.0
    ai_exit_threshold_bull: float = 0.22
    ai_exit_threshold_bear: float = 0.50
    news_sentiment_enabled: bool = False
    news_sentiment_threshold: float = -0.30


DEFAULT_SETTINGS = StrategySettings()


def validate_settings(settings: StrategySettings) -> StrategySettings:
    """Normalize and validate legacy single-strategy settings."""

    settings.tickers = [str(ticker).strip().upper() for ticker in settings.tickers]
    settings.market_regime_ticker = str(settings.market_regime_ticker).strip().upper()
    settings.relative_strength_benchmark_ticker = str(settings.relative_strength_benchmark_ticker).strip().upper()
    if not settings.tickers or any(not ticker for ticker in settings.tickers):
        raise ValueError("tickers must not be empty")
    if settings.ma_fast <= 0 or settings.ma_slow <= 0:
        raise ValueError("ma_fast and ma_slow must be positive")
    if settings.ma_fast >= settings.ma_slow:
        raise ValueError("ma_fast must be smaller than ma_slow")
    if not 0 < settings.rsi_buy_limit <= 101:
        raise ValueError("rsi_buy_limit must be between 0 and 101")
    if not 0 < settings.max_position_pct <= 1:
        raise ValueError("max_position_pct must be between 0 and 1")
    if settings.max_total_positions <= 0:
        raise ValueError("max_total_positions must be positive")
    if settings.max_sector_positions <= 0:
        raise ValueError("max_sector_positions must be positive")
    if settings.max_orders_per_run <= 0:
        raise ValueError("max_orders_per_run must be positive")
    if settings.max_daily_order_amount <= 0:
        raise ValueError("max_daily_order_amount must be positive")
    if settings.max_test_order_amount <= 0:
        raise ValueError("max_test_order_amount must be positive")
    if settings.buy_cooldown_days < 0:
        raise ValueError("buy_cooldown_days must be non-negative")
    return settings


def load_settings(path: str | Path = CONFIG_PATH) -> StrategySettings:
    """Load the active legacy single-strategy config."""

    settings_path = Path(path).expanduser().resolve()
    merged = DEFAULT_SETTINGS.__dict__.copy()
    if settings_path.exists():
        merged.update(json.loads(settings_path.read_text(encoding="utf-8")))
    return validate_settings(StrategySettings(**merged))


def save_settings(settings: StrategySettings, path: str | Path = CONFIG_PATH) -> None:
    """Save the active legacy single-strategy config."""

    settings = validate_settings(settings)
    settings_path = Path(path).expanduser().resolve()
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")


@dataclass
class AssetAllocationConfig:
    """자산 배분 전략 설정"""

    allocation_type: AllocationType
    # Fixed weight 사용 시 각 전략별 비중 (Strategy Name -> Weight)
    weights: Dict[str, float] = field(default_factory=dict)


@dataclass
class PortfolioConfig:
    """전체 포트폴리오 관리 설정 (최상위)"""

    # 1. 전략 프로필 리스트
    strategies: List[StrategyProfile]

    # 2. 자산 배분 설정
    allocation: AssetAllocationConfig

    # 3. 공통 리스크 관리 (전체 포트폴리오 수준)
    max_total_positions: int
    max_daily_order_amount: float
    stop_loss_pct: float
    take_profit_pct: float

    # 기본값이 있는 필드들은 뒤로 배치
    trailing_stop_pct: Optional[float] = None
    buy_cooldown_days: int = 1
    max_test_order_amount: float = 1000.0
    max_orders_per_run: int = 10


# --- 유틸리티 함수 ---

def save_portfolio_config(config: PortfolioConfig) -> None:
    """설정을 JSON 파일로 저장"""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

    def _as_dict(obj):
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, list):
            return [_as_dict(i) for i in obj]
        if isinstance(obj, dict):
            return {k: _as_dict(v) for k, v in obj.items()}
        if hasattr(obj, "__dict__"):
            return {k: _as_dict(v) for k, v in asdict(obj).items()}
        return obj

    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(_as_dict(config), f, indent=2)


def load_portfolio_config() -> PortfolioConfig:
    """설정을 JSON 파일에서 로드"""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Configuration file not found at {CONFIG_PATH}")

    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)

    # 재귀적으로 dataclass를 복원하는 로직 (간소화된 버전)
    def _recursive_decode(obj, cls):
        if cls is StrategyProfile:
            return StrategyProfile(**obj)
        if cls is AssetAllocationConfig:
            # Enum 변환 필요
            obj["allocation_type"] = AllocationType(obj["allocation_type"])
            return AssetAllocationConfig(**obj)
        if cls is PortfolioConfig:
            # 중첩된 객체들 복원
            obj["allocation"] = _recursive_decode(obj["allocation"], AssetAllocationConfig)
            obj["strategies"] = [_recursive_decode(s, StrategyProfile) for s in obj["strategies"]]
            return PortfolioConfig(**obj)
        return obj

    return _recursive_decode(data, PortfolioConfig)


def print_portfolio_config(config: PortfolioConfig) -> None:
    """설정 내용을 출력"""
    print("Portfolio Configuration")
    print("=" * 40)
    print(f"Total Strategies: {len(config.strategies)}")
    for s in config.strategies:
        print(f"  - Strategy: {s.name} ({len(s.tickers)} tickers)")
    print(f"Allocation Type: {config.allocation.allocation_type.value}")
    if config.allocation.allocation_type == AllocationType.FIXED_WEIGHT:
        print(f"  Weights: {config.allocation.weights}")
    print(f"Max Positions: {config.max_total_positions}")
    print(f"Stop Loss: {config.stop_loss_pct:.2%}")
    print(f"Take Profit: {config.take_profit_pct:.2%}")
    print("=" * 40)
