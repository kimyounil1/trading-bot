import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.main import _load_peaks, _save_peaks


class MainPeaksTest(unittest.TestCase):
    def test_save_peaks_writes_normalized_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            peaks_path = Path(temp_dir) / "trailing_peaks.json"
            with patch("src.main.PEAKS_PATH", peaks_path):
                _save_peaks({" aapl ": 123.45, "msft": 456})
                loaded = _load_peaks()
                self.assertTrue(peaks_path.exists())
                self.assertFalse(peaks_path.with_suffix(".json.tmp").exists())

        self.assertEqual(loaded, {"AAPL": 123.45, "MSFT": 456.0})

    def test_load_peaks_quarantines_corrupt_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            peaks_path = Path(temp_dir) / "trailing_peaks.json"
            peaks_path.write_text("{bad json", encoding="utf-8")

            with patch("src.main.PEAKS_PATH", peaks_path):
                loaded = _load_peaks()

            corrupt_path = peaks_path.with_suffix(".json.corrupt")
            self.assertFalse(peaks_path.exists())
            self.assertTrue(corrupt_path.exists())

        self.assertEqual(loaded, {})

    def test_load_peaks_quarantines_invalid_peak_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            peaks_path = Path(temp_dir) / "trailing_peaks.json"
            peaks_path.write_text('{"AAPL": "oops"}', encoding="utf-8")

            with patch("src.main.PEAKS_PATH", peaks_path):
                loaded = _load_peaks()

            corrupt_path = peaks_path.with_suffix(".json.corrupt")
            self.assertTrue(corrupt_path.exists())

        self.assertEqual(loaded, {})


if __name__ == "__main__":
    unittest.main()
