"""Regime-adaptive stop-loss / trailing-stop policy from SPY 20d return."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

DEFAULT_BULL_SPY_20D_THRESHOLD = 0.03
DEFAULT_STRESS_SPY_20D_THRESHOLD = -0.08


@dataclass(frozen=True)
class RegimeStopProfile:
    bull_stop_loss_pct: float = 0.07
    bull_trailing_stop_pct: float = 0.18
    bear_stop_loss_pct: float = 0.04
    bear_trailing_stop_pct: float = 0.10
    stress_stop_loss_pct: float = 0.03
    stress_trailing_stop_pct: float = 0.08
    bull_spy_20d_threshold: float = DEFAULT_BULL_SPY_20D_THRESHOLD
    stress_spy_20d_threshold: float = DEFAULT_STRESS_SPY_20D_THRESHOLD


STANDARD_REGIME_STOP_PROFILE = RegimeStopProfile()
CONSERVATIVE_REGIME_STOP_PROFILE = RegimeStopProfile(
    bull_stop_loss_pct=0.05,
    bull_trailing_stop_pct=0.15,
    bear_stop_loss_pct=0.035,
    bear_trailing_stop_pct=0.08,
    stress_stop_loss_pct=0.025,
    stress_trailing_stop_pct=0.06,
)

# SPY 20d >= 0 → baseline 5%/12%; SPY 20d < 0 → tight 3%/10% (no separate stress tier)
BEAR_ONLY_TIGHT_STOP_PROFILE = RegimeStopProfile(
    bull_stop_loss_pct=0.05,
    bull_trailing_stop_pct=0.12,
    bear_stop_loss_pct=0.03,
    bear_trailing_stop_pct=0.10,
    stress_stop_loss_pct=0.03,
    stress_trailing_stop_pct=0.10,
    bull_spy_20d_threshold=0.0,
    stress_spy_20d_threshold=-0.999,
)


def spy_return_lookback(
    spy_df: pd.DataFrame,
    as_of: pd.Timestamp,
    lookback_days: int = 20,
) -> float | None:
    if spy_df is None or spy_df.empty or lookback_days <= 0:
        return None
    df = spy_df.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    col = "adj_close" if "adj_close" in df.columns else "close"
    df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=[col]).sort_values("date")
    as_of = pd.Timestamp(as_of).normalize()
    window = df[df["date"] <= as_of]
    if len(window) < lookback_days + 1:
        return None
    tail = window.tail(lookback_days + 1)
    start = float(tail.iloc[0][col])
    end = float(tail.iloc[-1][col])
    if start <= 0:
        return None
    return end / start - 1.0


def classify_spy_regime(
    spy_20d_return: float | None,
    *,
    bull_threshold: float = DEFAULT_BULL_SPY_20D_THRESHOLD,
    stress_threshold: float = DEFAULT_STRESS_SPY_20D_THRESHOLD,
) -> str:
    if spy_20d_return is None:
        return "unknown"
    if spy_20d_return >= bull_threshold:
        return "bull"
    if spy_20d_return <= stress_threshold:
        return "stress"
    return "bear"


def resolve_regime_stop_params(
    spy_df: pd.DataFrame | None,
    as_of: pd.Timestamp,
    *,
    fallback_stop_loss_pct: float,
    fallback_trailing_stop_pct: float,
    enabled: bool,
    profile: RegimeStopProfile | None = None,
) -> tuple[float, float, str]:
    """Return (stop_loss_pct, trailing_stop_pct, regime_label)."""
    if not enabled or spy_df is None:
        return fallback_stop_loss_pct, fallback_trailing_stop_pct, "fixed"

    prof = profile or STANDARD_REGIME_STOP_PROFILE
    spy_20d = spy_return_lookback(spy_df, as_of, 20)
    regime = classify_spy_regime(
        spy_20d,
        bull_threshold=prof.bull_spy_20d_threshold,
        stress_threshold=prof.stress_spy_20d_threshold,
    )
    if regime == "bull":
        return prof.bull_stop_loss_pct, prof.bull_trailing_stop_pct, regime
    if regime == "stress":
        return prof.stress_stop_loss_pct, prof.stress_trailing_stop_pct, regime
    if regime == "bear":
        return prof.bear_stop_loss_pct, prof.bear_trailing_stop_pct, regime
    return fallback_stop_loss_pct, fallback_trailing_stop_pct, regime
