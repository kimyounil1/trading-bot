import unittest
from unittest.mock import patch

import pandas as pd

from src.data_health_check import build_data_health_report


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


if __name__ == "__main__":
    unittest.main()
