import json
from dataclasses import asdict, dataclass, field, fields
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# 경로 설정
CONFIG_PATH = Path("config/strategy_config.json")
PROFILES_PATH = Path("config/strategy_profiles.json")


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
    max_portfolio_drawdown_pct: float = 0.15
    max_holding_days: int = 30
    correlation_guard_enabled: bool = False
    max_correlation_threshold: float = 0.85
    max_portfolio_avg_correlation_threshold: float = 0.70
    correlation_lookback_days: int = 60
    earnings_filter_enabled: bool = False
    earnings_lookback_days: int = 3
    earnings_lookforward_days: int = 1
    take_profit_partial_pct: float = 0.0
    partial_exit_ratio: float = 0.5
    leverage_factor: float = 1.0
    max_gross_exposure_pct: float = 1.0
    min_cash_buffer_pct: float = 0.05
    max_single_name_loss_pct: float = 0.02
    crowding_guard_enabled: bool = False
    crowding_lookback_days: int = 60
    crowding_max_positions: int = 2
    crowding_momentum_threshold: float = 0.15
    crowding_trend_gap_threshold: float = 0.05
    dynamic_universe_enabled: bool = False
    dynamic_count: int = 50
    allow_leveraged_etfs: bool = False
    max_leveraged_etf_positions: int = 1
    max_effective_leverage_exposure_pct: float = 1.25
    block_leveraged_etfs_vix_above: float = 28.0
    trailing_stop_pct: float = 0.05
    adaptive_trailing_stop_enabled: bool = False
    atr_multiplier: float = 3.0
    rebalance_threshold_pct: float = 0.20
    sector_rotation_enabled: bool = False
    macro_event_risk_enabled: bool = False
    macro_event_lookahead_days: int = 2
    macro_event_lookback_days: int = 1
    llm_degraded_mode: str = "PASS"  # "PASS" or "FAIL"
    llm_cache_enabled: bool = True


_STRATEGY_SETTINGS_FIELD_NAMES = {item.name for item in fields(StrategySettings)}
_PROFILE_OVERRIDE_FIELD_NAMES = _STRATEGY_SETTINGS_FIELD_NAMES - {"name", "tickers"}
_PROFILES_CONFIG_FIELD_NAMES = {"profiles", "regime_mapping", "manual_override"}


DEFAULT_SETTINGS = StrategySettings()


def _read_json_object(path: Path) -> Dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a top-level JSON object")

    return payload


def _validate_strategy_settings_payload(payload: Dict[str, Any], path: Path) -> Dict[str, Any]:
    unknown_keys = sorted(set(payload) - _STRATEGY_SETTINGS_FIELD_NAMES)
    if unknown_keys:
        raise ValueError(f"Unknown keys in {path}: {unknown_keys}")

    tickers = payload.get("tickers")
    if tickers is not None and (
        not isinstance(tickers, list) or any(not isinstance(ticker, str) for ticker in tickers)
    ):
        raise ValueError(f"{path}: 'tickers' must be a list of strings")

    market_regime_ticker = payload.get("market_regime_ticker")
    if market_regime_ticker is not None and not isinstance(market_regime_ticker, str):
        raise ValueError(f"{path}: 'market_regime_ticker' must be a string")

    return payload


def _validate_profiles_payload(payload: Dict[str, Any], path: Path) -> Dict[str, Any]:
    unknown_keys = sorted(set(payload) - _PROFILES_CONFIG_FIELD_NAMES)
    if unknown_keys:
        raise ValueError(f"Unknown keys in {path}: {unknown_keys}")

    profiles = payload.get("profiles")
    if not isinstance(profiles, dict) or not profiles:
        raise ValueError(f"{path}: 'profiles' must be a non-empty object")

    for profile_name, overrides in profiles.items():
        if not isinstance(profile_name, str) or not profile_name.strip():
            raise ValueError(f"{path}: profile names must be non-empty strings")
        if not isinstance(overrides, dict):
            raise ValueError(f"{path}: profile '{profile_name}' must be an object")
        override_unknown = sorted(set(overrides) - _PROFILE_OVERRIDE_FIELD_NAMES)
        if override_unknown:
            raise ValueError(
                f"{path}: profile '{profile_name}' has unknown keys: {override_unknown}"
            )

    regime_mapping = payload.get("regime_mapping")
    if not isinstance(regime_mapping, dict) or not regime_mapping:
        raise ValueError(f"{path}: 'regime_mapping' must be a non-empty object")
    for regime, profile_name in regime_mapping.items():
        if not isinstance(regime, str) or not regime.strip():
            raise ValueError(f"{path}: regime keys must be non-empty strings")
        if not isinstance(profile_name, str) or profile_name not in profiles:
            raise ValueError(
                f"{path}: regime '{regime}' must map to an existing profile name"
            )

    manual_override = payload.get("manual_override")
    if manual_override is not None and (
        not isinstance(manual_override, str) or manual_override not in profiles
    ):
        raise ValueError(
            f"{path}: 'manual_override' must be null or an existing profile name"
        )

    return payload


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
    if not 0 <= settings.stop_loss_pct < 1:
        raise ValueError("stop_loss_pct must be between 0 and 1")
    if settings.take_profit_pct < 0:
        raise ValueError("take_profit_pct must be non-negative")
    if not 0 <= settings.trailing_stop_pct < 1:
        raise ValueError("trailing_stop_pct must be between 0 and 1")
    if settings.atr_multiplier <= 0:
        raise ValueError("atr_multiplier must be positive")
    if settings.max_orders_per_run <= 0:
        raise ValueError("max_orders_per_run must be positive")
    if settings.max_daily_order_amount <= 0:
        raise ValueError("max_daily_order_amount must be positive")
    if settings.max_test_order_amount <= 0:
        raise ValueError("max_test_order_amount must be positive")
    if settings.buy_cooldown_days < 0:
        raise ValueError("buy_cooldown_days must be non-negative")
    if settings.max_holding_days <= 0:
        raise ValueError("max_holding_days must be positive")
    if not 0 <= settings.max_portfolio_drawdown_pct < 1:
        raise ValueError("max_portfolio_drawdown_pct must be between 0 and 1")
    if not 0 < settings.max_correlation_threshold <= 1:
        raise ValueError("max_correlation_threshold must be between 0 and 1")
    if not 0 < settings.max_portfolio_avg_correlation_threshold <= 1:
        raise ValueError("max_portfolio_avg_correlation_threshold must be between 0 and 1")
    if settings.correlation_lookback_days <= 0:
        raise ValueError("correlation_lookback_days must be positive")
    if settings.earnings_lookback_days < 0 or settings.earnings_lookforward_days < 0:
        raise ValueError("earnings window days must be non-negative")
    if settings.take_profit_partial_pct < 0:
        raise ValueError("take_profit_partial_pct must be non-negative")
    if not 0 < settings.partial_exit_ratio <= 1:
        raise ValueError("partial_exit_ratio must be between 0 and 1")
    if settings.leverage_factor <= 0:
        raise ValueError("leverage_factor must be positive")
    if not 0 < settings.max_gross_exposure_pct <= max(1.0, settings.leverage_factor):
        raise ValueError("max_gross_exposure_pct must be positive and no greater than leverage_factor")
    if not 0 <= settings.min_cash_buffer_pct < 1:
        raise ValueError("min_cash_buffer_pct must be between 0 and 1")
    if not 0 < settings.max_single_name_loss_pct < 1:
        raise ValueError("max_single_name_loss_pct must be between 0 and 1")
    if settings.crowding_lookback_days <= 0:
        raise ValueError("crowding_lookback_days must be positive")
    if settings.crowding_max_positions <= 0:
        raise ValueError("crowding_max_positions must be positive")
    if settings.crowding_momentum_threshold < 0:
        raise ValueError("crowding_momentum_threshold must be non-negative")
    if settings.crowding_trend_gap_threshold < 0:
        raise ValueError("crowding_trend_gap_threshold must be non-negative")
    if settings.dynamic_count <= 0:
        raise ValueError("dynamic_count must be positive")
    if settings.max_leveraged_etf_positions <= 0:
        raise ValueError("max_leveraged_etf_positions must be positive")
    if settings.max_effective_leverage_exposure_pct <= 0:
        raise ValueError("max_effective_leverage_exposure_pct must be positive")
    if settings.block_leveraged_etfs_vix_above < 0:
        raise ValueError("block_leveraged_etfs_vix_above must be non-negative")
    if settings.rebalance_threshold_pct < 0:
        raise ValueError("rebalance_threshold_pct must be non-negative")
    return settings


def load_settings(path: Union[str, Path] = CONFIG_PATH) -> StrategySettings:
    """Load the active legacy single-strategy config."""

    from src.universe_loader import resolve_scan_tickers

    settings_path = Path(path).expanduser().resolve()
    merged = asdict(DEFAULT_SETTINGS)
    if settings_path.exists():
        payload = _validate_strategy_settings_payload(_read_json_object(settings_path), settings_path)
        base_tickers = payload.get("tickers", merged.get("tickers"))
        payload["tickers"] = resolve_scan_tickers(list(base_tickers))
        merged.update(payload)
    else:
        merged["tickers"] = resolve_scan_tickers(list(merged["tickers"]))
    return validate_settings(StrategySettings(**merged))


def save_settings(settings: StrategySettings, path: Union[str, Path] = CONFIG_PATH) -> None:
    """Save the active legacy single-strategy config."""

    settings = validate_settings(settings)
    settings_path = Path(path).expanduser().resolve()
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")


def apply_dynamic_profile(
    settings: StrategySettings, 
    current_regime: str,
    profiles_path: Union[str, Path] = PROFILES_PATH
) -> Tuple[StrategySettings, str]:
    """시장 레짐 또는 사용자 설정에 따라 전략 프로필을 동적으로 적용한다."""
    path = Path(profiles_path).expanduser().resolve()
    if not path.exists():
        return settings, "DEFAULT (no profiles file)"

    try:
        data = _validate_profiles_payload(_read_json_object(path), path)
        profiles = data.get("profiles", {})
        mapping = data.get("regime_mapping", {})
        override = data.get("manual_override")

        # 1. 수동 오버라이드 우선, 없으면 레짐 매핑 사용
        profile_name = override if override else mapping.get(current_regime)
        if not profile_name or profile_name not in profiles:
            return settings, f"DEFAULT (profile '{profile_name}' not found)"

        # 2. 설정 덮어쓰기
        profile_overrides = profiles[profile_name]
        settings_dict = asdict(settings)
        settings_dict.update(profile_overrides)
        
        # 이름 기록
        settings_dict["name"] = profile_name

        return validate_settings(StrategySettings(**settings_dict)), profile_name

    except Exception as e:
        print(f"Warning: Failed to apply dynamic profile: {e}")
        return settings, f"DEFAULT (error: {e})"


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
