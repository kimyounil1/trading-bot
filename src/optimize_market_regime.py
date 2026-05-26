import argparse
from itertools import product
from pathlib import Path

import pandas as pd

from src.data_loader import load_cached_price_data_batch
from src.ml_model import load_ai_score_model
from src.portfolio_backtester import build_ai_score_frames, run_portfolio_backtest
from src.settings import load_settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Grid-search market regime filter settings against the current baseline."
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


def main() -> None:
    args = parse_args()
    settings = load_settings()
    period = "2y"
    benchmark_ticker = settings.market_regime_ticker

    tickers_to_load = list(dict.fromkeys([*settings.tickers, benchmark_ticker]))
    print(f"Loading cached data for {len(tickers_to_load)} tickers...")
    loaded_data = load_cached_price_data_batch(tickers_to_load, period=period)
    ticker_data = {ticker: loaded_data[ticker] for ticker in settings.tickers}
    benchmark_df = loaded_data[benchmark_ticker]

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
        "volume_filter_enabled": settings.volume_filter_enabled,
        "volume_lookback_days": settings.volume_lookback_days,
        "min_volume_ratio": settings.min_volume_ratio,
        "volatility_filter_enabled": settings.volatility_filter_enabled,
        "volatility_lookback_days": settings.volatility_lookback_days,
        "max_volatility": settings.max_volatility,
        "rank_trend_weight": settings.rank_trend_weight,
        "rank_ai_weight": settings.rank_ai_weight,
        "rank_momentum_weight": settings.rank_momentum_weight,
        "rank_volatility_weight": settings.rank_volatility_weight,
    }

    baseline_result, _, _ = run_portfolio_backtest(**common_kwargs)
    baseline_risk_adjusted = _risk_adjusted_score(
        baseline_result.total_return,
        baseline_result.max_drawdown,
    )

    rows = [
        {
            "mode": "baseline",
            "use_ai_score": use_ai_score,
            "benchmark_ticker": benchmark_ticker,
            "market_regime_ma_fast": None,
            "market_regime_ma_slow": None,
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

    fast_values = [20, 50, 100]
    slow_values = [100, 150, 200]
    combos = [
        (fast, slow)
        for fast, slow in product(fast_values, slow_values)
        if fast < slow
    ]
    for index, (market_regime_ma_fast, market_regime_ma_slow) in enumerate(
        combos,
        start=1,
    ):
        print(
            f"[{index}/{len(combos)}] "
            f"market_fast={market_regime_ma_fast}, market_slow={market_regime_ma_slow}"
        )
        result, _, _ = run_portfolio_backtest(
            **common_kwargs,
            benchmark_df=benchmark_df,
            market_regime_filter_enabled=True,
            market_regime_ma_fast=market_regime_ma_fast,
            market_regime_ma_slow=market_regime_ma_slow,
        )
        risk_adjusted = _risk_adjusted_score(result.total_return, result.max_drawdown)
        passes_return_and_risk = (
            result.total_return > baseline_result.total_return
            and result.max_drawdown >= baseline_result.max_drawdown
        )
        rows.append(
            {
                "mode": "market_regime",
                "use_ai_score": use_ai_score,
                "benchmark_ticker": benchmark_ticker,
                "market_regime_ma_fast": market_regime_ma_fast,
                "market_regime_ma_slow": market_regime_ma_slow,
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

    output_dir = Path("logs/market_regime")
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
    print(f"Saved market regime results to {output_path}")
    print()
    print("Top 10")
    print(
        df.head(10)[
            [
                "mode",
                "use_ai_score",
                "benchmark_ticker",
                "market_regime_ma_fast",
                "market_regime_ma_slow",
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
