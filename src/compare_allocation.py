"""Compare equal_weight vs MVO vs BL+MVO allocation methods."""

from pathlib import Path

import pandas as pd

from src.settings import load_settings
from src.data_loader import load_price_data_batch
from src.portfolio_backtester import run_portfolio_backtest, save_portfolio_backtest_outputs


METHODS = ["equal_weight", "mvo", "bl_mvo"]


def pct(v: float) -> str:
    return f"{v * 100:.2f}%"


def run_one(method: str, settings, ticker_data, **kwargs):
    result, equity_df, trades_df = run_portfolio_backtest(
        ticker_data=ticker_data,
        initial_cash=10000.0,
        max_positions=settings.max_total_positions,
        target_position_pct=settings.max_position_pct,
        transaction_cost_pct=0.001,
        ma_fast=settings.ma_fast,
        ma_slow=settings.ma_slow,
        rsi_buy_limit=settings.rsi_buy_limit,
        use_ai_score=settings.use_ai_score,
        ai_score_buy_threshold=settings.ai_score_buy_threshold,
        volume_filter_enabled=settings.volume_filter_enabled,
        volume_lookback_days=settings.volume_lookback_days,
        min_volume_ratio=settings.min_volume_ratio,
        rank_trend_weight=settings.rank_trend_weight,
        rank_ai_weight=settings.rank_ai_weight,
        rank_momentum_weight=settings.rank_momentum_weight,
        rank_volatility_weight=settings.rank_volatility_weight,
        allocation_method=method,
        **kwargs,
    )
    return result, equity_df, trades_df


def main() -> None:
    settings = load_settings()
    print(f"Loading {len(settings.tickers)} tickers (2y)...")
    loaded_data = load_price_data_batch(settings.tickers, period="2y")
    ticker_data = {t: loaded_data[t] for t in settings.tickers if t in loaded_data}
    print(f"Loaded {len(ticker_data)} tickers\n")

    rows = []
    for method in METHODS:
        print(f"Running {method}...", end=" ", flush=True)
        result, equity_df, trades_df = run_one(method, settings, ticker_data)
        print("done")

        output_dir = Path(f"logs/allocation_compare/{method}")
        save_portfolio_backtest_outputs(output_dir, result, equity_df, trades_df)

        rows.append({
            "method": method,
            "total_return": pct(result.total_return),
            "max_drawdown": pct(result.max_drawdown),
            "sharpe_ratio": f"{result.sharpe_ratio:.3f}",
            "trades": result.trades,
            "win_rate": pct(result.win_rate),
            "final_equity": f"${result.final_equity:,.2f}",
        })

    print()
    print("-" * 80)
    print("Allocation Method Comparison (2y backtest)")
    print("-" * 80)
    df = pd.DataFrame(rows)
    print(df.to_string(index=False))
    print("-" * 80)
    print("Saved outputs to logs/allocation_compare/")


if __name__ == "__main__":
    main()
