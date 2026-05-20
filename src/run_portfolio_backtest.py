from pathlib import Path

from src.config import TICKERS
from src.data_loader import load_price_data
from src.portfolio_backtester import (
    run_portfolio_backtest,
    save_portfolio_backtest_outputs,
)


def pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def main() -> None:
    ticker_data = {}

    for ticker in TICKERS:
        print(f"Loading {ticker}...")
        ticker_data[ticker] = load_price_data(ticker, period="2y")

    result, equity_df, trades_df = run_portfolio_backtest(
        ticker_data=ticker_data,
        initial_cash=10000.0,
        max_positions=3,
        target_position_pct=0.30,
        transaction_cost_pct=0.001,
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
    print("-" * 80)
    print(f"Saved outputs to {output_dir}")


if __name__ == "__main__":
    main()
