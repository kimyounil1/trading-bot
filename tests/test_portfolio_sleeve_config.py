import json
import unittest

from src.portfolio_sleeves import (
    default_sleeves_config,
    parse_sleeves_config,
    validate_sleeves_config,
)
from src.settings import StrategySettings, validate_settings


class PortfolioSleeveConfigTest(unittest.TestCase):
    def test_default_weights_sum_at_most_one(self) -> None:
        parsed = parse_sleeves_config(default_sleeves_config())
        errors = validate_sleeves_config(parsed, enabled=True)
        self.assertEqual(errors, [])

    def test_rejects_weight_sum_over_one(self) -> None:
        raw = default_sleeves_config()
        raw["core"]["target_weight"] = 0.80
        parsed = parse_sleeves_config(raw)
        errors = validate_sleeves_config(parsed, enabled=True)
        self.assertTrue(any("exceeds 1.0" in err for err in errors))

    def test_validate_settings_accepts_disabled_sleeves(self) -> None:
        settings = validate_settings(StrategySettings(portfolio_sleeves_enabled=False))
        self.assertFalse(settings.portfolio_sleeves_enabled)

    def test_validate_settings_rejects_enabled_without_core(self) -> None:
        sleeves = default_sleeves_config()
        sleeves.pop("core")
        with self.assertRaises(ValueError):
            validate_settings(
                StrategySettings(
                    portfolio_sleeves_enabled=True,
                    sleeves=sleeves,
                )
            )

    def test_tournament_paper_profile_exists(self) -> None:
        from pathlib import Path

        path = json.loads(
            Path("config/profiles/tournament_paper.json").read_text(encoding="utf-8")
        )
        self.assertEqual(path["trading_environment"], "paper")


if __name__ == "__main__":
    unittest.main()
