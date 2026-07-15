from types import SimpleNamespace

import numpy as np
import pandas as pd

from src.rank_quality_risk import (
    build_rank_quality_risk_overrides,
    evaluate_rank_quality_risk,
)
from src.portfolio_backtest_settings import portfolio_backtest_kwargs
from src.settings import StrategySettings


def _settings(**overrides):
    values = {
        "rank_quality_risk_enabled": True,
        "rank_quality_drawdown_threshold": 0.25,
        "rank_quality_one_bad_multiplier": 0.5,
        "rank_quality_two_bad_multiplier": 0.25,
        "rank_quality_block_leverage_when_both_bad": True,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _frame(closes: list[float], *, append_partial: bool = False) -> pd.DataFrame:
    dates = pd.bdate_range("2025-01-02", periods=len(closes))
    frame = pd.DataFrame({"date": dates, "close": closes})
    if append_partial:
        frame.loc[len(frame)] = [dates[-1] + pd.offsets.BDay(1), np.nan]
    return frame


def test_quality_risk_uses_expected_strict_multipliers() -> None:
    high_drawdown_only = [200.0] + [100.0] * 231 + [140.0] * 20
    both_bad = [200.0] * 100 + [100.0] * 152

    one_bad = evaluate_rank_quality_risk(_frame(high_drawdown_only), _settings())
    both = evaluate_rank_quality_risk(_frame(both_bad), _settings())

    assert one_bad.high_drawdown is True
    assert one_bad.downtrend is False
    assert one_bad.notional_multiplier == 0.5
    assert one_bad.allow_leveraged is True
    assert both.high_drawdown is True
    assert both.downtrend is True
    assert both.notional_multiplier == 0.25
    assert both.allow_leveraged is False


def test_quality_risk_ignores_incomplete_latest_bar() -> None:
    closes = [200.0] * 100 + [100.0] * 152

    complete = evaluate_rank_quality_risk(_frame(closes), _settings())
    with_partial = evaluate_rank_quality_risk(
        _frame(closes, append_partial=True),
        _settings(),
    )

    assert with_partial == complete


def test_backtest_overrides_match_latest_live_decision() -> None:
    ticker_frame = _frame([200.0] + [100.0] * 231 + [140.0] * 20)
    settings = _settings()

    live = evaluate_rank_quality_risk(ticker_frame, settings)
    history = build_rank_quality_risk_overrides({"aapl": ticker_frame}, settings)
    latest = history[pd.Timestamp(ticker_frame["date"].iloc[-1]).normalize()]["AAPL"]

    assert latest == {
        "notional_multiplier": live.notional_multiplier,
        "allow_leveraged": live.allow_leveraged,
    }


def test_disabled_quality_risk_is_noop() -> None:
    decision = evaluate_rank_quality_risk(
        _frame([200.0] * 100 + [100.0] * 152),
        _settings(rank_quality_risk_enabled=False),
    )

    assert decision.notional_multiplier == 1.0
    assert decision.allow_leveraged is True
    assert build_rank_quality_risk_overrides(
        {"AAPL": _frame([100.0] * 252)},
        _settings(rank_quality_risk_enabled=False),
    ) == {}


def test_portfolio_backtest_settings_builds_quality_overrides_automatically() -> None:
    ticker_frame = _frame([200.0] * 100 + [100.0] * 152)
    settings = StrategySettings(
        tickers=["AAPL"],
        rank_quality_risk_enabled=True,
    )

    kwargs = portfolio_backtest_kwargs(
        settings,
        ticker_data={"AAPL": ticker_frame},
    )
    latest = kwargs["entry_risk_overrides_by_date"][
        pd.Timestamp(ticker_frame["date"].iloc[-1]).normalize()
    ]["AAPL"]

    assert latest == {"notional_multiplier": 0.25, "allow_leveraged": False}
