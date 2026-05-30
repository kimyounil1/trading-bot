"""Compare portfolio backtest metrics with factor/crowding guard on vs off."""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pandas as pd

from src.data_loader import load_price_data_batch
from src.macro_loader import load_macro_data
from src.portfolio_backtester import build_ai_score_frames, run_portfolio_backtest
from src.settings import StrategySettings, load_settings

from src.guard_impact_metrics import (
    GUARD_IMPACT_REPORT_KEYS,
    delta_metrics,
    result_metrics,
    validate_guard_impact_report,
)

DEFAULT_OUTPUT_DIR = Path("logs/guard_impact")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_guard_impact_report(
    *,
    settings: StrategySettings,
    ticker_data: dict[str, pd.DataFrame],
    benchmark_df: pd.DataFrame | None,
    relative_strength_benchmark_df: pd.DataFrame | None,
    vix_df: pd.DataFrame | None,
    macro_df: pd.DataFrame | None,
    ai_score_frames: dict[str, pd.DataFrame] | None,
) -> dict[str, Any]:
    common_kwargs = dict(
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
        ai_exit_enabled=getattr(settings, "ai_exit_enabled", False),
        ai_exit_threshold=getattr(settings, "ai_exit_threshold", 0.35),
        ai_exit_dynamic_enabled=getattr(settings, "ai_exit_dynamic_enabled", False),
        ai_exit_vix_low=getattr(settings, "ai_exit_vix_low", 15.0),
        ai_exit_vix_high=getattr(settings, "ai_exit_vix_high", 25.0),
        ai_exit_threshold_bull=getattr(settings, "ai_exit_threshold_bull", 0.55),
        ai_exit_threshold_bear=getattr(settings, "ai_exit_threshold_bear", 0.28),
        vix_df=vix_df,
        macro_df=macro_df,
        ai_score_frames=ai_score_frames,
    )

    settings_off = replace(settings, crowding_guard_enabled=False)
    settings_on = replace(settings, crowding_guard_enabled=True)

    with patch("src.risk_manager.load_settings", return_value=settings_off):
        baseline_result, _, baseline_trades = run_portfolio_backtest(
            **common_kwargs,
            crowding_guard_enabled=False,
        )
    with patch("src.risk_manager.load_settings", return_value=settings_on):
        guarded_result, _, guarded_trades = run_portfolio_backtest(
            **common_kwargs,
            crowding_guard_enabled=True,
        )

    baseline = result_metrics(baseline_result)
    guarded = result_metrics(guarded_result)
    blocked_buys = max(0, len(baseline_trades) - len(guarded_trades))

    guarded["estimated_crowding_blocked_trades"] = blocked_buys
    delta = delta_metrics(baseline, guarded)

    return validate_guard_impact_report(
        {
            "generated_at": _utc_now_iso(),
            "baseline": baseline,
            "with_crowding_guard": guarded,
            "delta": delta,
            "crowding_guard_enabled_in_config": bool(settings.crowding_guard_enabled),
        }
    )


def write_guard_impact_artifacts(report: dict[str, Any], output_dir: Path = DEFAULT_OUTPUT_DIR) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "latest_summary.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return path


def run_guard_impact_report() -> dict[str, Any]:
    settings = load_settings()
    tickers_to_load = list(settings.tickers)
    if settings.market_regime_filter_enabled:
        tickers_to_load.append(settings.market_regime_ticker)
    if settings.relative_strength_filter_enabled:
        tickers_to_load.append(settings.relative_strength_benchmark_ticker)
    if settings.use_ai_score and "^VIX" not in tickers_to_load:
        tickers_to_load.append("^VIX")
    tickers_to_load = list(dict.fromkeys(tickers_to_load))
    loaded = load_price_data_batch(tickers_to_load, period="2y")
    ticker_data = {t: loaded[t] for t in settings.tickers if t in loaded}
    vix_df = loaded.get("^VIX")
    macro_df = load_macro_data(period="2y") if settings.use_ai_score else None
    benchmark_df = (
        loaded.get(settings.market_regime_ticker)
        if settings.market_regime_filter_enabled
        else None
    )
    rs_df = (
        loaded.get(settings.relative_strength_benchmark_ticker)
        if settings.relative_strength_filter_enabled
        else None
    )
    ai_score_frames = None
    if settings.use_ai_score:
        ai_score_frames = build_ai_score_frames(
            ticker_data=ticker_data,
            vix_df=vix_df,
            macro_df=macro_df,
        )

    report = build_guard_impact_report(
        settings=settings,
        ticker_data=ticker_data,
        benchmark_df=benchmark_df,
        relative_strength_benchmark_df=rs_df,
        vix_df=vix_df,
        macro_df=macro_df,
        ai_score_frames=ai_score_frames,
    )
    write_guard_impact_artifacts(report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Crowding guard backtest impact report")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    report = run_guard_impact_report()
    write_guard_impact_artifacts(report, Path(args.output_dir))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
