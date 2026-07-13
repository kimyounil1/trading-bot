from pathlib import Path

from src.settings import load_settings
from src.data_loader import load_price_data_batch
from src.portfolio_backtester import (
    run_portfolio_backtest,
    save_portfolio_backtest_outputs,
)


def pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def main() -> None:
    settings = load_settings()
    # Keep the selected-strategy runner aligned with the active entry signal.
    params = {
        "ma_fast": settings.ma_fast,
        "ma_slow": settings.ma_slow,
        "rsi_buy_limit": settings.rsi_buy_limit,
        "max_positions": 2,
        "target_position_pct": 0.40,
        "transaction_cost_pct": 0.001,
    }

    print(f"Loading {len(settings.tickers)} tickers...")
    tickers_to_load = list(settings.tickers)
    if settings.market_regime_filter_enabled:
        tickers_to_load.append(settings.market_regime_ticker)
    if settings.relative_strength_filter_enabled:
        tickers_to_load.append(settings.relative_strength_benchmark_ticker)
    tickers_to_load = list(dict.fromkeys(tickers_to_load))
    loaded_data = load_price_data_batch(tickers_to_load, period="2y")
    ticker_data = {ticker: loaded_data[ticker] for ticker in settings.tickers}
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
        **params,
    )

    output_dir = Path("logs/selected_strategy")
    save_portfolio_backtest_outputs(
        output_dir=output_dir,
        result=result,
        equity_df=equity_df,
        trades_df=trades_df,
    )

    print("-" * 80)
    print("Selected strategy params")
    for key, value in params.items():
        print(f"{key}={value}")

    print("-" * 80)
    print("Selected strategy result")
    print(f"strategy_return={pct(result.total_return)}")
    print(f"equal_weight_buy_hold={pct(result.benchmark_return)}")
    print(f"max_drawdown={pct(result.max_drawdown)}")
    print(f"trades={result.trades}")
    print(f"win_rate={pct(result.win_rate)}")
    print(f"final_equity=${result.final_equity:.2f}")
    print("-" * 80)
    print(f"Saved outputs to {output_dir}")


if __name__ == "__main__":
    main()
