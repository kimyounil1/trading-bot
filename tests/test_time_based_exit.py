import unittest
from datetime import datetime, timedelta, timezone
from src.main import _resolve_full_exit_reason

class TestTimeBasedExit(unittest.TestCase):
    def test_max_holding_reached(self):
        # unrealized_plpc=0.01 (1%), not triggered by stop/tp/trailing
        reason = _resolve_full_exit_reason(
            unrealized_plpc=0.01,
            stop_loss_pct=0.05,
            take_profit_pct=0.1,
            trailing_drawdown=0.0,
            trailing_stop_pct=0.05,
            signal="HOLD",
            ai_exit_triggered=False,
            holding_days=31,
            max_holding_days=30
        )
        self.assertIsNotNone(reason)
        self.assertIn("max holding period reached", reason)

    def test_max_holding_not_reached(self):
        reason = _resolve_full_exit_reason(
            unrealized_plpc=0.01,
            stop_loss_pct=0.05,
            take_profit_pct=0.1,
            trailing_drawdown=0.0,
            trailing_stop_pct=0.05,
            signal="HOLD",
            ai_exit_triggered=False,
            holding_days=10,
            max_holding_days=30
        )
        self.assertIsNone(reason)

if __name__ == "__main__":
    unittest.main()
