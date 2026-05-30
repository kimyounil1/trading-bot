import json
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from src.report_performance import (
    analyze_slippage,
    compute_slippage_report,
    format_slippage_report,
    run_weekly_slippage_report,
    write_slippage_artifacts,
)


@pytest.fixture
def create_log_files(tmp_path):
    signals_file = tmp_path / "signals.csv"
    orders_file = tmp_path / "orders.csv"

    signals_data = {
        "timestamp": ["2023-01-01T10:00:00Z", "2023-01-01T10:00:00Z"],
        "ticker": ["TICKER1", "TICKER2"],
        "close": [100.0, 200.0],
        "volume": [1000, 500],
    }
    pd.DataFrame(signals_data).to_csv(signals_file, index=False)

    orders_data = {
        "timestamp": ["2023-01-01T10:00:10Z", "2023-01-01T10:00:15Z"],
        "ticker": ["TICKER1", "TICKER2"],
        "notional": [1000, 1000],
        "order_id": ["order1", "order2"],
        "status": ["filled", "filled"],
        "side": ["OrderSide.BUY", "OrderSide.SELL"],
        "order_type": ["market", "market"],
        "filled_qty": [10, 5],
        "filled_avg_price": [101.0, 199.0],
        "reason": ["some_reason", "some_reason"],
        "event": ["STATUS_CHECK", "STATUS_CHECK"],
    }
    pd.DataFrame(orders_data).to_csv(orders_file, index=False)

    return signals_file, orders_file


@patch("sys.stdout", new_callable=StringIO)
def test_analyze_slippage_with_usd_cost(mock_stdout, create_log_files):
    signals_path, orders_path = create_log_files

    analyze_slippage(signals_path=signals_path, orders_path=orders_path)

    output = mock_stdout.getvalue()
    assert "Total Slippage Cost: $15.00" in output
    assert "TICKER1" in output
    assert "TICKER2" in output
    assert "10.0" in output
    assert "5.0" in output


def test_compute_slippage_report(create_log_files):
    signals_path, orders_path = create_log_files
    report = compute_slippage_report(signals_path=signals_path, orders_path=orders_path)
    assert report is not None
    assert report.matched_trades == 2
    assert report.total_slippage_usd == pytest.approx(15.0)
    assert "TICKER1" in {row["ticker"] for row in report.by_ticker}


def test_write_slippage_artifacts(create_log_files, tmp_path: Path):
    signals_path, orders_path = create_log_files
    report = compute_slippage_report(signals_path=signals_path, orders_path=orders_path)
    assert report is not None
    run_dir = write_slippage_artifacts(report, tmp_path, run_id="test_run")
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["total_slippage_usd"] == pytest.approx(15.0)
    assert (tmp_path / "latest_summary.json").is_file()


def test_run_weekly_slippage_report_writes_no_data_summary(tmp_path: Path):
    missing_signals = tmp_path / "signals.csv"
    missing_orders = tmp_path / "orders.csv"
    report = run_weekly_slippage_report(
        lookback_days=7,
        output_dir=tmp_path / "out",
        signals_path=missing_signals,
        orders_path=missing_orders,
    )
    assert report.status == "no_data"
    latest = json.loads((tmp_path / "out" / "latest_summary.json").read_text(encoding="utf-8"))
    assert latest["status"] == "no_data"
    assert latest["matched_trades"] == 0


@patch("sys.stdout", new_callable=StringIO)
def test_run_weekly_slippage_report(mock_stdout, create_log_files, tmp_path: Path):
    signals_path, orders_path = create_log_files
    report = run_weekly_slippage_report(
        lookback_days=9999,
        output_dir=tmp_path,
        signals_path=signals_path,
        orders_path=orders_path,
    )
    assert report is not None
    assert format_slippage_report(report)
    assert list(tmp_path.glob("slippage_*"))
