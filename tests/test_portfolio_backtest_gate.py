"""Threshold gate tests for portfolio backtest outputs ([AGY])."""

from pathlib import Path

import pandas as pd
import pytest

from src.portfolio_backtest_validation import (
    PortfolioBacktestThresholds,
    check_portfolio_backtest_thresholds,
    check_portfolio_summary_thresholds,
)


def _write_summary(path: Path, row: dict) -> None:
    pd.DataFrame([row]).to_csv(path, index=False)


def _write_minimal_bundle(dir_path: Path, summary_row: dict) -> None:
    dir_path.mkdir(parents=True, exist_ok=True)
    _write_summary(dir_path / "portfolio_summary.csv", summary_row)
    pd.DataFrame(
        [{"date": "2024-01-01", "equity": 10000.0, "cash": 10000.0, "positions_value": 0.0,
          "positions_count": 0, "open_symbols": "", "daily_return": 0.0,
          "running_max": 10000.0, "drawdown": 0.0, "benchmark_equity": 10000.0},
         {"date": "2024-01-02", "equity": 10100.0, "cash": 5000.0, "positions_value": 5100.0,
          "positions_count": 1, "open_symbols": "SPY", "daily_return": 0.01,
          "running_max": 10100.0, "drawdown": 0.0, "benchmark_equity": 10050.0}]
    ).to_csv(dir_path / "portfolio_equity.csv", index=False)
    pd.DataFrame(
        columns=[
            "ticker", "entry_date", "exit_date", "entry_price", "exit_price",
            "qty", "cost_basis", "exit_value", "return_pct", "exit_reason",
        ]
    ).to_csv(dir_path / "portfolio_trades.csv", index=False)


def test_summary_thresholds_pass_in_memory():
    summary = {
        "total_return": 0.10,
        "benchmark_return": 0.12,
        "max_drawdown": -0.08,
        "sharpe_ratio": 1.2,
    }
    result = check_portfolio_summary_thresholds(summary)
    assert result.passed


def test_thresholds_pass(tmp_path: Path):
    _write_minimal_bundle(
        tmp_path,
        {
            "initial_cash": 10000.0,
            "final_equity": 11000.0,
            "total_return": 0.10,
            "benchmark_return": 0.12,
            "max_drawdown": -0.08,
            "sharpe_ratio": 1.2,
            "trades": 0,
            "win_rate": 0.0,
        },
    )
    result = check_portfolio_backtest_thresholds(tmp_path)
    assert result.passed
    assert not result.failures


def test_thresholds_fail_max_drawdown(tmp_path: Path):
    _write_minimal_bundle(
        tmp_path,
        {
            "initial_cash": 10000.0,
            "final_equity": 9000.0,
            "total_return": -0.10,
            "benchmark_return": 0.05,
            "max_drawdown": -0.35,
            "sharpe_ratio": -0.5,
            "trades": 0,
            "win_rate": 0.0,
        },
    )
    result = check_portfolio_backtest_thresholds(
        tmp_path, PortfolioBacktestThresholds(max_drawdown_floor=-0.20)
    )
    assert not result.passed
    assert any("max_drawdown" in f for f in result.failures)


def test_thresholds_fail_benchmark_gap(tmp_path: Path):
    _write_minimal_bundle(
        tmp_path,
        {
            "initial_cash": 10000.0,
            "final_equity": 9500.0,
            "total_return": 0.05,
            "benchmark_return": 0.30,
            "max_drawdown": -0.10,
            "sharpe_ratio": 0.5,
            "trades": 0,
            "win_rate": 0.0,
        },
    )
    result = check_portfolio_backtest_thresholds(
        tmp_path, PortfolioBacktestThresholds(min_return_vs_benchmark=-0.15)
    )
    assert not result.passed
    assert any("benchmark" in f for f in result.failures)


def test_cli_exit_codes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import subprocess
    import sys

    _write_minimal_bundle(
        tmp_path,
        {
            "initial_cash": 10000.0,
            "final_equity": 11000.0,
            "total_return": 0.10,
            "benchmark_return": 0.12,
            "max_drawdown": -0.08,
            "sharpe_ratio": 1.2,
            "trades": 0,
            "win_rate": 0.0,
        },
    )
    script = Path(__file__).resolve().parents[1] / "scripts" / "check_portfolio_backtest_gate.py"
    env = {**dict(__import__("os").environ), "PYTHONPATH": "."}
    ok = subprocess.run(
        [sys.executable, str(script), "--dir", str(tmp_path)],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        check=False,
    )
    assert ok.returncode == 0