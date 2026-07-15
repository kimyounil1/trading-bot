"""Shared Rank-AI entry risk overlay for live trading and backtests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class RankQualityRiskDecision:
    notional_multiplier: float
    allow_leveraged: bool
    high_drawdown: bool
    downtrend: bool
    close: float | None
    high_252: float | None
    ma20: float | None
    ma200: float | None
    market_date: str | None
    reason: str


def _completed_close_series(frame: pd.DataFrame) -> pd.Series:
    """Return sorted, unique, completed daily closes indexed by date."""
    if frame is None or frame.empty:
        return pd.Series(dtype=float)
    close_col = "close" if "close" in frame.columns else "adj_close"
    if close_col not in frame.columns:
        return pd.Series(dtype=float)

    if "date" in frame.columns:
        dates = pd.to_datetime(frame["date"], errors="coerce")
    else:
        dates = pd.to_datetime(frame.index, errors="coerce")
    closes = pd.to_numeric(frame[close_col], errors="coerce")
    valid = dates.notna() & closes.notna() & np.isfinite(closes) & (closes > 0)
    series = pd.Series(
        closes.loc[valid].to_numpy(dtype=float),
        index=pd.DatetimeIndex(dates.loc[valid]).normalize(),
        dtype=float,
    )
    return series[~series.index.duplicated(keep="last")].sort_index()


def _setting(settings: Any, name: str, default: Any) -> Any:
    return getattr(settings, name, default)


def _decision_from_values(
    *,
    close: float | None,
    high_252: float | None,
    ma20: float | None,
    ma200: float | None,
    settings: Any,
    market_date: str | None = None,
) -> RankQualityRiskDecision:
    enabled = bool(_setting(settings, "rank_quality_risk_enabled", False))
    threshold = float(_setting(settings, "rank_quality_drawdown_threshold", 0.25))
    one_bad_multiplier = float(
        _setting(settings, "rank_quality_one_bad_multiplier", 0.5)
    )
    two_bad_multiplier = float(
        _setting(settings, "rank_quality_two_bad_multiplier", 0.25)
    )

    complete_high = high_252 is not None and np.isfinite(high_252) and high_252 > 0
    complete_trend = all(
        value is not None and np.isfinite(value) for value in (ma20, ma200)
    )
    complete_close = close is not None and np.isfinite(close) and close > 0
    high_drawdown = (
        not complete_close
        or not complete_high
        or float(close) / float(high_252) < 1.0 - threshold
    )
    downtrend = (
        not complete_trend
        or not complete_close
        or float(ma20) < float(ma200)
    )
    bad_count = int(high_drawdown) + int(downtrend)

    if not enabled:
        multiplier = 1.0
        allow_leveraged = True
        state = "disabled"
    elif bad_count == 0:
        multiplier = 1.0
        allow_leveraged = True
        state = "0/2 bad"
    elif bad_count == 1:
        multiplier = one_bad_multiplier
        allow_leveraged = True
        state = "1/2 bad"
    else:
        multiplier = two_bad_multiplier
        allow_leveraged = not bool(
            _setting(
                settings,
                "rank_quality_block_leverage_when_both_bad",
                True,
            )
        )
        state = "2/2 bad"

    flags = []
    if high_drawdown:
        flags.append("drawdown")
    if downtrend:
        flags.append("downtrend")
    flag_text = "+".join(flags) if flags else "quality-ok"
    return RankQualityRiskDecision(
        notional_multiplier=float(multiplier),
        allow_leveraged=allow_leveraged,
        high_drawdown=high_drawdown,
        downtrend=downtrend,
        close=float(close) if complete_close else None,
        high_252=float(high_252) if complete_high else None,
        ma20=float(ma20) if ma20 is not None and np.isfinite(ma20) else None,
        ma200=float(ma200) if ma200 is not None and np.isfinite(ma200) else None,
        market_date=market_date,
        reason=(
            f"rank quality risk {state}: {flag_text}, "
            f"size={float(multiplier):.2f}x, leveraged={allow_leveraged}"
        ),
    )


def evaluate_rank_quality_risk(
    frame: pd.DataFrame,
    settings: Any,
) -> RankQualityRiskDecision:
    """Evaluate the latest completed daily bar with no intraday partial row."""
    close = _completed_close_series(frame)
    if close.empty:
        return _decision_from_values(
            close=None,
            high_252=None,
            ma20=None,
            ma200=None,
            settings=settings,
            market_date=None,
        )
    return _decision_from_values(
        close=float(close.iloc[-1]),
        high_252=(
            float(close.iloc[-252:].max()) if len(close) >= 252 else None
        ),
        ma20=float(close.iloc[-20:].mean()) if len(close) >= 20 else None,
        ma200=float(close.iloc[-200:].mean()) if len(close) >= 200 else None,
        settings=settings,
        market_date=pd.Timestamp(close.index[-1]).date().isoformat(),
    )


def build_rank_quality_risk_overrides(
    ticker_data: dict[str, pd.DataFrame],
    settings: Any,
) -> dict[pd.Timestamp, dict[str, dict[str, Any]]]:
    """Build point-in-time entry overrides using only data known on each date."""
    if not bool(_setting(settings, "rank_quality_risk_enabled", False)):
        return {}

    overrides: dict[pd.Timestamp, dict[str, dict[str, Any]]] = {}
    for raw_ticker, frame in ticker_data.items():
        ticker = str(raw_ticker).strip().upper()
        close = _completed_close_series(frame)
        if close.empty:
            continue
        high_252 = close.rolling(252, min_periods=252).max()
        ma20 = close.rolling(20, min_periods=20).mean()
        ma200 = close.rolling(200, min_periods=200).mean()
        for date in close.index:
            decision = _decision_from_values(
                close=float(close.loc[date]),
                high_252=(
                    float(high_252.loc[date])
                    if pd.notna(high_252.loc[date])
                    else None
                ),
                ma20=float(ma20.loc[date]) if pd.notna(ma20.loc[date]) else None,
                ma200=(
                    float(ma200.loc[date]) if pd.notna(ma200.loc[date]) else None
                ),
                settings=settings,
                market_date=pd.Timestamp(date).date().isoformat(),
            )
            overrides.setdefault(pd.Timestamp(date).normalize(), {})[ticker] = {
                "notional_multiplier": decision.notional_multiplier,
                "allow_leveraged": decision.allow_leveraged,
            }
    return overrides
