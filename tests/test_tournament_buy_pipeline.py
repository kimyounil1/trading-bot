import unittest
from unittest.mock import MagicMock, patch

from src.portfolio_sleeves import TOURNAMENT_SLEEVE_ID, default_sleeves_config
from src.settings import StrategySettings
from src.sleeve_runtime import init_sleeve_run_context
from src.trading.tournament_buy_pipeline import run_tournament_buy_pipeline


class TournamentBuyPipelineTest(unittest.TestCase):
    @patch("src.trading.tournament_buy_pipeline.select_tournament_candidates")
    @patch("src.trading.tournament_buy_pipeline.get_signal_for_ticker")
    def test_skips_when_no_alpha_picks(
        self,
        mock_signal,
        mock_select,
    ) -> None:
        mock_select.return_value = {}
        settings = StrategySettings(
            portfolio_sleeves_enabled=True,
            sleeves=default_sleeves_config(),
            tickers=["AAPL"],
        )
        broker = MagicMock()
        broker.get_open_orders.return_value = []
        broker.get_open_symbols.return_value = set()
        ctx = MagicMock()
        ctx.settings = settings
        ctx.sleeve_ctx = init_sleeve_run_context(
            settings,
            broker_adapter=broker,
            account={
                "portfolio_value": 100_000.0,
                "cash": 20_000.0,
                "buying_power": 20_000.0,
            },
            positions=[],
        )
        ctx.sleeve_ctx.recon_ok = True
        ctx.rank_ai_gate_scores = {}
        ctx.ticker_data = {"AAPL": MagicMock()}
        ctx.price_data_freshness = {"AAPL": (True, "")}
        ctx.buy_summary_rows = []
        run_tournament_buy_pipeline(ctx)
        mock_signal.assert_not_called()

    def test_tournament_budget_initialized(self) -> None:
        settings = StrategySettings(
            portfolio_sleeves_enabled=True,
            sleeves=default_sleeves_config(),
        )
        broker = MagicMock()
        broker.get_open_orders.return_value = []
        sleeve_ctx = init_sleeve_run_context(
            settings,
            broker_adapter=broker,
            account={
                "portfolio_value": 100_000.0,
                "cash": 20_000.0,
                "buying_power": 20_000.0,
            },
            positions=[],
        )
        self.assertIn(TOURNAMENT_SLEEVE_ID, sleeve_ctx.budget_remaining)


if __name__ == "__main__":
    unittest.main()
