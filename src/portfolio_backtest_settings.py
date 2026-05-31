"""Map StrategySettings to run_portfolio_backtest keyword arguments."""

from __future__ import annotations

from typing import Any

from src.settings import StrategySettings


def portfolio_backtest_kwargs(
    settings: StrategySettings,
    *,
    ticker_data: dict,
    benchmark_df=None,
    relative_strength_benchmark_df=None,
    vix_df=None,
    macro_df=None,
    ai_score_frames=None,
    allocation_method: str | None = None,
    evaluation_start_date=None,
    evaluation_end_date=None,
    initial_cash: float = 10000.0,
    transaction_cost_pct: float = 0.001,
) -> dict[str, Any]:
    """Single source of truth for portfolio backtest parameters from config."""
    return {
        "ticker_data": ticker_data,
        "benchmark_df": benchmark_df,
        "relative_strength_benchmark_df": relative_strength_benchmark_df,
        "initial_cash": initial_cash,
        "max_positions": settings.max_total_positions,
        "target_position_pct": settings.max_position_pct,
        "transaction_cost_pct": transaction_cost_pct,
        "ma_fast": settings.ma_fast,
        "ma_slow": settings.ma_slow,
        "rsi_buy_limit": settings.rsi_buy_limit,
        "use_ai_score": settings.use_ai_score,
        "ai_score_buy_threshold": settings.ai_score_buy_threshold,
        "market_regime_filter_enabled": settings.market_regime_filter_enabled,
        "market_regime_ma_fast": settings.market_regime_ma_fast,
        "market_regime_ma_slow": settings.market_regime_ma_slow,
        "relative_strength_filter_enabled": settings.relative_strength_filter_enabled,
        "relative_strength_lookback_days": settings.relative_strength_lookback_days,
        "relative_strength_min_excess_return": settings.relative_strength_min_excess_return,
        "volume_filter_enabled": settings.volume_filter_enabled,
        "volume_lookback_days": settings.volume_lookback_days,
        "min_volume_ratio": settings.min_volume_ratio,
        "volatility_filter_enabled": settings.volatility_filter_enabled,
        "volatility_lookback_days": settings.volatility_lookback_days,
        "max_volatility": settings.max_volatility,
        "rank_trend_weight": settings.rank_trend_weight,
        "rank_ai_weight": settings.rank_ai_weight,
        "rank_momentum_weight": settings.rank_momentum_weight,
        "rank_volatility_weight": settings.rank_volatility_weight,
        "stop_loss_pct": settings.stop_loss_pct,
        "take_profit_pct": settings.take_profit_pct,
        "trailing_stop_pct": settings.trailing_stop_pct,
        "allocation_method": allocation_method or getattr(settings, "allocation_method", "equal_weight"),
        "ai_exit_enabled": getattr(settings, "ai_exit_enabled", False),
        "ai_exit_threshold": settings.ai_exit_threshold,
        "ai_exit_dynamic_enabled": getattr(settings, "ai_exit_dynamic_enabled", False),
        "ai_exit_vix_low": getattr(settings, "ai_exit_vix_low", 15.0),
        "ai_exit_vix_high": getattr(settings, "ai_exit_vix_high", 25.0),
        "ai_exit_threshold_bull": getattr(settings, "ai_exit_threshold_bull", 0.55),
        "ai_exit_threshold_bear": getattr(settings, "ai_exit_threshold_bear", 0.28),
        "vix_df": vix_df,
        "macro_df": macro_df,
        "ai_score_frames": ai_score_frames,
        "evaluation_start_date": evaluation_start_date,
        "evaluation_end_date": evaluation_end_date,
    }
