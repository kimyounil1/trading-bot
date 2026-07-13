import numpy as np
import pandas as pd
import pytest

from src.portfolio_backtester import run_portfolio_backtest


def _rising_price_frame(rows: int = 260) -> pd.DataFrame:
    close = np.linspace(100.0, 160.0, rows)
    return pd.DataFrame(
        {
            "date": pd.bdate_range("2025-01-02", periods=rows),
            "open": close,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "adj_close": close,
            "volume": np.full(rows, 1_000_000),
        }
    )


def _run(leverage_factor: float, margin_rate: float):
    return run_portfolio_backtest(
        ticker_data={"AAPL": _rising_price_frame()},
        initial_cash=10_000.0,
        max_positions=1,
        target_position_pct=0.75,
        transaction_cost_pct=0.0,
        ma_fast=5,
        ma_slow=20,
        rsi_buy_limit=101.0,
        allow_leveraged_etfs=False,
        max_effective_leverage_exposure_pct=leverage_factor,
        leverage_factor=leverage_factor,
        annual_margin_interest_rate=margin_rate,
    )


def test_two_x_margin_increases_rising_market_return_and_uses_debt() -> None:
    baseline, baseline_equity, _ = _run(1.0, 0.0625)
    leveraged, equity, _ = _run(2.0, 0.0625)

    assert leveraged.total_return > baseline.total_return
    assert baseline_equity["borrowed_cash"].max() < 1e-8
    assert equity["borrowed_cash"].max() > 0
    assert equity["gross_exposure_pct"].max() <= 2.001


def test_margin_interest_reduces_leveraged_return() -> None:
    without_interest, _, _ = _run(2.0, 0.0)
    with_interest, equity, _ = _run(2.0, 0.0625)

    assert with_interest.final_equity < without_interest.final_equity
    assert equity["cumulative_margin_interest"].iloc[-1] > 0


def test_margin_leverage_rejects_values_below_one() -> None:
    with pytest.raises(ValueError, match="at least 1.0"):
        _run(0.9, 0.0)
