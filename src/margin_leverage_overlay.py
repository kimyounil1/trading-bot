"""Daily margin overlays for regime-conditional backtest comparisons."""

from __future__ import annotations

import pandas as pd

from src.strategy import build_market_regime_frame


def simulate_conditional_margin_overlay(
    equity_df: pd.DataFrame,
    benchmark_df: pd.DataFrame,
    *,
    vix_df: pd.DataFrame | None = None,
    max_vix: float | None = None,
    bull_leverage_factor: float = 2.0,
    defensive_leverage_factor: float = 1.0,
    regime_ma_fast: int = 50,
    regime_ma_slow: int = 200,
    annual_margin_interest_rate: float = 0.0625,
    transition_cost_pct: float = 0.001,
) -> pd.DataFrame:
    """Apply bull-only leverage to an existing 1x portfolio equity curve.

    The regime observed at day T close controls exposure for T+1, avoiding
    same-close look-ahead. Normal strategy trading costs are already present
    in ``daily_return``; ``transition_cost_pct`` covers only leverage changes.
    """
    required = {"date", "equity", "daily_return", "gross_exposure_pct"}
    missing = required - set(equity_df.columns)
    if missing:
        raise ValueError(f"equity_df missing required columns: {sorted(missing)}")
    if bull_leverage_factor < 1.0 or defensive_leverage_factor < 1.0:
        raise ValueError("leverage factors must be at least 1.0")
    if defensive_leverage_factor > bull_leverage_factor:
        raise ValueError("defensive leverage must not exceed bull leverage")
    if annual_margin_interest_rate < 0 or transition_cost_pct < 0:
        raise ValueError("interest rate and transition cost must be non-negative")
    if max_vix is not None and max_vix <= 0:
        raise ValueError("max_vix must be positive")
    if max_vix is not None and (vix_df is None or vix_df.empty):
        raise ValueError("vix_df is required when max_vix is set")

    frame = equity_df.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame = frame.sort_values("date").reset_index(drop=True)

    regime = build_market_regime_frame(
        benchmark_df,
        ma_fast=regime_ma_fast,
        ma_slow=regime_ma_slow,
    ).copy()
    regime["date"] = pd.to_datetime(regime["date"])
    frame = frame.merge(regime, on="date", how="left")
    observed_bull = frame["market_regime_bullish"].fillna(False).astype(bool)
    if max_vix is not None and vix_df is not None:
        vix = vix_df.copy()
        vix["date"] = pd.to_datetime(vix["date"])
        vix_close_col = "adj_close" if "adj_close" in vix.columns else "close"
        vix = vix[["date", vix_close_col]].rename(
            columns={vix_close_col: "vix_close"}
        )
        frame = frame.merge(vix, on="date", how="left")
        observed_bull = observed_bull & (
            pd.to_numeric(frame["vix_close"], errors="coerce") < float(max_vix)
        ).fillna(False)
    frame["leverage_regime_bullish"] = observed_bull.shift(
        1, fill_value=False
    )
    frame["target_leverage_factor"] = frame["leverage_regime_bullish"].map(
        {True: float(bull_leverage_factor), False: float(defensive_leverage_factor)}
    )

    base_return = pd.to_numeric(frame["daily_return"], errors="coerce").fillna(0.0)
    base_exposure = pd.to_numeric(
        frame["gross_exposure_pct"], errors="coerce"
    ).fillna(0.0)
    exposure_for_return = base_exposure.shift(1).fillna(base_exposure)
    factor = frame["target_leverage_factor"]
    previous_factor = factor.shift(1).fillna(factor)

    frame["target_gross_exposure_pct"] = factor * exposure_for_return
    frame["borrowed_exposure_pct"] = (
        frame["target_gross_exposure_pct"] - 1.0
    ).clip(lower=0.0)
    frame["transition_turnover_pct"] = (
        (factor - previous_factor).abs() * exposure_for_return
    )
    frame["transition_cost_return"] = (
        frame["transition_turnover_pct"] * transition_cost_pct
    )

    elapsed_days = frame["date"].diff().dt.days.fillna(1).clip(lower=1)
    frame["margin_interest_return"] = (
        frame["borrowed_exposure_pct"]
        * annual_margin_interest_rate
        * elapsed_days
        / 360.0
    )
    frame["conditional_daily_return"] = (
        factor * base_return
        - frame["transition_cost_return"]
        - frame["margin_interest_return"]
    )
    if (frame["conditional_daily_return"] <= -1.0).any():
        raise ValueError("conditional leverage overlay reached liquidation")

    initial_equity = float(frame["equity"].iloc[0])
    frame["conditional_equity"] = (
        (1.0 + frame["conditional_daily_return"]).cumprod() * initial_equity
    )
    prior_equity = frame["conditional_equity"].shift(1).fillna(initial_equity)
    frame["margin_interest_paid"] = prior_equity * frame["margin_interest_return"]
    frame["cumulative_margin_interest"] = frame["margin_interest_paid"].cumsum()
    frame["running_max"] = frame["conditional_equity"].cummax()
    frame["drawdown"] = (
        frame["conditional_equity"] / frame["running_max"] - 1.0
    )
    return frame


def summarize_conditional_margin_overlay(
    frame: pd.DataFrame,
    *,
    start: pd.Timestamp,
) -> dict[str, float | str]:
    window = frame[pd.to_datetime(frame["date"]) >= pd.Timestamp(start)].copy()
    if window.empty:
        raise ValueError("No conditional overlay rows in requested window")
    daily = pd.to_numeric(
        window["conditional_daily_return"], errors="coerce"
    ).fillna(0.0)
    curve = (1.0 + daily).cumprod()
    drawdown = curve / curve.cummax() - 1.0
    std = float(daily.std())
    prior = frame[pd.to_datetime(frame["date"]) < pd.Timestamp(start)]
    interest_before = (
        float(prior["cumulative_margin_interest"].iloc[-1])
        if not prior.empty
        else 0.0
    )
    return {
        "total_return": float(curve.iloc[-1] - 1.0),
        "max_drawdown": float(drawdown.min()),
        "sharpe_ratio": (
            float(daily.mean() / std * (252**0.5)) if std > 1e-10 else 0.0
        ),
        "avg_gross_exposure": float(window["target_gross_exposure_pct"].mean()),
        "max_gross_exposure": float(window["target_gross_exposure_pct"].max()),
        "leveraged_days_pct": float(
            (window["target_leverage_factor"] > 1.0).mean()
        ),
        "margin_interest_paid": float(
            window["cumulative_margin_interest"].iloc[-1] - interest_before
        ),
        "start": pd.Timestamp(window["date"].iloc[0]).date().isoformat(),
        "end": pd.Timestamp(window["date"].iloc[-1]).date().isoformat(),
    }
