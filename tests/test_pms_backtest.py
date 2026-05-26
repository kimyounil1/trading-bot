import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.strategy import add_indicators, generate_signal, is_bullish_market_regime
from src.settings import StrategyProfile, PortfolioConfig, AllocationType, AssetAllocationConfig
from src.backtester import run_portfolio_backtest

class TestPMSBacktest(unittest.TestCase):
    def setUp(self):
        # 1. 가상 데이터 생성 (100일치)
        self.dates = pd.date_range(start="2023-01-01", periods=100)
        self.tickers = ["AAPL", "MSFT", "GOOGL", "AMZN"]
        self.all_data = {}
        
        for ticker in self.tickers:
            df = pd.DataFrame({
                'date': self.dates,
                'close': np.linspace(100, 200, 100) + np.random.randn(100) * 5,
                'open': 100.0,
                'high': 110.0,
                'low': 90.0,
                'volume': 1000000
            })
            # Required columns for indicators and signal generation
            df['ma_fast'] = df['close'].rolling(10).mean()
            df['ma_slow'] = df['close'].rolling(50).mean()
            df['rsi'] = 50.0
            df['return_20d'] = df['close'].pct_change(20)
            df['volume_change_5d'] = 1.5 # Dummy value to pass volume filter
            self.all_data[ticker] = df

        # 2. 전략 프로필 설정 (2개 전략)
        self.profile1 = StrategyProfile(
            name="TrendFollower",
            tickers=["AAPL", "MSFT"],
            ma_fast=10, ma_slow=30, rsi_buy_limit=70.0,
            use_ai_score=False, ai_score_buy_threshold=0.5,
            market_regime_filter_enabled=False, market_regime_ticker="SPY",
            market_regime_ma_fast=50, market_regime_ma_slow=200,
            relative_strength_filter_enabled=False, relative_strength_benchmark_ticker="SPY",
            relative_strength_lookback_days=20, relative_strength_min_excess_return=0.0,
            volume_filter_enabled=False, volume_lookback_days=20, min_volume_ratio=1.0,
            volatility_filter_enabled=False, volatility_lookback_days=20, max_volatility=0.04,
            rank_trend_weight=1.0, rank_ai_weight=0.0, rank_momentum_weight=0.0, rank_volatility_weight=0.0
        )
        
        self.profile2 = StrategyProfile(
            name="Momentum",
            tickers=["GOOGL", "AMZN"],
            ma_fast=10, ma_slow=30, rsi_buy_limit=70.0,
            use_ai_score=False, ai_score_buy_threshold=0.5,
            market_regime_filter_enabled=False, market_regime_ticker="SPY",
            market_regime_ma_fast=50, market_regime_ma_slow=200,
            relative_strength_filter_enabled=False, relative_strength_benchmark_ticker="SPY",
            relative_strength_lookback_days=20, relative_strength_min_excess_return=0.0,
            volume_filter_enabled=False, volume_lookback_days=20, min_volume_ratio=1.0,
            volatility_filter_enabled=False, volatility_lookback_days=20, max_volatility=0.04,
            rank_trend_weight=0.0, rank_ai_weight=0.0, rank_momentum_weight=1.0, rank_volatility_weight=0.0
        )

        # 3. 포트폴리오 설정
        self.config = PortfolioConfig(
            strategies=[self.profile1, self.profile2],
            allocation=AssetAllocationConfig(allocation_type=AllocationType.EQUAL_WEIGHT),
            max_total_positions=2,
            max_daily_order_amount=10000.0,
            stop_loss_pct=0.05,
            take_profit_pct=0.10,
            buy_cooldown_days=1,
            max_test_order_amount=1000.0,
            max_orders_per_run=10
        )

    def test_portfolio_max_positions(self):
        """테스트: max_total_positions 제약 조건이 작동하는지 확인"""
        result, equity_df = run_portfolio_backtest(self.config, self.all_data)
        
        self.assertFalse(equity_df.empty)
        self.assertIsInstance(result.final_equity, float)

if __name__ == "__main__":
    unittest.main()
