import tempfile
import unittest
from pathlib import Path

from src.portfolio_sleeves import CORE_SLEEVE_ID, TOURNAMENT_SLEEVE_ID
from src.sleeve_position_registry import (
    bootstrap_open_positions,
    load_sleeve_position_map,
    tag_symbol,
    untag_symbol,
)


class SleevePositionRegistryTest(unittest.TestCase):
    def test_bootstrap_tags_unassigned_symbols_to_core(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "sleeve_positions.json"
            mapping = bootstrap_open_positions(["AAPL", "MSFT"], path=path)
            self.assertEqual(mapping["AAPL"], CORE_SLEEVE_ID)
            self.assertEqual(mapping["MSFT"], CORE_SLEEVE_ID)
            reloaded = load_sleeve_position_map(path)
            self.assertEqual(reloaded, mapping)

    def test_tag_and_untag_symbol(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "sleeve_positions.json"
            tag_symbol("NVDA", TOURNAMENT_SLEEVE_ID, path=path)
            self.assertEqual(
                load_sleeve_position_map(path)["NVDA"],
                TOURNAMENT_SLEEVE_ID,
            )
            untag_symbol("NVDA", path=path)
            self.assertNotIn("NVDA", load_sleeve_position_map(path))


if __name__ == "__main__":
    unittest.main()
