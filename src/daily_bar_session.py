"""Daily bar session handling: drop incomplete intraday bars, freshness checks."""

from __future__ import annotations

import pandas as pd
from pandas.tseries.offsets import BDay


def to_session_date(value: str) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    if ts.tzinfo is not None:
        ts = ts.tz_convert("UTC").tz_localize(None)
    return ts.normalize()


def normalize_bar_dates(date_series: pd.Series) -> pd.Series:
    normalized = pd.to_datetime(date_series, errors="coerce").dropna()
    if normalized.empty:
        return normalized
    if getattr(normalized.dt, "tz", None) is not None:
        normalized = normalized.dt.tz_convert("UTC").dt.tz_localize(None)
    return normalized.dt.normalize()


def last_completed_bar_date(date_series: pd.Series, market_clock) -> pd.Timestamp | None:
    normalized = normalize_bar_dates(date_series)
    if normalized.empty:
        return None

    session_date = to_session_date(market_clock.timestamp)
    latest_bar_date = normalized.max()
    if market_clock.is_open and latest_bar_date >= session_date:
        completed = normalized[normalized < session_date]
        if completed.empty:
            return None
        return completed.max()
    return latest_bar_date


def drop_incomplete_session_bar(raw_df: pd.DataFrame, market_clock) -> pd.DataFrame:
    if raw_df is None or raw_df.empty or "date" not in raw_df.columns:
        return raw_df
    if not market_clock.is_open:
        return raw_df

    session_date = to_session_date(market_clock.timestamp)
    df = raw_df.copy()
    parsed = pd.to_datetime(df["date"], errors="coerce")
    if getattr(parsed.dt, "tz", None) is not None:
        parsed = parsed.dt.tz_convert("UTC").dt.tz_localize(None)
    parsed = parsed.dt.normalize()
    mask = parsed.notna() & (parsed < session_date)
    return df.loc[mask.to_numpy()].copy()


def check_price_frame_freshness(raw_df, market_clock) -> tuple[bool, str]:
    if raw_df is None or raw_df.empty:
        return False, "price data is empty"
    if "date" not in raw_df.columns:
        return False, "price data missing date column"

    date_series = pd.to_datetime(raw_df["date"], errors="coerce").dropna()
    if date_series.empty:
        return False, "price data has no valid dates"

    session_date = to_session_date(market_clock.timestamp)
    last_completed = last_completed_bar_date(date_series, market_clock)
    if last_completed is None:
        return (
            False,
            f"no completed daily bar before session (session={session_date.date()})",
        )

    stale_cutoff = (session_date - BDay(3)).normalize()
    if last_completed < stale_cutoff:
        return (
            False,
            f"stale price data (last_completed={last_completed.date()}, cutoff={stale_cutoff.date()})",
        )

    note = f"last_completed={last_completed.date()}"
    if market_clock.is_open:
        latest = normalize_bar_dates(date_series).max()
        if latest >= session_date:
            note += " (intraday bar excluded from signals)"
    return True, f"price data fresh ({note})"
