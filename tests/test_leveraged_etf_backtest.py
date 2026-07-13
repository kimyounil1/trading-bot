import numpy as np
import pandas as pd

from src.portfolio_backtester import run_portfolio_backtest


def _price_frame(start: float, end: float, rows: int = 260) -> pd.DataFrame:
    close = np.linspace(start, end, rows)
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


def test_leveraged_etfs_are_blocked_when_disabled() -> None:
    _, equity, _ = run_portfolio_backtest(
        ticker_data={"SOXL": _price_frame(10.0, 30.0)},
        ma_fast=30,
        ma_slow=200,
        rsi_buy_limit=101.0,
        allow_leveraged_etfs=False,
    )

    assert equity["positions_count"].max() == 0


def test_leveraged_etf_backtest_caps_count_and_position_size() -> None:
    data = {
        "SOXL": _price_frame(10.0, 30.0),
        "SOXS": _price_frame(5.0, 15.0),
    }
    _, equity, _ = run_portfolio_backtest(
        ticker_data=data,
        initial_cash=10_000.0,
        max_positions=3,
        target_position_pct=0.30,
        ma_fast=30,
        ma_slow=200,
        rsi_buy_limit=101.0,
        allow_leveraged_etfs=True,
        leveraged_etf_allowlist=["SOXL"],
        max_leveraged_etf_positions=1,
        max_effective_leverage_exposure_pct=1.25,
    )

    held_counts = equity["open_symbols"].map(
        lambda value: len({x for x in str(value).split(",") if x in {"SOXL", "SOXS"}})
    )
    assert held_counts.max() == 1
    assert equity["open_symbols"].str.contains("SOXS").sum() == 0
    first_invested = equity[equity["positions_count"] > 0].iloc[0]
    assert first_invested["positions_value"] <= 1_010.0


def test_leveraged_etf_backtest_applies_vix_block() -> None:
    prices = _price_frame(10.0, 30.0)
    vix = prices[["date"]].copy()
    vix["close"] = 35.0

    _, equity, _ = run_portfolio_backtest(
        ticker_data={"SOXL": prices},
        vix_df=vix,
        ma_fast=30,
        ma_slow=200,
        rsi_buy_limit=101.0,
        allow_leveraged_etfs=True,
        leveraged_etf_allowlist=["SOXL"],
        block_leveraged_etfs_vix_above=28.0,
    )

    assert equity["positions_count"].max() == 0
