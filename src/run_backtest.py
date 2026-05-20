from pathlib import Path

import pandas as pd

from src.config import TICKERS
from src.data_loader import load_price_data
from src.backtester import run_backtest


def pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def main() -> None:
    output_dir = Path("logs/backtests")
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []

    for ticker in TICKERS:
        try:
            df = load_price_data(ticker, period="2y")
            result, equity_df, trades_df = run_backtest(ticker, df)

            equity_path = output_dir / f"{ticker}_equity.csv"
            trades_path = output_dir / f"{ticker}_trades.csv"

            equity_df.to_csv(equity_path, index=False)
            trades_df.to_csv(trades_path, index=False)

            results.append(
                {
                    "ticker": result.ticker,
                    "total_return": result.total_return,
                    "buy_hold_return": result.buy_hold_return,
                    "max_drawdown": result.max_drawdown,
                    "trades": result.trades,
                    "win_rate": result.win_rate,
                    "final_equity": result.final_equity,
                }
            )

            print(
                f"{ticker}: "
                f"strategy={pct(result.total_return)}, "
                f"buy_hold={pct(result.buy_hold_return)}, "
                f"mdd={pct(result.max_drawdown)}, "
                f"trades={result.trades}, "
                f"win_rate={pct(result.win_rate)}, "
                f"final_equity=${result.final_equity:.2f}"
            )

        except Exception as exc:
            print(f"{ticker}: ERROR - {exc}")

    results_df = pd.DataFrame(results)
    results_df.to_csv(output_dir / "summary.csv", index=False)

    print("-" * 80)
    print(f"Saved summary to {output_dir / 'summary.csv'}")


if __name__ == "__main__":
    main()
