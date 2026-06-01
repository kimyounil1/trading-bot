import unittest

from src.extended_hours_fill_report import build_extended_hours_fill_report


class TestExtendedHoursFillReport(unittest.TestCase):
    def test_fill_rate_from_mock_orders(self) -> None:
        closed = [
            {
                "id": "1",
                "extended_hours": True,
                "type": "LIMIT",
                "status_simple": "FILLED",
                "submitted_at": "2026-06-01T10:00:00Z",
            },
            {
                "id": "2",
                "extended_hours": True,
                "type": "LIMIT",
                "status_simple": "CANCELED",
                "submitted_at": "2026-06-01T11:00:00Z",
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
