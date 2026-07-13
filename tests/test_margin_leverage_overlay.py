import numpy as np
import pandas as pd

from src.margin_leverage_overlay import simulate_conditional_margin_overlay


def _equity_frame(rows: int = 260) -> pd.DataFrame:
    dates = pd.bdate_range("2025-01-02", periods=rows)
    daily = np.full(rows, 0.001)
    daily[0] = 0.0
    equity = 10_000.0 * np.cumprod(1.0 + daily)
    return pd.DataFrame(
        {
            "date": dates,
            "equity": equity,
            "daily_return": daily,
            "gross_exposure_pct": np.full(rows, 0.9),
        }
    )


def _benchmark(rows: int = 260) -> pd.DataFrame:
    dates = pd.bdate_range("2025-01-02", periods=rows)
    close = np.concatenate([np.full(200, 100.0), np.linspace(101.0, 180.0, rows - 200)])
    return pd.DataFrame({"date": dates, "close": close})


def test_conditional_overlay_uses_prior_day_regime_and_bull_leverage() -> None:
    result = simulate_conditional_margin_overlay(
        _equity_frame(),
        _benchmark(),
        regime_ma_fast=5,
        regime_ma_slow=20,
    )

    first_bull_observation = result.index[result["market_regime_bullish"]][0]
    assert result.loc[first_bull_observation, "target_leverage_factor"] == 1.0
    assert result.loc[first_bull_observation + 1, "target_leverage_factor"] == 2.0
    assert set(result["target_leverage_factor"]) == {1.0, 2.0}
    assert result["margin_interest_paid"].sum() > 0
    assert result["transition_cost_return"].sum() > 0


def test_conditional_overlay_outperforms_one_x_on_positive_bull_returns() -> None:
    base = _equity_frame()
    result = simulate_conditional_margin_overlay(
        base,
        _benchmark(),
        regime_ma_fast=5,
        regime_ma_slow=20,
        annual_margin_interest_rate=0.0,
    )

    assert result["conditional_equity"].iloc[-1] > base["equity"].iloc[-1]


def test_vix_threshold_blocks_leverage_on_high_vix_days() -> None:
    base = _equity_frame()
    vix = base[["date"]].copy()
    vix["close"] = 35.0
    result = simulate_conditional_margin_overlay(
        base,
        _benchmark(),
        vix_df=vix,
        max_vix=22.0,
        regime_ma_fast=5,
        regime_ma_slow=20,
    )

    assert set(result["target_leverage_factor"]) == {1.0}
