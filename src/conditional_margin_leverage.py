"""Resolve the paper margin factor from lagged SPY trend and VIX risk."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class ConditionalMarginLeverageDecision:
    leverage_factor: float
    active: bool
    reason: str
    spy_ma_fast: float | None = None
    spy_ma_slow: float | None = None
    vix_close: float | None = None


def _close_series(frame: pd.DataFrame | None) -> pd.Series:
    if frame is None or frame.empty:
        return pd.Series(dtype=float)
    close_col = "adj_close" if "adj_close" in frame.columns else "close"
    if close_col not in frame.columns:
        return pd.Series(dtype=float)
    return pd.to_numeric(frame[close_col], errors="coerce").dropna()


def resolve_conditional_margin_leverage(
    settings: Any,
    *,
    spy_df: pd.DataFrame | None,
    vix_df: pd.DataFrame | None,
) -> ConditionalMarginLeverageDecision:
    defensive = float(
        getattr(settings, "conditional_margin_leverage_defensive_factor", 1.0)
    )
    if not bool(getattr(settings, "conditional_margin_leverage_enabled", False)):
        factor = float(getattr(settings, "leverage_factor", defensive))
        return ConditionalMarginLeverageDecision(
            factor,
            factor > defensive,
            "conditional margin leverage disabled",
        )

    bull = float(getattr(settings, "conditional_margin_leverage_bull_factor", 2.0))
    ma_fast = int(getattr(settings, "market_regime_ma_fast", 50))
    ma_slow = int(getattr(settings, "market_regime_ma_slow", 200))
    vix_max = float(getattr(settings, "conditional_margin_leverage_vix_max", 22.0))
    spy_close = _close_series(spy_df)
    vix_close_series = _close_series(vix_df)
    if len(spy_close) < ma_slow or vix_close_series.empty:
        return ConditionalMarginLeverageDecision(
            defensive,
            False,
            "conditional leverage fail-closed: missing SPY/VIX history",
        )

    fast_value = float(spy_close.rolling(ma_fast).mean().iloc[-1])
    slow_value = float(spy_close.rolling(ma_slow).mean().iloc[-1])
    vix_close = float(vix_close_series.iloc[-1])
    active = fast_value > slow_value and vix_close < vix_max
    factor = bull if active else defensive
    reason = (
        f"SPY SMA{ma_fast}={fast_value:.2f} "
        f"{'>' if fast_value > slow_value else '<='} "
        f"SMA{ma_slow}={slow_value:.2f}; "
        f"VIX={vix_close:.2f} {'<' if vix_close < vix_max else '>='} {vix_max:.2f}"
    )
    return ConditionalMarginLeverageDecision(
        factor,
        active,
        reason,
        spy_ma_fast=fast_value,
        spy_ma_slow=slow_value,
        vix_close=vix_close,
    )
