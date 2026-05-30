"""Holdout slicing for retrain portfolio promotion ([Cursor] slice)."""

import pandas as pd

from src.retrain_holdout import (
    exclude_holdout_from_ticker_data,
    portfolio_holdout_window,
    slice_ticker_data_to_holdout,
)


def _frame(start: str, days: int) -> pd.DataFrame:
    dates = pd.date_range(start, periods=days, freq="B")
    return pd.DataFrame(
        {
            "date": dates,
            "open": 1.0,
            "high": 1.0,
            "low": 1.0,
            "close": 1.0,
            "volume": 100.0,
        }
    )


def test_holdout_window_and_slices_do_not_overlap():
    ticker_data = {"AAPL": _frame("2024-01-01", 400)}
    holdout_start, holdout_end = portfolio_holdout_window(ticker_data, months=6)
    fit = exclude_holdout_from_ticker_data(ticker_data, holdout_start)
    holdout = slice_ticker_data_to_holdout(ticker_data, holdout_start, holdout_end)

    fit_max = pd.to_datetime(fit["AAPL"]["date"]).max()
    holdout_min = pd.to_datetime(holdout["AAPL"]["date"]).min()
    assert fit_max < holdout_min
    assert holdout_end >= holdout_min
