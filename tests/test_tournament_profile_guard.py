import unittest

from src.brokers.paper import PaperBrokerAdapter
from src.settings import StrategySettings
from src.trading_config_guard import validate_live_policies


class TournamentProfileGuardTest(unittest.TestCase):
    def test_tournament_paper_only_blocks_live_sleeves(self) -> None:
        settings = StrategySettings(
            portfolio_sleeves_enabled=True,
            live_safety_enabled=True,
            live_safety_max_daily_loss_pct=0.03,
            sleeves={
                "core": {
                    "enabled": True,
                    "target_weight": 0.5,
                    "profile": "paper",
                    "strategy": "current_core",
                },
                "tournament": {
                    "enabled": True,
                    "target_weight": 0.3,
                    "profile": "tournament_paper",
                    "strategy": "alpha_tournament",
                    "paper_only": True,
                },
                "cash": {
                    "enabled": True,
                    "target_weight": 0.2,
                    "strategy": "cash_reserve",
                },
            },
        )
        broker = PaperBrokerAdapter()
        reasons = validate_live_policies(settings, "live", broker)
        self.assertTrue(any("tournament" in r for r in reasons))
        self.assertTrue(any("paper_only" in r for r in reasons))


if __name__ == "__main__":
    unittest.main()
