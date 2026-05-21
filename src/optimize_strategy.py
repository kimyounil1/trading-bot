from itertools import product
from pathlib import Path

import pandas as pd

from src.settings import load_settings
from src.data_loader import load_price_data_batch
from src.portfolio_backtester import run_portfolio_backtest


def main() -> None:
    settings = load_settings()
    print(f"Loading {len(settings.tickers)} tickers...")
    ticker_data = load_price_data_batch(settings.tickers, period="2y")

    ma_fast_values = [10, 20, 30]
    ma_slow_values = [50, 100, 150, 200]
    rsi_buy_limits = [60, 65, 70, 75, 80]
    max_positions_values = [2, 3, 4, 5]
    target_position_pct_values = [0.20, 0.30, 0.40]

    rows = []

    total = (
        len(ma_fast_values)
        * len(ma_slow_values)
        * len(rsi_buy_limits)
        * len(max_positions_values)
        * len(target_position_pct_values)
    )

    count = 0

    for ma_fast, ma_slow, rsi_limit, max_positions, target_pct in product(
        ma_fast_values,
        ma_slow_values,
        rsi_buy_limits,
        max_positions_values,
        target_position_pct_values,
    ):
        if ma_fast >= ma_slow:
            continue

        count += 1
        print(
            f"[{count}/{total}] "
            f"ma_fast={ma_fast}, ma_slow={ma_slow}, "
            f"rsi={rsi_limit}, max_pos={max_positions}, target={target_pct}"
        )

        try:
            result, _, _ = run_portfolio_backtest(
                ticker_data=ticker_data,
                initial_cash=10000.0,
                max_positions=max_positions,
                target_position_pct=target_pct,
                transaction_cost_pct=0.001,
                ma_fast=ma_fast,
                ma_slow=ma_slow,
                rsi_buy_limit=rsi_limit,
            )

            rows.append(
                {
                    "ma_fast": ma_fast,
                    "ma_slow": ma_slow,
                    "rsi_buy_limit": rsi_limit,
                    "max_positions": max_positions,
                    "target_position_pct": target_pct,
                    "total_return": result.total_return,
                    "benchmark_return": result.benchmark_return,
                    "excess_return": result.total_return - result.benchmark_return,
                    "max_drawdown": result.max_drawdown,
                    "trades": result.trades,
                    "win_rate": result.win_rate,
                    "final_equity": result.final_equity,
                }
            )

        except Exception as exc:
            print(f"  ERROR: {exc}")

    output_dir = Path("logs/optimization")
    output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(rows)

    # 단순 수익률만 보면 과최적화될 수 있으니 MDD 대비 수익률도 계산
    df["risk_adjusted_score"] = df["total_return"] / df["max_drawdown"].abs()

    df = df.sort_values(
        ["risk_adjusted_score", "total_return"],
        ascending=[False, False],
    )

    output_path = output_dir / "grid_search_results.csv"
    df.to_csv(output_path, index=False)

    print("-" * 80)
    print(f"Saved optimization results to {output_path}")
    print()
    print("Top 10 by risk_adjusted_score")
    print(
        df.head(10)[
            [
                "ma_fast",
                "ma_slow",
                "rsi_buy_limit",
                "max_positions",
                "target_position_pct",
                "total_return",
                "benchmark_return",
                "max_drawdown",
                "trades",
                "win_rate",
                "risk_adjusted_score",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
