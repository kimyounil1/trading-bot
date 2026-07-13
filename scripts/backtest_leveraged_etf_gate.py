#!/usr/bin/env python3
"""Compare the active core universe with a risk-capped leveraged-ETF overlay."""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data_loader import load_price_data_batch
from src.instrument_meta import load_instrument_registry
from src.macro_loader import load_macro_data
from src.portfolio_backtest_settings import portfolio_backtest_kwargs
from src.portfolio_backtester import run_portfolio_backtest
from src.settings import load_settings


OUTPUT_DIR = Path("logs/leverage_etf_validation_20260713")


def _result_row(label, window, result, equity, trades, leveraged_tickers) -> dict:
    leverage_trades = 0
    if not trades.empty and "ticker" in trades:
        leverage_trades = int(trades["ticker"].isin(leveraged_tickers).sum())
    return {
        "mode": label,
        "window": window,
        "total_return": result.total_return,
        "max_drawdown": result.max_drawdown,
        "sharpe_ratio": result.sharpe_ratio,
        "trades": result.trades,
        "win_rate": result.win_rate,
        "benchmark_return": result.benchmark_return,
        "avg_positions": float(equity["positions_count"].mean()),
        "final_open_symbols": str(equity.iloc[-1]["open_symbols"]),
        "leveraged_trades": leverage_trades,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--include-operational", action="store_true")
    args = parser.parse_args()

    settings = load_settings()
    registry = load_instrument_registry()
    leveraged = sorted(
        ticker for ticker, meta in registry.items() if meta.is_leveraged_etf
    )
    core = list(settings.tickers)
    expanded = list(dict.fromkeys([*core, *leveraged]))
    loaded = load_price_data_batch([*expanded, "^VIX"], period="5y")
    core_data = {ticker: loaded[ticker] for ticker in core}
    expanded_data = {ticker: loaded[ticker] for ticker in expanded}
    vix_df = loaded["^VIX"]

    end = min(pd.to_datetime(frame["date"]).max() for frame in expanded_data.values())
    windows = {
        "6m": end - pd.DateOffset(months=6),
        "1y": end - pd.DateOffset(years=1),
        "4y": end - pd.DateOffset(years=4),
    }
    common = {
        "initial_cash": 10_000.0,
        "max_positions": settings.max_total_positions,
        "target_position_pct": settings.max_position_pct,
        "transaction_cost_pct": 0.001,
        "ma_fast": settings.ma_fast,
        "ma_slow": settings.ma_slow,
        "rsi_buy_limit": settings.rsi_buy_limit,
        "stop_loss_pct": settings.stop_loss_pct,
        "take_profit_pct": settings.take_profit_pct,
        "trailing_stop_pct": settings.trailing_stop_pct,
        "max_holding_days": settings.max_holding_days,
        "vix_df": vix_df,
        "max_leveraged_etf_positions": settings.max_leveraged_etf_positions,
        "leveraged_etf_allowlist": list(settings.leveraged_etf_allowlist),
        "max_effective_leverage_exposure_pct": settings.max_effective_leverage_exposure_pct,
        "block_leveraged_etfs_vix_above": settings.block_leveraged_etfs_vix_above,
        "evaluation_end_date": end,
    }

    rows: list[dict] = []
    for window, start in windows.items():
        baseline, baseline_eq, baseline_trades = run_portfolio_backtest(
            ticker_data=core_data,
            allow_leveraged_etfs=False,
            evaluation_start_date=start,
            **common,
        )
        overlay, overlay_eq, overlay_trades = run_portfolio_backtest(
            ticker_data=expanded_data,
            allow_leveraged_etfs=True,
            evaluation_start_date=start,
            **common,
        )
        rows.append(
            _result_row(
                "technical_core", window, baseline, baseline_eq, baseline_trades, leveraged
            )
        )
        rows.append(
            _result_row(
                "technical_leveraged",
                window,
                overlay,
                overlay_eq,
                overlay_trades,
                leveraged,
            )
        )

    if args.include_operational:
        macro_df = load_macro_data(period="5y") if settings.use_ai_score else None
        for label, active_settings, ticker_data in (
            ("operational_core", replace(settings, allow_leveraged_etfs=False), core_data),
            ("operational_leveraged", replace(settings, allow_leveraged_etfs=True), expanded_data),
        ):
            kwargs = portfolio_backtest_kwargs(
                active_settings,
                ticker_data=ticker_data,
                benchmark_df=(
                    loaded[active_settings.market_regime_ticker]
                    if active_settings.market_regime_filter_enabled
                    else None
                ),
                relative_strength_benchmark_df=(
                    loaded[active_settings.relative_strength_benchmark_ticker]
                    if active_settings.relative_strength_filter_enabled
                    else None
                ),
                vix_df=vix_df,
                macro_df=macro_df,
                evaluation_start_date=windows["6m"],
                evaluation_end_date=end,
            )
            result, equity, trades = run_portfolio_backtest(**kwargs)
            rows.append(
                _result_row(label, "6m_oos", result, equity, trades, leveraged)
            )

    summary = pd.DataFrame(rows)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary.to_csv(OUTPUT_DIR / "summary.csv", index=False)
    print(f"end={end.date()} core={len(core)} leveraged={len(leveraged)} expanded={len(expanded)}")
    print(summary.to_string(index=False))
    print(f"saved={OUTPUT_DIR / 'summary.csv'}")


if __name__ == "__main__":
    main()
