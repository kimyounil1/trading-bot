#!/usr/bin/env python3
"""Compare ordinary-stock portfolio returns under controlled margin leverage."""

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
from src.instrument_meta import get_instrument
from src.macro_loader import load_macro_data
from src.portfolio_backtest_settings import portfolio_backtest_kwargs
from src.portfolio_backtester import run_portfolio_backtest
from src.settings import load_settings


DEFAULT_OUTPUT_DIR = Path("logs/margin_leverage_validation_20260713")


def _window_row(
    *,
    factor: float,
    label: str,
    equity: pd.DataFrame,
    trades: pd.DataFrame,
    start: pd.Timestamp,
    annual_margin_rate: float,
) -> dict:
    frame = equity[pd.to_datetime(equity["date"]) >= start].copy()
    if frame.empty:
        raise ValueError(f"No equity rows for {label}")
    daily = pd.to_numeric(frame["daily_return"], errors="coerce").fillna(0.0)
    curve = (1.0 + daily).cumprod()
    drawdown = curve / curve.cummax() - 1.0
    std = float(daily.std())
    sharpe = float(daily.mean() / std * (252**0.5)) if std > 1e-10 else 0.0

    trade_count = 0
    win_rate = 0.0
    if not trades.empty:
        exits = trades[pd.to_datetime(trades["exit_date"]) >= start]
        trade_count = int(len(exits))
        if trade_count:
            win_rate = float((exits["return_pct"] > 0).mean())

    interest = pd.to_numeric(
        frame["cumulative_margin_interest"], errors="coerce"
    ).fillna(0.0)
    interest_before = 0.0
    prior = equity[pd.to_datetime(equity["date"]) < start]
    if not prior.empty:
        interest_before = float(prior["cumulative_margin_interest"].iloc[-1])

    return {
        "window": label,
        "leverage_factor": factor,
        "annual_margin_rate": annual_margin_rate,
        "total_return": float(curve.iloc[-1] - 1.0),
        "max_drawdown": float(drawdown.min()),
        "sharpe_ratio": sharpe,
        "trades": trade_count,
        "win_rate": win_rate,
        "avg_gross_exposure": float(frame["gross_exposure_pct"].mean()),
        "max_gross_exposure": float(frame["gross_exposure_pct"].max()),
        "max_borrowed_cash": float(frame["borrowed_cash"].max()),
        "margin_interest_paid": float(interest.iloc[-1] - interest_before),
        "start": pd.Timestamp(frame["date"].iloc[0]).date().isoformat(),
        "end": pd.Timestamp(frame["date"].iloc[-1]).date().isoformat(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--factors",
        default="1.0,1.25,1.5,2.0",
        help="Comma-separated gross leverage factors",
    )
    parser.add_argument("--margin-rate", type=float, default=0.0625)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--force-refresh", action="store_true")
    parser.add_argument(
        "--operational",
        action="store_true",
        help="Include the active AI/rank gates; intended for shorter 1y runs",
    )
    args = parser.parse_args()

    factors = [float(value) for value in args.factors.split(",")]
    settings = load_settings()
    tickers = [
        ticker
        for ticker in settings.tickers
        if not get_instrument(ticker).is_leveraged_etf
    ]
    auxiliary_tickers = [
        settings.market_regime_ticker,
        settings.relative_strength_benchmark_ticker,
    ]
    loaded = load_price_data_batch(
        list(dict.fromkeys([*tickers, *auxiliary_tickers, "^VIX"])),
        period="5y",
        force_refresh=args.force_refresh,
    )
    ticker_data = {ticker: loaded[ticker] for ticker in tickers}
    vix_df = loaded["^VIX"]
    end = min(pd.to_datetime(frame["date"]).max() for frame in ticker_data.values())
    starts = {
        "6m": end - pd.DateOffset(months=6),
        "1y": end - pd.DateOffset(years=1),
        "4y": end - pd.DateOffset(years=4),
    }

    if args.operational:
        active_settings = replace(settings, allow_leveraged_etfs=False)
        macro_df = load_macro_data(period="5y") if settings.use_ai_score else None
        common = portfolio_backtest_kwargs(
            active_settings,
            ticker_data=ticker_data,
            benchmark_df=(
                loaded[settings.market_regime_ticker]
                if settings.market_regime_filter_enabled
                else None
            ),
            relative_strength_benchmark_df=(
                loaded[settings.relative_strength_benchmark_ticker]
                if settings.relative_strength_filter_enabled
                else None
            ),
            vix_df=vix_df,
            macro_df=macro_df,
            evaluation_start_date=starts["1y"],
            evaluation_end_date=end,
            initial_cash=10_000.0,
            transaction_cost_pct=0.001,
        )
        output_windows = {key: starts[key] for key in ("6m", "1y")}
        output_prefix = "operational_"
    else:
        common = {
            "ticker_data": ticker_data,
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
            "allow_leveraged_etfs": False,
            "evaluation_start_date": starts["4y"],
            "evaluation_end_date": end,
        }
        output_windows = starts
        output_prefix = ""

    args.outdir.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for factor in factors:
        run_kwargs = {
            **common,
            "leverage_factor": factor,
            "max_effective_leverage_exposure_pct": factor,
            "annual_margin_interest_rate": args.margin_rate,
        }
        result, equity, trades = run_portfolio_backtest(**run_kwargs)
        equity.to_csv(
            args.outdir / f"{output_prefix}equity_{factor:.2f}x.csv",
            index=False,
        )
        trades.to_csv(
            args.outdir / f"{output_prefix}trades_{factor:.2f}x.csv",
            index=False,
        )
        for label, start in output_windows.items():
            rows.append(
                _window_row(
                    factor=factor,
                    label=label,
                    equity=equity,
                    trades=trades,
                    start=start,
                    annual_margin_rate=args.margin_rate,
                )
            )
        print(
            f"factor={factor:.2f} final={result.final_equity:.2f} "
            f"return={result.total_return:.2%} mdd={result.max_drawdown:.2%}"
        )

    summary = pd.DataFrame(rows).sort_values(["window", "leverage_factor"])
    summary_name = "operational_summary.csv" if args.operational else "summary.csv"
    summary.to_csv(args.outdir / summary_name, index=False)
    print(f"end={end.date()} tickers={len(tickers)} margin_rate={args.margin_rate:.2%}")
    print(summary.to_string(index=False))
    print(f"saved={args.outdir / summary_name}")


if __name__ == "__main__":
    main()
