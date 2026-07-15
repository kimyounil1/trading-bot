import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from src.logger import log_execution_audit
from src.main import _summarize_run_metrics


class LoggerAuditTest(unittest.TestCase):
    def test_log_execution_audit_writes_expected_columns(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "execution_audit.csv"
            with patch("src.logger.EXECUTION_AUDIT_LOG_PATH", str(log_path)):
                log_execution_audit(
                    event_type="BUY_SUBMITTED",
                    ticker="AAPL",
                    action="BUY",
                    status="accepted",
                    reason="buy allowed",
                    profile_name="AGGRESSIVE",
                    regime="BULL",
                    signal="BUY",
                    ai_score=0.81234,
                    llm_verdict="ACCEPT: no major issues",
                    order_id="abc123",
                    order_type="market",
                    side="buy",
                    notional=1234.567,
                    quantity=10.12345,
                    filled_qty=10.12345,
                    filled_avg_price=121.98765,
                    signal_ticker="AAPL",
                    execution_ticker="AAPB",
                    decision_market_date="2026-07-14",
                    quality_notional_multiplier=0.5,
                    quality_allow_leveraged=True,
                    route_leveraged=True,
                    portfolio_value=10000.0,
                    planned_notional_pct=0.05,
                )

            frame = pd.read_csv(log_path)

        self.assertEqual(frame.loc[0, "event_type"], "BUY_SUBMITTED")
        self.assertEqual(frame.loc[0, "ticker"], "AAPL")
        self.assertEqual(frame.loc[0, "profile_name"], "AGGRESSIVE")
        self.assertEqual(frame.loc[0, "regime"], "BULL")
        self.assertAlmostEqual(frame.loc[0, "ai_score"], 0.8123, places=4)
        self.assertAlmostEqual(frame.loc[0, "notional"], 1234.57, places=2)
        self.assertAlmostEqual(frame.loc[0, "quantity"], 10.1235, places=4)
        self.assertAlmostEqual(frame.loc[0, "filled_avg_price"], 121.9877, places=4)
        self.assertEqual(frame.loc[0, "execution_ticker"], "AAPB")
        self.assertAlmostEqual(
            frame.loc[0, "quality_notional_multiplier"], 0.5, places=4
        )
        self.assertAlmostEqual(frame.loc[0, "planned_notional_pct"], 0.05, places=4)

    def test_summarize_run_metrics_formats_counts(self) -> None:
        summary = _summarize_run_metrics(
            live_order_count=3,
            skipped_reasons=Counter({"buy:dry_run_only": 2, "exit:stale data": 1}),
            data_error_count=4,
            api_error_count=1,
        )

        self.assertIn("orders_submitted=3", summary)
        self.assertIn("buy:dry_run_only=2", summary)
        self.assertIn("exit:stale data=1", summary)
        self.assertIn("data_errors=4", summary)
        self.assertIn("api_errors=1", summary)


if __name__ == "__main__":
    unittest.main()
