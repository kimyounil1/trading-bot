import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import json
import pandas as pd
import tempfile

from src.reappraise_regime import reappraise_regime, STATE_PATH

class TestReappraiseRegime(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.state_path_mock = Path(self.temp_dir.name) / "market_regime_state.json"
        self.historical_state_path_mock = Path(self.temp_dir.name) / "market_regime_state_historical.json"
        
        # Patch paths to point to our temp state files
        self.state_path_patcher = patch("src.reappraise_regime.STATE_PATH", self.state_path_mock)
        self.historical_path_patcher = patch("src.reappraise_regime.HISTORICAL_STATE_PATH", self.historical_state_path_mock)
        self.state_path_patcher.start()
        self.historical_path_patcher.start()

    def tearDown(self):
        self.state_path_patcher.stop()
        self.historical_path_patcher.stop()
        self.temp_dir.cleanup()

    @patch("src.reappraise_regime.load_price_data_batch")
    @patch("src.reappraise_regime.notify_info")
    def test_reappraise_regime_first_run(self, mock_notify, mock_load_data):
        # Setup mock data for SPY and VIX (computes to BULL)
        spy_dates = pd.date_range("2026-01-01", periods=250)
        spy_df = pd.DataFrame({
            "date": spy_dates,
            "adj_close": [100.0 + i * 0.1 for i in range(250)]
        })
        vix_df = pd.DataFrame({
            "date": spy_dates,
            "adj_close": [15.0] * 250
        })
        mock_load_data.return_value = {
            "SPY": spy_df,
            "^VIX": vix_df
        }

        # Run
        reappraise_regime()

        # Check state file creation
        self.assertTrue(self.state_path_mock.exists())
        state = json.loads(self.state_path_mock.read_text(encoding="utf-8"))
        self.assertEqual(state["regime"], "BULL")
        self.assertIn("updated_at", state)

        # First run should not trigger change notification
        mock_notify.assert_not_called()

    @patch("src.reappraise_regime.load_price_data_batch")
    @patch("src.reappraise_regime.notify_info")
    def test_reappraise_regime_change_triggers_notification(self, mock_notify, mock_load_data):
        # Create a previous state of BEAR
        self.state_path_mock.write_text(json.dumps({
            "regime": "BEAR",
            "updated_at": "2026-05-29T10:00:00"
        }), encoding="utf-8")

        # Mock data (computes to BULL)
        spy_dates = pd.date_range("2026-01-01", periods=250)
        spy_df = pd.DataFrame({
            "date": spy_dates,
            "adj_close": [100.0 + i * 0.1 for i in range(250)]
        })
        vix_df = pd.DataFrame({
            "date": spy_dates,
            "adj_close": [15.0] * 250
        })
        mock_load_data.return_value = {
            "SPY": spy_df,
            "^VIX": vix_df
        }

        # Run
        reappraise_regime()

        # Verify state is updated to BULL
        state = json.loads(self.state_path_mock.read_text(encoding="utf-8"))
        self.assertEqual(state["regime"], "BULL")

        # Verify change notification was triggered
        mock_notify.assert_called_once()
        args, _ = mock_notify.call_args
        self.assertEqual(args[0], "📢 Regime & Profile Updated")
        self.assertIn("Previous: BEAR", args[1])
        self.assertIn("Current: BULL", args[1])

    @patch("src.reappraise_regime.load_price_data_batch")
    @patch("src.reappraise_regime.notify_info")
    def test_reappraise_regime_historical_run(self, mock_notify, mock_load_data):
        # Mock data (computes to BULL)
        spy_dates = pd.date_range("2024-01-01", periods=800)
        spy_df = pd.DataFrame({
            "date": spy_dates,
            "adj_close": [100.0 + i * 0.1 for i in range(800)]
        })
        vix_df = pd.DataFrame({
            "date": spy_dates,
            "adj_close": [15.0] * 800
        })
        mock_load_data.return_value = {
            "SPY": spy_df,
            "^VIX": vix_df
        }

        # Run with target date
        reappraise_regime(current_date_str="2026-03-18")

        # Live state file should NOT be created
        self.assertFalse(self.state_path_mock.exists())

        # Historical state file SHOULD be created
        self.assertTrue(self.historical_state_path_mock.exists())
        state = json.loads(self.historical_state_path_mock.read_text(encoding="utf-8"))
        self.assertEqual(state["regime"], "BULL")
        self.assertTrue(state["is_historical"])

        # Historical runs should never send notifications
        mock_notify.assert_not_called()

if __name__ == "__main__":
    unittest.main()
