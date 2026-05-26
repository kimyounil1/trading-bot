import argparse
from pathlib import Path

from src.settings import load_settings
from src.data_loader import load_price_data_batch
from src.portfolio_backtester import (
    run_portfolio_backtest,
    save_portfolio_backtest_outputs,
)
from src.macro_loader import load_macro_data


def pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--allocation",
        choices=["equal_weight", "mvo", "bl_mvo"],
        default="equal_weight",
        help="Position sizing method",
    )
    args = parser.parse_args()

    settings = load_settings()
    print(f"Loading {len(settings.tickers)} tickers...")
    tickers_to_load = list(settings.tickers)
    if settings.market_regime_filter_enabled:
        tickers_to_load.append(settings.market_regime_ticker)
    if settings.relative_strength_filter_enabled:
        tickers_to_load.append(settings.relative_strength_benchmark_ticker)
    if settings.use_ai_score and "^VIX" not in tickers_to_load:
        tickers_to_load.append("^VIX")
    tickers_to_load = list(dict.fromkeys(tickers_to_load))
    loaded_data = load_price_data_batch(tickers_to_load, period="2y")
    ticker_data = {ticker: loaded_data[ticker] for ticker in settings.tickers}
    vix_df = loaded_data.get("^VIX")
    macro_df = load_macro_data(period="2y") if settings.use_ai_score else None
    benchmark_df = (
        loaded_data[settings.market_regime_ticker]
        if settings.market_regime_filter_enabled
        else None
    )
    relative_strength_benchmark_df = (
        loaded_data[settings.relative_strength_benchmark_ticker]
        if settings.relative_strength_filter_enabled
        else None
    )

    result, equity_df, trades_df = run_portfolio_backtest(
        ticker_data=ticker_data,
        benchmark_df=benchmark_df,
        relative_strength_benchmark_df=relative_strength_benchmark_df,
        initial_cash=10000.0,
        max_positions=settings.max_total_positions,
        target_position_pct=settings.max_position_pct,
        transaction_cost_pct=0.001,
        ma_fast=settings.ma_fast,
        ma_slow=settings.ma_slow,
        rsi_buy_limit=settings.rsi_buy_limit,
        use_ai_score=settings.use_ai_score,
        ai_score_buy_threshold=settings.ai_score_buy_threshold,
        market_regime_filter_enabled=settings.market_regime_filter_enabled,
        market_regime_ma_fast=settings.market_regime_ma_fast,
        market_regime_ma_slow=settings.market_regime_ma_slow,
        relative_strength_filter_enabled=settings.relative_strength_filter_enabled,
        relative_strength_lookback_days=settings.relative_strength_lookback_days,
        relative_strength_min_excess_return=settings.relative_strength_min_excess_return,
        volume_filter_enabled=settings.volume_filter_enabled,
        volume_lookback_days=settings.volume_lookback_days,
        min_volume_ratio=settings.min_volume_ratio,
        volatility_filter_enabled=settings.volatility_filter_enabled,
        volatility_lookback_days=settings.volatility_lookback_days,
        max_volatility=settings.max_volatility,
        rank_trend_weight=settings.rank_trend_weight,
        rank_ai_weight=settings.rank_ai_weight,
        rank_momentum_weight=settings.rank_momentum_weight,
        rank_volatility_weight=settings.rank_volatility_weight,
        allocation_method=args.allocation,
        ai_exit_enabled=getattr(settings, "ai_exit_enabled", False),
        ai_exit_threshold=getattr(settings, "ai_exit_threshold", 0.35),
        ai_exit_dynamic_enabled=getattr(settings, "ai_exit_dynamic_enabled", False),
        ai_exit_vix_low=getattr(settings, "ai_exit_vix_low", 15.0),
        ai_exit_vix_high=getattr(settings, "ai_exit_vix_high", 25.0),
        ai_exit_threshold_bull=getattr(settings, "ai_exit_threshold_bull", 0.55),
        ai_exit_threshold_bear=getattr(settings, "ai_exit_threshold_bear", 0.28),
        vix_df=vix_df,
        macro_df=macro_df,
    )

    output_dir = Path("logs/portfolio_backtest")
    save_portfolio_backtest_outputs(
        output_dir=output_dir,
        result=result,
        equity_df=equity_df,
        trades_df=trades_df,
    )

    print("-" * 80)
    print("Portfolio backtest result")
    print(f"strategy_return={pct(result.total_return)}")
    print(f"equal_weight_buy_hold={pct(result.benchmark_return)}")
    print(f"max_drawdown={pct(result.max_drawdown)}")
    print(f"trades={result.trades}")
    print(f"win_rate={pct(result.win_rate)}")
    print(f"final_equity=${result.final_equity:.2f}")
    print(f"sharpe_ratio={result.sharpe_ratio:.3f}")
    print(f"allocation_method={args.allocation}")
    print("-" * 80)
    print(f"Saved outputs to {output_dir}")


if __name__ == "__main__":
    main()
