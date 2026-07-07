import unittest
from datetime import datetime, timedelta, timezone

from src.extended_hours_fill_report import build_extended_hours_fill_report


class TestExtendedHoursFillReport(unittest.TestCase):
    def test_fill_rate_from_mock_orders(self) -> None:
        # relative timestamp so the orders always fall inside the lookback window
        submitted = (datetime.now(timezone.utc) - timedelta(days=3)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        closed = [
            {
                "id": "1",
                "extended_hours": True,
                "type": "LIMIT",
                "status_simple": "FILLED",
                "submitted_at": submitted,
            },
            {
                "id": "2",
                "extended_hours": True,
                "type": "LIMIT",
                "status_simple": "CANCELED",
                "submitted_at": submitted,
            },
        ]
        report = build_extended_hours_fill_report(
            closed_orders=closed,
            open_orders=[],
            lookback_days=30,
        )
        self.assertEqual(report["extended_limit_orders"], 2)
        self.assertEqual(report["filled"], 1)
        self.assertEqual(report["fill_rate_terminal"], 0.5)


if __name__ == "__main__":
    unittest.main()
