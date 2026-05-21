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
    # 후보 B: 표본/안정성 우선
    params = {
        "ma_fast": 10,
        "ma_slow": 50,
        "rsi_buy_limit": 65,
        "max_positions": 2,
        "target_position_pct": 0.40,
        "transaction_cost_pct": 0.001,
    }

    print(f"Loading {len(settings.tickers)} tickers...")
    tickers_to_load = list(settings.tickers)
    if settings.market_regime_filter_enabled:
        tickers_to_load.append(settings.market_regime_ticker)
        tickers_to_load = list(dict.fromkeys(tickers_to_load))
    loaded_data = load_price_data_batch(tickers_to_load, period="2y")
    ticker_data = {ticker: loaded_data[ticker] for ticker in settings.tickers}
    benchmark_df = (
        loaded_data[settings.market_regime_ticker]
        if settings.market_regime_filter_enabled
        else None
    )

    result, equity_df, trades_df = run_portfolio_backtest(
        ticker_data=ticker_data,
        benchmark_df=benchmark_df,
        initial_cash=10000.0,
        market_regime_filter_enabled=settings.market_regime_filter_enabled,
        market_regime_ma_fast=settings.market_regime_ma_fast,
        market_regime_ma_slow=settings.market_regime_ma_slow,
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
