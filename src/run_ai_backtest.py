from pathlib import Path

from src.settings import load_settings
from src.data_loader import load_price_data
from src.portfolio_backtester import (
    run_portfolio_backtest,
    save_portfolio_backtest_outputs,
)


def pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def main() -> None:
    settings = load_settings()

    ticker_data = {}

    for ticker in settings.tickers:
        print(f"Loading {ticker}...")
        ticker_data[ticker] = load_price_data(ticker, period="2y")

    print("Running baseline backtest...")
    baseline_result, baseline_equity, baseline_trades = run_portfolio_backtest(
        ticker_data=ticker_data,
        initial_cash=10000.0,
        max_positions=settings.max_total_positions,
        target_position_pct=settings.max_position_pct,
        transaction_cost_pct=0.001,
        ma_fast=settings.ma_fast,
        ma_slow=settings.ma_slow,
        rsi_buy_limit=settings.rsi_buy_limit,
        use_ai_score=False,
        ai_score_buy_threshold=settings.ai_score_buy_threshold,
    )

    print("Running AI-filtered backtest...")
    ai_result, ai_equity, ai_trades = run_portfolio_backtest(
        ticker_data=ticker_data,
        initial_cash=10000.0,
        max_positions=settings.max_total_positions,
        target_position_pct=settings.max_position_pct,
        transaction_cost_pct=0.001,
        ma_fast=settings.ma_fast,
        ma_slow=settings.ma_slow,
        rsi_buy_limit=settings.rsi_buy_limit,
        use_ai_score=True,
        ai_score_buy_threshold=settings.ai_score_buy_threshold,
    )

    output_dir = Path("logs/ai_backtest")
    output_dir.mkdir(parents=True, exist_ok=True)

    save_portfolio_backtest_outputs(
        output_dir=output_dir / "baseline",
        result=baseline_result,
        equity_df=baseline_equity,
        trades_df=baseline_trades,
    )

    save_portfolio_backtest_outputs(
        output_dir=output_dir / "ai_filtered",
        result=ai_result,
        equity_df=ai_equity,
        trades_df=ai_trades,
    )

    print("-" * 80)
    print("Baseline")
    print(f"return={pct(baseline_result.total_return)}")
    print(f"benchmark={pct(baseline_result.benchmark_return)}")
    print(f"mdd={pct(baseline_result.max_drawdown)}")
    print(f"trades={baseline_result.trades}")
    print(f"win_rate={pct(baseline_result.win_rate)}")
    print(f"final_equity=${baseline_result.final_equity:.2f}")

    print("-" * 80)
    print("AI Filtered")
    print(f"threshold={settings.ai_score_buy_threshold}")
    print(f"return={pct(ai_result.total_return)}")
    print(f"benchmark={pct(ai_result.benchmark_return)}")
    print(f"mdd={pct(ai_result.max_drawdown)}")
    print(f"trades={ai_result.trades}")
    print(f"win_rate={pct(ai_result.win_rate)}")
    print(f"final_equity=${ai_result.final_equity:.2f}")

    print("-" * 80)
    print("Saved to logs/ai_backtest")


if __name__ == "__main__":
    main()
