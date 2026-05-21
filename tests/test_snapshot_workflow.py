import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from src.generate_qlib_snapshot import main as generate_qlib_snapshot_main
from src.snapshot_utils import build_snapshot_payload, save_snapshot_payload


class SnapshotWorkflowTest(unittest.TestCase):
    def test_build_and_save_snapshot_payload(self) -> None:
        payload = build_snapshot_payload(
            period="2y",
            tickers=["AAPL"],
            settings={"ma_fast": 10},
            result={"final_equity": 11000.0},
            equity_rows=100,
            trade_rows=5,
            extra_fields={"provider_uri": "/tmp/qlib"},
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = save_snapshot_payload(payload, Path(temp_dir) / "snapshot.json")
            saved = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(saved["period"], "2y")
        self.assertEqual(saved["provider_uri"], "/tmp/qlib")

    def test_generate_qlib_snapshot_matches_baseline_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            settings_path = temp_path / "settings.json"
            tickers_path = temp_path / "tickers.txt"
            equity_path = temp_path / "equity.csv"
            trades_path = temp_path / "trades.csv"
            output_path = temp_path / "qlib_snapshot.json"

            settings_path.write_text(json.dumps({"ma_fast": 10, "ma_slow": 50}), encoding="utf-8")
            tickers_path.write_text("AAPL\nMSFT\n", encoding="utf-8")
            pd.DataFrame({"equity": [10000, 10100]}).to_csv(equity_path, index=False)
            pd.DataFrame({"ticker": ["AAPL"]}).to_csv(trades_path, index=False)

            argv = [
                "prog",
                "--output",
                str(output_path),
                "--settings-json",
                str(settings_path),
                "--tickers-file",
                str(tickers_path),
                "--equity-csv",
                str(equity_path),
                "--trades-csv",
                str(trades_path),
                "--provider-uri",
                "/tmp/qlib/us_custom",
                "--initial-cash",
                "10000",
                "--final-equity",
                "11250",
                "--total-return",
                "0.125",
                "--benchmark-return",
                "0.09",
                "--max-drawdown",
                "-0.04",
                "--trades",
                "7",
                "--win-rate",
                "0.57",
            ]

            with patch("sys.argv", argv):
                generate_qlib_snapshot_main()

            snapshot = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(snapshot["tickers"], ["AAPL", "MSFT"])
        self.assertEqual(snapshot["equity_rows"], 2)
        self.assertEqual(snapshot["trade_rows"], 1)
        self.assertEqual(snapshot["result"]["final_equity"], 11250.0)
        self.assertEqual(snapshot["provider_uri"], "/tmp/qlib/us_custom")


if __name__ == "__main__":
    unittest.main()
