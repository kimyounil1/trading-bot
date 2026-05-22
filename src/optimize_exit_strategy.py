from itertools import product
from pathlib import Path

import pandas as pd

from src.data_loader import load_cached_price_data_batch
from src.portfolio_backtester import build_ai_score_frames, run_portfolio_backtest
from src.ml_model import load_ai_score_model
from src.settings import load_settings


def _risk_adjusted_score(total_return: float, max_drawdown: float) -> float:
    if max_drawdown == 0:
        return 0.0
    return total_return / abs(max_drawdown)


def main() -> None:
    settings = load_settings()
    period = "2y"

    print(f"Loading cached data for {len(settings.tickers)} tickers...")
    loaded_data = load_cached_price_data_batch(settings.tickers, period=period)
    ticker_data = {ticker: loaded_data[ticker] for ticker in settings.tickers}

    ai_score_frames = None
    if settings.use_ai_score:
        print("Building AI score cache...")
        ai_score_frames = build_ai_score_frames(
            ticker_data,
            ai_model_bundle=load_ai_score_model(),
        )

    common_kwargs = {
        "ticker_data": ticker_data,
        "initial_cash": 10000.0,
        "max_positions": settings.max_total_positions,
        "target_position_pct": settings.max_position_pct,
        "transaction_cost_pct": 0.001,
        "ma_fast": settings.ma_fast,
        "ma_slow": settings.ma_slow,
        "rsi_buy_limit": settings.rsi_buy_limit,
        "use_ai_score": settings.use_ai_score,
        "ai_score_buy_threshold": settings.ai_score_buy_threshold,
        "ai_score_frames": ai_score_frames,
    }

    baseline_result, _, _ = run_portfolio_backtest(**common_kwargs)
    baseline_risk_adjusted = _risk_adjusted_score(
        baseline_result.total_return,
        baseline_result.max_drawdown,
    )

    stop_loss_values = [0.0, 0.03, 0.05, 0.08]
    take_profit_values = [0.0, 0.10, 0.15, 0.25]
    trailing_stop_values = [0.0, 0.05, 0.08, 0.12]

    rows = [
        {
            "mode": "baseline",
            "stop_loss_pct": 0.0,
            "take_profit_pct": 0.0,
            "trailing_stop_pct": 0.0,
            "total_return": baseline_result.total_return,
            "benchmark_return": baseline_result.benchmark_return,
            "max_drawdown": baseline_result.max_drawdown,
            "trades": baseline_result.trades,
            "win_rate": baseline_result.win_rate,
            "final_equity": baseline_result.final_equity,
            "return_vs_baseline": 0.0,
            "drawdown_vs_baseline": 0.0,
            "risk_adjusted_score": baseline_risk_adjusted,
            "risk_adjusted_vs_baseline": 0.0,
            "passes_return_and_risk": True,
        }
    ]

    combos = list(product(stop_loss_values, take_profit_values, trailing_stop_values))
    for index, (stop_loss_pct, take_profit_pct, trailing_stop_pct) in enumerate(
        combos,
        start=1,
    ):
        if stop_loss_pct == 0.0 and take_profit_pct == 0.0 and trailing_stop_pct == 0.0:
            continue

        print(
            f"[{index}/{len(combos)}] "
            f"stop={stop_loss_pct}, take={take_profit_pct}, trailing={trailing_stop_pct}"
        )
        result, _, _ = run_portfolio_backtest(
            **common_kwargs,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct,
            trailing_stop_pct=trailing_stop_pct,
        )
        risk_adjusted = _risk_adjusted_score(result.total_return, result.max_drawdown)
        passes_return_and_risk = (
            result.total_return > baseline_result.total_return
            and result.max_drawdown >= baseline_result.max_drawdown
        )
        rows.append(
            {
                "mode": "exit_rules",
                "stop_loss_pct": stop_loss_pct,
                "take_profit_pct": take_profit_pct,
                "trailing_stop_pct": trailing_stop_pct,
                "total_return": result.total_return,
                "benchmark_return": result.benchmark_return,
                "max_drawdown": result.max_drawdown,
                "trades": result.trades,
                "win_rate": result.win_rate,
                "final_equity": result.final_equity,
                "return_vs_baseline": result.total_return - baseline_result.total_return,
                "drawdown_vs_baseline": result.max_drawdown - baseline_result.max_drawdown,
                "risk_adjusted_score": risk_adjusted,
                "risk_adjusted_vs_baseline": risk_adjusted - baseline_risk_adjusted,
                "passes_return_and_risk": passes_return_and_risk,
            }
        )

    output_dir = Path("logs/exit_strategy")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "grid_search_results.csv"

    df = pd.DataFrame(rows)
    df = df.sort_values(
        ["passes_return_and_risk", "risk_adjusted_score", "total_return"],
        ascending=[False, False, False],
    )
    df.to_csv(output_path, index=False)

    print("-" * 80)
    print(f"Saved exit strategy results to {output_path}")
    print()
    print("Top 10")
    print(
        df.head(10)[
            [
                "mode",
                "stop_loss_pct",
                "take_profit_pct",
                "trailing_stop_pct",
                "total_return",
                "return_vs_baseline",
                "max_drawdown",
                "drawdown_vs_baseline",
                "trades",
                "win_rate",
                "risk_adjusted_score",
                "passes_return_and_risk",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
