import sys
import os
import pandas as pd
from unittest.mock import patch
from io import StringIO
import pytest

# Add src to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from report_performance import analyze_slippage

@pytest.fixture
def create_log_files(tmp_path):
    signals_file = tmp_path / "signals.csv"
    orders_file = tmp_path / "orders.csv"

    signals_data = {
        "timestamp": ["2023-01-01T10:00:00Z", "2023-01-01T10:00:00Z"],
        "ticker": ["TICKER1", "TICKER2"],
        "close": [100.0, 200.0],
        "volume": [1000, 500]
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
        "event": ["STATUS_CHECK", "STATUS_CHECK"]
    }
    pd.DataFrame(orders_data).to_csv(orders_file, index=False)

    return str(signals_file), str(orders_file)

@patch('sys.stdout', new_callable=StringIO)
def test_analyze_slippage_with_usd_cost(mock_stdout, create_log_files):
    signals_path, orders_path = create_log_files

    # Call analyze_slippage with the paths to the temporary log files
    analyze_slippage(signals_path=signals_path, orders_path=orders_path)

    output = mock_stdout.getvalue()
    
    # Check for TICKER1 (buy) slippage: (101 - 100) * 10 = 10
    # Check for TICKER2 (sell) slippage: (200 - 199) * 5 = 5
    # Total slippage: 10 + 5 = 15

    assert "Total Slippage Cost: $15.00" in output
    assert "TICKER1" in output
    assert "TICKER2" in output
    # Check for the summary table values
    # For TICKER1, total_slippage_usd is 10.0
    # For TICKER2, total_slippage_usd is 5.0
    assert "10.0" in output
    assert "5.0" in output
