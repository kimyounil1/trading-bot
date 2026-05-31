"""LLM backtest impact replay ([AGY])."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

from src.llm_backtest_impact_report import (
    build_llm_backtest_impact_report,
    validate_llm_backtest_impact_report,
)

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "portfolio_backtest"


def test_llm_backtest_impact_blocks_losing_trade(tmp_path: Path):
    trades = pd.DataFrame(
        [
            {
                "ticker": "BAD",
                "entry_date": "2025-06-01",
                "exit_date": "2025-06-10",
                "entry_price": 10,
                "exit_price": 8,
                "qty": 100,
                "cost_basis": 1000,
                "exit_value": 800,
                "return_pct": -0.2,
                "exit_reason": "STOP_LOSS",
            },
            {
                "ticker": "GOOD",
                "entry_date": "2025-06-02",
                "exit_date": "2025-06-10",
                "entry_price": 10,
                "exit_price": 12,
                "qty": 100,
                "cost_basis": 1000,
                "exit_value": 1300,
                "return_pct": 0.3,
                "exit_reason": "TAKE_PROFIT",
            },
        ]
    )
    summary = pd.DataFrame(
        [
            {
                "initial_cash": 10000,
                "final_equity": 10100,
                "total_return": 0.01,
                "benchmark_return": 0.05,
                "max_drawdown": -0.05,
                "sharpe_ratio": 1.0,
                "trades": 2,
                "win_rate": 0.5,
            }
        ]
    )
    bt = tmp_path / "bt"
    bt.mkdir()
    trades.to_csv(bt / "portfolio_trades.csv", index=False)
    summary.to_csv(bt / "portfolio_summary.csv", index=False)

    settings = SimpleNamespace(
        news_sentiment_enabled=False,
        llm_cache_enabled=True,
        llm_degraded_mode="PASS",
    )

    def fake_eval(ticker, settings=None, as_of_date=None, cache_only=False):
        if ticker == "BAD":
            return False, "LLM Reject test"
        return True, "approved"

    with patch("src.llm_backtest_impact_report.evaluate_ticker_consensus", side_effect=fake_eval):
        report = build_llm_backtest_impact_report(bt, settings=settings, cache_only=True)

    validate_llm_backtest_impact_report(report)
    assert report["with_live_filters"]["blocked_trades"] == 1
    assert report["trade_level"]["blocked_losses_avoided"] > 0
    assert report["with_live_filters"]["adjusted_realized_pnl_sum"] == 300.0
    assert report["trade_level"]["llm_reject_count"] == 1
