"""Map StrategySettings to run_portfolio_backtest keyword arguments."""

from __future__ import annotations

from typing import Any

from src.settings import StrategySettings
from src.rank_quality_risk import build_rank_quality_risk_overrides


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
    leveraged_product_data: dict | None = None,
    leveraged_product_routes: dict[str, str] | None = None,
    historical_universe_by_date: dict | None = None,
    base_universe: set[str] | list[str] | None = None,
    benchmark_universe: set[str] | list[str] | None = None,
    rank_ai_score_history: dict | None = None,
    rank_ai_primary_selector_enabled: bool | None = None,
    entry_parameter_overrides_by_date: dict | None = None,
    entry_risk_overrides_by_date: dict | None = None,
    exit_parameter_overrides_by_date: dict | None = None,
    tournament_alpha_enabled: bool = False,
    fractionable_symbols: set[str] | None = None,
    cash_reserve_pct: float | None = None,
    include_external_filters: bool = False,
) -> dict[str, Any]:
    """Single source of truth for portfolio backtest parameters from config."""
    if entry_risk_overrides_by_date is None:
        entry_risk_overrides_by_date = build_rank_quality_risk_overrides(
            ticker_data,
            settings,
        )
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
        "max_holding_days": getattr(settings, "max_holding_days", 0),
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
        "crowding_guard_enabled": settings.crowding_guard_enabled,
        "max_sector_positions": settings.max_sector_positions,
        "correlation_guard_enabled": settings.correlation_guard_enabled,
        "max_correlation_threshold": settings.max_correlation_threshold,
        "max_portfolio_avg_correlation_threshold": settings.max_portfolio_avg_correlation_threshold,
        "correlation_lookback_days": settings.correlation_lookback_days,
        "regime_adaptive_stop_enabled": settings.regime_adaptive_stop_enabled,
        "regime_stop_spy_df": benchmark_df,
        "llm_filter_enabled": bool(
            include_external_filters and not settings.llm_advisory_only
        ),
        "news_sentiment_filter_enabled": bool(
            include_external_filters and settings.news_sentiment_enabled
        ),
        "news_sentiment_threshold": settings.news_sentiment_threshold,
        "rank_ai_buy_gate_enabled": settings.rank_ai_buy_gate_enabled,
        "rank_ai_buy_top_k_enabled": getattr(settings, "rank_ai_buy_top_k_enabled", True),
        "max_orders_per_run": settings.max_orders_per_run,
        "operational_settings": settings,
        "allow_leveraged_etfs": settings.allow_leveraged_etfs,
        "leveraged_etf_allowlist": list(settings.leveraged_etf_allowlist),
        "max_leveraged_etf_positions": settings.max_leveraged_etf_positions,
        "max_effective_leverage_exposure_pct": settings.max_effective_leverage_exposure_pct,
        "block_leveraged_etfs_vix_above": settings.block_leveraged_etfs_vix_above,
        "prefer_leveraged_products": settings.prefer_leveraged_products,
        "leveraged_product_data": leveraged_product_data,
        "leveraged_product_routes": leveraged_product_routes,
        "historical_universe_by_date": historical_universe_by_date,
        "base_universe": base_universe,
        "benchmark_universe": benchmark_universe,
        "rank_ai_score_history": rank_ai_score_history,
        "rank_ai_primary_selector_enabled": (
            settings.rank_ai_primary_selector_enabled
            if rank_ai_primary_selector_enabled is None
            else rank_ai_primary_selector_enabled
        ),
        "entry_parameter_overrides_by_date": entry_parameter_overrides_by_date,
        "entry_risk_overrides_by_date": entry_risk_overrides_by_date,
        "exit_parameter_overrides_by_date": exit_parameter_overrides_by_date,
        "tournament_alpha_enabled": tournament_alpha_enabled,
        "tournament_alpha_rank_weight": settings.tournament_alpha_rank_weight,
        "take_profit_partial_pct": settings.take_profit_partial_pct,
        "partial_exit_ratio": settings.partial_exit_ratio,
        "minimum_order_notional": max(10.0, settings.dust_position_min_usd),
        "fractionable_symbols": fractionable_symbols,
        "cash_reserve_pct": (
            settings.min_cash_buffer_pct
            if cash_reserve_pct is None
            else cash_reserve_pct
        ),
    }
