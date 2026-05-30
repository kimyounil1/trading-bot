"""Holdout window helpers for retrain portfolio promotion (no ML deps)."""

from __future__ import annotations

import pandas as pd

PORTFOLIO_HOLDOUT_MONTHS = 6


def portfolio_holdout_window(
    ticker_data: dict[str, pd.DataFrame],
    *,
    months: int = PORTFOLIO_HOLDOUT_MONTHS,
) -> tuple[pd.Timestamp, pd.Timestamp]:
    latest_dates = []
    for df in ticker_data.values():
        if df is None or df.empty or "date" not in df.columns:
            continue
        series = pd.to_datetime(df["date"], errors="coerce").dropna()
        if not series.empty:
            latest_dates.append(series.max())
    if not latest_dates:
        raise ValueError("No valid dates found in ticker_data")
    eval_end = max(latest_dates)
    eval_start = eval_end - pd.DateOffset(months=months)
    return eval_start, eval_end


def exclude_holdout_from_ticker_data(
    ticker_data: dict[str, pd.DataFrame],
    holdout_start: pd.Timestamp,
) -> dict[str, pd.DataFrame]:
    """Rows with date >= holdout_start are removed (challenger training set)."""
    out: dict[str, pd.DataFrame] = {}
    for ticker, df in ticker_data.items():
        if df is None or df.empty or "date" not in df.columns:
            continue
        frame = df.copy()
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
        out[ticker] = frame[frame["date"] < holdout_start].reset_index(drop=True)
    return out


def slice_ticker_data_to_holdout(
    ticker_data: dict[str, pd.DataFrame],
    holdout_start: pd.Timestamp,
    holdout_end: pd.Timestamp,
) -> dict[str, pd.DataFrame]:
    """Rows within [holdout_start, holdout_end] for portfolio OOS scoring."""
    out: dict[str, pd.DataFrame] = {}
    for ticker, df in ticker_data.items():
        if df is None or df.empty or "date" not in df.columns:
            continue
        frame = df.copy()
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
        mask = (frame["date"] >= holdout_start) & (frame["date"] <= holdout_end)
        sliced = frame.loc[mask].reset_index(drop=True)
        if not sliced.empty:
            out[ticker] = sliced
    return out
