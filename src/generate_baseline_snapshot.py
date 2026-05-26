import json
from dataclasses import asdict
from pathlib import Path

from src.data_loader import load_cached_price_data_batch
from src.portfolio_backtester import (
    PortfolioBacktestResult,
    run_portfolio_backtest,
    save_portfolio_backtest_outputs,
)
from src.qlib_adapter import export_qlib_ready_data
from src.snapshot_utils import build_snapshot_payload, save_snapshot_payload
from src.settings import load_settings


def _serialize_result(result: PortfolioBacktestResult) -> dict:
    return asdict(result)


def main() -> None:
    settings = load_settings()
    period = "2y"
    output_dir = Path("logs/baselines/current_strategy")

    print(f"Loading cached data for {len(settings.tickers)} tickers...")
    tickers_to_load = list(settings.tickers)
    if settings.market_regime_filter_enabled:
        tickers_to_load.append(settings.market_regime_ticker)
    if settings.relative_strength_filter_enabled:
        tickers_to_load.append(settings.relative_strength_benchmark_ticker)
    tickers_to_load = list(dict.fromkeys(tickers_to_load))
    loaded_data = load_cached_price_data_batch(tickers_to_load, period=period)
    ticker_data = {ticker: loaded_data[ticker] for ticker in settings.tickers}
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

    result, equity_df, trades_df = run_portfolio_backtest(
        ticker_data=ticker_data,
        benchmark_df=benchmark_df,
        relative_strength_benchmark_df=relative_strength_benchmark_df,
        initial_cash=10000.0,
        max_positions=settings.max_total_positions,
        target_position_pct=settings.max_position_pct,
        transaction_cost_pct=0.001,
        ma_fast=settings.ma_fast,
        ma_slow=settings.ma_slow,
        rsi_buy_limit=settings.rsi_buy_limit,
        use_ai_score=settings.use_ai_score,
        ai_score_buy_threshold=settings.ai_score_buy_threshold,
        market_regime_filter_enabled=settings.market_regime_filter_enabled,
        market_regime_ma_fast=settings.market_regime_ma_fast,
        market_regime_ma_slow=settings.market_regime_ma_slow,
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

    save_portfolio_backtest_outputs(
        output_dir=output_dir,
        result=result,
        equity_df=equity_df,
        trades_df=trades_df,
    )

    qlib_paths = export_qlib_ready_data(
        ticker_data=ticker_data,
        output_dir=output_dir / "qlib_ready",
    )

    metadata = build_snapshot_payload(
        period=period,
        tickers=settings.tickers,
        settings=settings,
        result=_serialize_result(result),
        equity_rows=len(equity_df),
        trade_rows=len(trades_df),
        extra_fields={"qlib_ready_files": [str(path) for path in qlib_paths]},
    )

    metadata_path = save_snapshot_payload(
        metadata,
        output_dir / "baseline_snapshot.json",
    )

    print(f"Saved baseline snapshot to {metadata_path}")


if __name__ == "__main__":
    main()
