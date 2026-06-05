import os
import unittest
from unittest.mock import patch

from src.live_deploy_guard import assert_live_execution_allowed


class LiveDeployGuardTest(unittest.TestCase):
    def test_paper_execute_allowed_without_confirm(self) -> None:
        assert_live_execution_allowed(execute=True, trading_environment="paper")

    @patch.dict(os.environ, {"TRADING_ENV": "live"}, clear=False)
    def test_live_execute_blocked_without_confirm(self) -> None:
        with self.assertRaises(RuntimeError):
            assert_live_execution_allowed(execute=True, trading_environment="live")

    @patch.dict(
        os.environ,
        {"TRADING_ENV": "live", "CONFIRM_LIVE_TRADING": "YES_I_UNDERSTAND"},
        clear=False,
    )
    def test_live_execute_allowed_with_phrase(self) -> None:
        assert_live_execution_allowed(execute=True, trading_environment="live")


if __name__ == "__main__":
    unittest.main()
