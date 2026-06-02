"""Refresh champion-model buy/exit threshold grid without full retrain."""

from __future__ import annotations

import argparse
import json

from src.data_loader import load_price_data_batch
from src.features import MAX_FEATURE_LOOKBACK
from src.macro_loader import load_macro_data
from src.settings import load_settings
from src.train_ai_model import (
    VIX_TICKER,
    _run_threshold_retune,
    _write_threshold_retune_report,
)

MIN_BACKTEST_ROWS = MAX_FEATURE_LOOKBACK + 20


def _filter_usable_ticker_data(
    ticker_data: dict,
    settings,
) -> dict:
    """Drop symbols with insufficient history so feature/backtest steps do not fail."""
    reserved = {
        str(VIX_TICKER).upper(),
        "SPY",
        str(getattr(settings, "market_regime_ticker", "") or "").upper(),
        str(getattr(settings, "relative_strength_benchmark_ticker", "") or "").upper(),
    }
    reserved.discard("")

    filtered: dict = {}
    for ticker, frame in ticker_data.items():
        key = str(ticker).upper()
        if frame is None or frame.empty:
            if key in reserved:
                raise ValueError(f"Required benchmark/context ticker {ticker} has no price data")
            continue
        if key not in reserved and len(frame) < MIN_BACKTEST_ROWS:
            continue
        filtered[ticker] = frame
    if not any(k for k in filtered if str(k).upper() not in reserved):
        raise ValueError("No tradable tickers with sufficient history for threshold retune")
    return filtered


def run_threshold_retune(*, period: str = "5y") -> dict:
    settings = load_settings()
    tickers = list(dict.fromkeys(list(settings.tickers) + [VIX_TICKER, "SPY"]))
    ticker_data = load_price_data_batch(tickers, period=period)
    vix_df = ticker_data.pop(VIX_TICKER, None)
    ticker_data = _filter_usable_ticker_data(ticker_data, settings)
    macro_df = load_macro_data(period=period)
    if macro_df is not None and macro_df.empty:
        macro_df = None
    report, results_df = _run_threshold_retune(
        settings=settings,
        ticker_data=ticker_data,
        vix_df=vix_df,
        macro_df=macro_df,
    )
    _write_threshold_retune_report(report, results_df)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run buy/exit threshold retune on cached data")
    parser.add_argument("--period", default="5y")
    args = parser.parse_args()
    report = run_threshold_retune(period=args.period)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
