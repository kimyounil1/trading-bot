import argparse
from pathlib import Path

from src.settings import load_settings
from src.data_loader import load_price_data_batch
from src.portfolio_backtest_settings import portfolio_backtest_kwargs
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

    bt_kwargs = portfolio_backtest_kwargs(
        settings,
        ticker_data=ticker_data,
        benchmark_df=benchmark_df,
        relative_strength_benchmark_df=relative_strength_benchmark_df,
        vix_df=vix_df,
        macro_df=macro_df,
        allocation_method=args.allocation,
    )
    result, equity_df, trades_df = run_portfolio_backtest(**bt_kwargs)

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
