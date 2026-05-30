"""Golden regression for portfolio backtest CSV outputs ([AGY] slice)."""

from pathlib import Path

import pytest

from src.portfolio_backtest_validation import (
    load_summary_row,
    validate_portfolio_backtest_dir,
)

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "portfolio_backtest"


@pytest.fixture
def golden_summary() -> dict:
    return load_summary_row(FIXTURE_DIR / "portfolio_summary.csv")


def test_fixture_dir_passes_schema_and_trade_count():
    result = validate_portfolio_backtest_dir(FIXTURE_DIR)
    assert result["equity_rows"] >= 100
    assert result["trades_rows"] == result["summary"]["trades"]


def test_fixture_matches_golden_summary_metrics(golden_summary: dict):
    validate_portfolio_backtest_dir(FIXTURE_DIR, golden_summary=golden_summary)


def test_rejects_missing_summary_column(tmp_path: Path, golden_summary: dict):
    import pandas as pd

    bad = tmp_path / "portfolio_summary.csv"
    pd.DataFrame([{"initial_cash": 10000.0}]).to_csv(bad, index=False)
    (tmp_path / "portfolio_equity.csv").write_text(
        (FIXTURE_DIR / "portfolio_equity.csv").read_text()
    )
    (tmp_path / "portfolio_trades.csv").write_text(
        (FIXTURE_DIR / "portfolio_trades.csv").read_text()
    )
    with pytest.raises(ValueError, match="missing columns"):
        validate_portfolio_backtest_dir(tmp_path, golden_summary=golden_summary)
