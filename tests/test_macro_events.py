import unittest
from datetime import date
from src.macro_events import get_macro_event_risk

class TestMacroEvents(unittest.TestCase):
    def test_fomc_upcoming(self):
        # FOMC 2026-03-18. 2 days before is 2026-03-16
        test_date = date(2026, 3, 16)
        is_risk, reason = get_macro_event_risk(current_date=test_date, lookforward_days=2)
        self.assertTrue(is_risk)
        self.assertIn("upcoming FOMC", reason)

    def test_cpi_day_of(self):
        # CPI 2026-05-12
        test_date = date(2026, 5, 12)
        is_risk, reason = get_macro_event_risk(current_date=test_date)
        self.assertTrue(is_risk)
        self.assertIn("upcoming CPI", reason)

    def test_nfp_recent(self):
        # NFP 2026-06-05. 1 day after is 2026-06-06
        test_date = date(2026, 6, 6)
        is_risk, reason = get_macro_event_risk(current_date=test_date, lookback_days=1)
        self.assertTrue(is_risk)
        self.assertIn("recent NFP", reason)

    def test_no_event(self):
        # Mid July 2026, far from events
        test_date = date(2026, 7, 20)
        is_risk, reason = get_macro_event_risk(current_date=test_date)
        self.assertFalse(is_risk)
        self.assertEqual(reason, "")

if __name__ == "__main__":
    unittest.main()
