import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import List, Dict, Optional, Union
from enum import Enum

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
    relative_strength_filter_enabled: bool
    relative_strength_benchmark_ticker: str
    relative_strength_lookback_days: int
    relative_strength_min_excess_return: float
    volume_filter_enabled: bool
    volume_lookback_days: int
    min_volume_ratio: float
    volatility_filter_enabled: bool
    volatility_lookback_days: int
    max_volatility: float
    
    # 랭킹 가중치
    rank_trend_weight: float
    rank_ai_weight: float
    rank_momentum_weight: float
    rank_volatility_weight: float

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
            obj['allocation_type'] = AllocationType(obj['allocation_type'])
            return AssetAllocationConfig(**obj)
        if cls is PortfolioConfig:
            # 중첩된 객체들 복원
            obj['allocation'] = _recursive_decode(obj['allocation'], AssetAllocationConfig)
            obj['strategies'] = [_recursive_decode(s, StrategyProfile) for s in obj['strategies']]
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

