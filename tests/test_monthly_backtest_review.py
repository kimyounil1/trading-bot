from pathlib import Path

import pandas as pd

from src.monthly_backtest_review import (
    build_monthly_backtest_attribution,
    write_monthly_backtest_review,
)


def _equity() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(
                ["2026-01-02", "2026-01-30", "2026-02-02", "2026-02-27"]
            ),
            "equity": [10_000.0, 10_500.0, 10_400.0, 9_900.0],
            "cash": [2_000.0, 2_100.0, 2_000.0, 2_500.0],
            "positions_value": [8_000.0, 8_400.0, 8_400.0, 7_400.0],
            "positions_count": [4, 4, 4, 3],
            "drawdown": [0.0, 0.0, -0.01, -0.06],
            "benchmark_equity": [10_000.0, 10_200.0, 10_250.0, 10_300.0],
        }
    )


def _trades() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["AAA", "BBB"],
            "exit_date": ["2026-02-10", "2026-02-20"],
            "cost_basis": [1_000.0, 1_000.0],
            "exit_value": [900.0, 1_050.0],
            "return_pct": [-0.10, 0.05],
            "exit_reason": ["STOP_LOSS", "TAKE_PROFIT"],
            "leveraged": [True, False],
            "sleeve_id": ["tournament", "core"],
        }
    )


def test_monthly_attribution_identifies_loss_driver() -> None:
    result = build_monthly_backtest_attribution(
        _equity(),
        _trades(),
        initial_cash=10_000.0,
    )

    february = result[result["month"] == "2026-02"].iloc[0]
    assert february["monthly_return"] < 0
    assert february["excess_return"] < 0
    assert february["worst_ticker"] == "AAA"
    assert february["stop_loss_count"] == 1
    assert february["leveraged_trade_count"] == 1
    assert february["leveraged_realized_pnl_usd"] == -100.0
    assert february["underlying_realized_pnl_usd"] == 50.0
    assert february["worst_sleeve"] == "tournament"


def test_monthly_review_queue_records_followup_checklist(tmp_path: Path) -> None:
    csv_path, queue_path = write_monthly_backtest_review(
        tmp_path,
        _equity(),
        _trades(),
        initial_cash=10_000.0,
    )

    assert csv_path.is_file()
    text = queue_path.read_text(encoding="utf-8")
    assert "2026-02 — 손실" in text
    assert "수정안 백테스트" in text
    assert "forward 검증" in text
