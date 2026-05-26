from pathlib import Path

import pandas as pd

from src.settings import load_settings
from src.data_loader import load_cached_price_data_batch
from src.ml_model import load_ai_score_model
from src.portfolio_backtester import build_ai_score_frames, run_portfolio_backtest


def pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def main() -> None:
    settings = load_settings()

    print(f"Loading cached data for {len(settings.tickers)} tickers...")
    tickers_to_load = list(settings.tickers)
    if settings.relative_strength_filter_enabled:
        tickers_to_load.append(settings.relative_strength_benchmark_ticker)
    tickers_to_load = list(dict.fromkeys(tickers_to_load))
    loaded_data = load_cached_price_data_batch(tickers_to_load, period="2y")
    ticker_data = {ticker: loaded_data[ticker] for ticker in settings.tickers}
    relative_strength_benchmark_df = (
        loaded_data[settings.relative_strength_benchmark_ticker]
        if settings.relative_strength_filter_enabled
        else None
    )
    print("Building AI score cache...")
    ai_score_frames = build_ai_score_frames(
        ticker_data,
        ai_model_bundle=load_ai_score_model(),
    )

    thresholds = [0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70]

    rows = []

    print("Running baseline...")
    baseline_result, _, _ = run_portfolio_backtest(
        ticker_data=ticker_data,
        relative_strength_benchmark_df=relative_strength_benchmark_df,
        initial_cash=10000.0,
        max_positions=settings.max_total_positions,
        target_position_pct=settings.max_position_pct,
        transaction_cost_pct=0.001,
        ma_fast=settings.ma_fast,
        ma_slow=settings.ma_slow,
        rsi_buy_limit=settings.rsi_buy_limit,
        use_ai_score=False,
        ai_score_buy_threshold=settings.ai_score_buy_threshold,
        relative_strength_filter_enabled=settings.relative_strength_filter_enabled,
        relative_strength_lookback_days=settings.relative_strength_lookback_days,
        relative_strength_min_excess_return=settings.relative_strength_min_excess_return,
        volume_filter_enabled=settings.volume_filter_enabled,
        volume_lookback_days=settings.volume_lookback_days,
        min_volume_ratio=settings.min_volume_ratio,
        volatility_filter_enabled=settings.volatility_filter_enabled,
        volatility_lookback_days=settings.volatility_lookback_days,
        max_volatility=settings.max_volatility,
        rank_trend_weight=settings.rank_trend_weight,
        rank_ai_weight=settings.rank_ai_weight,
        rank_momentum_weight=settings.rank_momentum_weight,
        rank_volatility_weight=settings.rank_volatility_weight,
    )

    rows.append(
        {
            "mode": "baseline",
            "ai_threshold": None,
            "total_return": baseline_result.total_return,
            "benchmark_return": baseline_result.benchmark_return,
            "max_drawdown": baseline_result.max_drawdown,
            "trades": baseline_result.trades,
            "win_rate": baseline_result.win_rate,
            "final_equity": baseline_result.final_equity,
            "return_vs_baseline": 0.0,
            "mdd_vs_baseline": 0.0,
        }
    )

    for threshold in thresholds:
        print(f"Running AI threshold={threshold}...")

        result, _, _ = run_portfolio_backtest(
            ticker_data=ticker_data,
            relative_strength_benchmark_df=relative_strength_benchmark_df,
            initial_cash=10000.0,
            max_positions=settings.max_total_positions,
            target_position_pct=settings.max_position_pct,
            transaction_cost_pct=0.001,
            ma_fast=settings.ma_fast,
            ma_slow=settings.ma_slow,
            rsi_buy_limit=settings.rsi_buy_limit,
            use_ai_score=True,
            ai_score_buy_threshold=threshold,
            ai_score_frames=ai_score_frames,
            relative_strength_filter_enabled=settings.relative_strength_filter_enabled,
            relative_strength_lookback_days=settings.relative_strength_lookback_days,
            relative_strength_min_excess_return=settings.relative_strength_min_excess_return,
            volume_filter_enabled=settings.volume_filter_enabled,
            volume_lookback_days=settings.volume_lookback_days,
            min_volume_ratio=settings.min_volume_ratio,
            volatility_filter_enabled=settings.volatility_filter_enabled,
            volatility_lookback_days=settings.volatility_lookback_days,
            max_volatility=settings.max_volatility,
            rank_trend_weight=settings.rank_trend_weight,
            rank_ai_weight=settings.rank_ai_weight,
            rank_momentum_weight=settings.rank_momentum_weight,
            rank_volatility_weight=settings.rank_volatility_weight,
        )

        rows.append(
            {
                "mode": "ai_filtered",
                "ai_threshold": threshold,
                "total_return": result.total_return,
                "benchmark_return": result.benchmark_return,
                "max_drawdown": result.max_drawdown,
                "trades": result.trades,
                "win_rate": result.win_rate,
                "final_equity": result.final_equity,
                "return_vs_baseline": result.total_return - baseline_result.total_return,
                "mdd_vs_baseline": result.max_drawdown - baseline_result.max_drawdown,
            }
        )

    output_dir = Path("logs/ai_threshold")
    output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(rows)
    df["risk_adjusted_score"] = df["total_return"] / df["max_drawdown"].abs()

    output_path = output_dir / "threshold_results.csv"
    df.to_csv(output_path, index=False)

    print("-" * 80)
    print(f"Saved to {output_path}")
    print()
    print(
        df[
            [
                "mode",
                "ai_threshold",
                "total_return",
                "max_drawdown",
                "trades",
                "win_rate",
                "return_vs_baseline",
                "mdd_vs_baseline",
                "risk_adjusted_score",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
