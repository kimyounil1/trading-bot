import tempfile
import unittest
from pathlib import Path

from src.sleeve_rebalance_state import (
    allocation_rebalance_pending,
    request_allocation_rebalance,
)


class SleeveRebalanceStateFileTest(unittest.TestCase):
    def test_request_writes_pending_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            request_allocation_rebalance(reason="unit", path=path)
            self.assertTrue(allocation_rebalance_pending(path=path))
            payload = path.read_text(encoding="utf-8")
            self.assertIn("allocation_rebalance_pending", payload)


if __name__ == "__main__":
    unittest.main()
