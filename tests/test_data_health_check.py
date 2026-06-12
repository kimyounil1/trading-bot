import unittest
from unittest.mock import patch

import pandas as pd

from src.data_health_check import _check_ticker_frame, build_data_health_report


def _frame_with_jump(jump_pct: float, rows: int = 30) -> pd.DataFrame:
    dates = pd.date_range(end=pd.Timestamp.utcnow(), periods=rows, freq="D")
    prices = [100.0] * rows
    prices[rows // 2] = 100.0 * (1.0 + jump_pct)
    return pd.DataFrame({"date": dates, "close": prices, "adj_close": prices})


class DataHealthCheckTest(unittest.TestCase):
    @patch("src.data_health_check.load_price_data_batch")
    def test_empty_batch_is_no_go(self, mock_load) -> None:
        mock_load.return_value = {}
        report = build_data_health_report(settings=__import__("src.settings", fromlist=["StrategySettings"]).StrategySettings(tickers=["AAPL"]))
        self.assertEqual(report["overall"], "NO_GO")

    @patch("src.data_health_check.load_price_data_batch")
    def test_fresh_data_can_be_go(self, mock_load) -> None:
        rows = 30
        dates = pd.date_range(end=pd.Timestamp.utcnow(), periods=rows, freq="D")
        frame = pd.DataFrame(
            {
                "date": dates,
                "close": [100.0 + i * 0.1 for i in range(rows)],
                "adj_close": [100.0 + i * 0.1 for i in range(rows)],
            }
        )
        mock_load.return_value = {"AAPL": frame, "SPY": frame, "^VIX": frame}
        report = build_data_health_report(
            settings=__import__("src.settings", fromlist=["StrategySettings"]).StrategySettings(tickers=["AAPL"])
        )
        self.assertIn(report["overall"], {"GO", "NO_GO"})

    def test_vix_daily_jump_uses_volatility_threshold(self) -> None:
        frame = _frame_with_jump(0.74)
        vix_result = _check_ticker_frame("^VIX", frame)
        self.assertTrue(vix_result["ok"], vix_result["issues"])

        stock_result = _check_ticker_frame("AAPL", frame)
        self.assertFalse(stock_result["ok"])
        self.assertTrue(any("max_daily_jump" in issue for issue in stock_result["issues"]))

    def test_vix_extreme_jump_still_flagged(self) -> None:
        result = _check_ticker_frame("^VIX", _frame_with_jump(2.5))
        self.assertFalse(result["ok"])
        self.assertTrue(any("max_daily_jump" in issue for issue in result["issues"]))


if __name__ == "__main__":
    unittest.main()
