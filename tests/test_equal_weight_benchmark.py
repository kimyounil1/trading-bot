"""Equal-weight benchmark must not be NaN when RS filter is enabled."""

import pandas as pd

from src.portfolio_backtester import _build_equal_weight_benchmark_values, run_portfolio_backtest


def _synthetic_ticker(start: str, n: int, base: float) -> pd.DataFrame:
    dates = pd.bdate_range(start, periods=n)
    closes = [base * (1.001 ** i) for i in range(n)]
    return pd.DataFrame(
        {
            "date": dates,
            "open": closes,
            "high": [c * 1.01 for c in closes],
            "low": [c * 0.99 for c in closes],
            "close": closes,
            "volume": [1_000_000] * n,
        }
    )


def test_equal_weight_benchmark_values_not_nan():
    ticker_data = {
        "AAA": _synthetic_ticker("2024-01-02", 120, 100.0),
        "BBB": _synthetic_ticker("2024-01-02", 120, 50.0),
    }
    equity_dates = pd.bdate_range("2024-03-01", periods=60)
    values = _build_equal_weight_benchmark_values(equity_dates, ticker_data, 10_000.0)
    assert len(values) == len(equity_dates)
    assert all(pd.notna(v) and v > 0 for v in values)


def test_run_portfolio_backtest_benchmark_return_finite():
    ticker_data = {
        "AAA": _synthetic_ticker("2024-01-02", 150, 100.0),
        "BBB": _synthetic_ticker("2024-01-02", 150, 80.0),
    }
    spy = _synthetic_ticker("2024-01-02", 150, 400.0)
    result, eq, _ = run_portfolio_backtest(
        ticker_data=ticker_data,
        relative_strength_benchmark_df=spy,
        relative_strength_filter_enabled=True,
        relative_strength_lookback_days=5,
        relative_strength_min_excess_return=0.0,
        use_ai_score=False,
        max_positions=1,
        initial_cash=10_000.0,
        ma_fast=5,
        ma_slow=10,
    )
    assert result.benchmark_return == result.benchmark_return
    assert eq["benchmark_equity"].notna().all()
