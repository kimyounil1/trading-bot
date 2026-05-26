import argparse
from pathlib import Path

import pandas as pd

from src.data_loader import load_cached_price_data_batch
from src.ml_model import load_ai_score_model
from src.portfolio_backtester import build_ai_score_frames, run_portfolio_backtest
from src.settings import load_settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Test volume and volatility filters one variable at a time."
    )
    parser.add_argument(
        "--no-ai-score",
        action="store_true",
        help="Disable AI score during this optimization run for a faster first-pass check.",
    )
    return parser.parse_args()


def _risk_adjusted_score(total_return: float, max_drawdown: float) -> float:
    if max_drawdown == 0:
        return 0.0
    return total_return / abs(max_drawdown)


def _result_row(
    *,
    mode: str,
    use_ai_score: bool,
    baseline_result,
    result,
    volume_lookback_days: int | None = None,
    min_volume_ratio: float | None = None,
    volatility_lookback_days: int | None = None,
    max_volatility: float | None = None,
) -> dict:
    risk_adjusted = _risk_adjusted_score(result.total_return, result.max_drawdown)
    baseline_risk_adjusted = _risk_adjusted_score(
        baseline_result.total_return,
        baseline_result.max_drawdown,
    )
    passes_return_and_risk = (
        result.total_return > baseline_result.total_return
        and result.max_drawdown >= baseline_result.max_drawdown
    )
    return {
        "mode": mode,
        "use_ai_score": use_ai_score,
        "volume_lookback_days": volume_lookback_days,
        "min_volume_ratio": min_volume_ratio,
        "volatility_lookback_days": volatility_lookback_days,
        "max_volatility": max_volatility,
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


def main() -> None:
    args = parse_args()
    settings = load_settings()
    period = "2y"

    print(f"Loading cached data for {len(settings.tickers)} tickers...")
    loaded_data = load_cached_price_data_batch(settings.tickers, period=period)
    ticker_data = {ticker: loaded_data[ticker] for ticker in settings.tickers}

    use_ai_score = bool(settings.use_ai_score and not args.no_ai_score)
    ai_score_frames = None
    if use_ai_score:
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
        "use_ai_score": use_ai_score,
        "ai_score_buy_threshold": settings.ai_score_buy_threshold,
        "ai_score_frames": ai_score_frames,
        "rank_trend_weight": settings.rank_trend_weight,
        "rank_ai_weight": settings.rank_ai_weight,
        "rank_momentum_weight": settings.rank_momentum_weight,
        "rank_volatility_weight": settings.rank_volatility_weight,
    }

    baseline_result, _, _ = run_portfolio_backtest(**common_kwargs)
    rows = [
        _result_row(
            mode="baseline",
            use_ai_score=use_ai_score,
            baseline_result=baseline_result,
            result=baseline_result,
        )
    ]

    volume_lookback_values = [10, 20, 40, 60]
    min_volume_ratio_values = [0.8, 1.0, 1.2, 1.5, 2.0]
    total_volume = len(volume_lookback_values) * len(min_volume_ratio_values)
    for index, volume_lookback_days in enumerate(volume_lookback_values, start=1):
        for min_volume_ratio in min_volume_ratio_values:
            print(
                f"[volume {index}/{len(volume_lookback_values)}] "
                f"lookback={volume_lookback_days}, min_ratio={min_volume_ratio}"
            )
            result, _, _ = run_portfolio_backtest(
                **common_kwargs,
                volume_filter_enabled=True,
                volume_lookback_days=volume_lookback_days,
                min_volume_ratio=min_volume_ratio,
            )
            rows.append(
                _result_row(
                    mode="volume_filter",
                    use_ai_score=use_ai_score,
                    baseline_result=baseline_result,
                    result=result,
                    volume_lookback_days=volume_lookback_days,
                    min_volume_ratio=min_volume_ratio,
                )
            )

    volatility_lookback_values = [10, 20, 40, 60]
    max_volatility_values = [0.02, 0.03, 0.04, 0.05, 0.06]
    total_volatility = len(volatility_lookback_values) * len(max_volatility_values)
    for index, volatility_lookback_days in enumerate(volatility_lookback_values, start=1):
        for max_volatility in max_volatility_values:
            print(
                f"[volatility {index}/{len(volatility_lookback_values)}] "
                f"lookback={volatility_lookback_days}, max_vol={max_volatility}"
            )
            result, _, _ = run_portfolio_backtest(
                **common_kwargs,
                volatility_filter_enabled=True,
                volatility_lookback_days=volatility_lookback_days,
                max_volatility=max_volatility,
            )
            rows.append(
                _result_row(
                    mode="volatility_filter",
                    use_ai_score=use_ai_score,
                    baseline_result=baseline_result,
                    result=result,
                    volatility_lookback_days=volatility_lookback_days,
                    max_volatility=max_volatility,
                )
            )

    output_dir = Path("logs/volume_volatility")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_name = "grid_search_results_ai.csv" if use_ai_score else "grid_search_results_no_ai.csv"
    output_path = output_dir / output_name

    df = pd.DataFrame(rows)
    df = df.sort_values(
        ["passes_return_and_risk", "risk_adjusted_score", "total_return"],
        ascending=[False, False, False],
    )
    df.to_csv(output_path, index=False)

    print("-" * 80)
    print(f"Saved volume/volatility results to {output_path}")
    print(f"volume_combinations={total_volume}, volatility_combinations={total_volatility}")
    print()
    print("Top 10")
    print(
        df.head(10)[
            [
                "mode",
                "use_ai_score",
                "volume_lookback_days",
                "min_volume_ratio",
                "volatility_lookback_days",
                "max_volatility",
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
