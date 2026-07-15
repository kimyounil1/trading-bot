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

    @patch("src.trading.tournament_buy_pipeline.audit_log")
    @patch("src.trading.tournament_buy_pipeline.build_buy_intent")
    @patch("src.trading.tournament_buy_pipeline.apply_effective_leverage_exposure_limits")
    @patch("src.trading.tournament_buy_pipeline.cap_single_order_amount", side_effect=lambda amount, *a, **k: amount)
    @patch("src.trading.tournament_buy_pipeline.adjust_position_cap_for_instrument", side_effect=lambda pct, *a, **k: pct)
    @patch("src.trading.tournament_buy_pipeline.check_instrument_buy_allowed", return_value=(True, ""))
    @patch("src.trading.tournament_buy_pipeline.resolve_leveraged_product_route")
    @patch("src.trading.tournament_buy_pipeline.evaluate_rank_quality_risk")
    @patch("src.trading.tournament_buy_pipeline.rank_ai_entry_signal", return_value="BUY")
    @patch("src.trading.tournament_buy_pipeline.load_named_profile_overlay", return_value={})
    @patch("src.trading.tournament_buy_pipeline.get_signal_for_ticker")
    @patch("src.trading.tournament_buy_pipeline.select_tournament_candidates")
    def test_buy_submitted_audit_includes_rank_fields(
        self,
        mock_select,
        mock_signal,
        mock_overlay,
        mock_entry,
        mock_quality,
        mock_route,
        mock_instrument,
        mock_cap_pct,
        mock_cap_amount,
        mock_leverage,
        mock_intent,
        mock_audit,
    ) -> None:
        from types import SimpleNamespace

        mock_select.return_value = {
            "AAPL": SimpleNamespace(alpha_score=0.9, max_position_pct=0.2, reason="alpha pick")
        }
        mock_signal.return_value = ("BUY", {"close": 100.0}, 0.8)
        mock_quality.return_value = SimpleNamespace(
            notional_multiplier=1.0,
            reason="quality ok",
            allow_leveraged=True,
            high_drawdown=False,
            downtrend=False,
            market_date="2026-07-15",
        )
        mock_route.return_value = SimpleNamespace(
            route_allowed=True,
            execution_ticker="AAPL",
            reason="direct",
            leveraged=False,
            reference_price=100.0,
        )
        mock_leverage.return_value = SimpleNamespace(
            allowed=True, target_amount=1_000.0, reason=""
        )
        mock_intent.return_value = SimpleNamespace(
            intent_id="intent-1",
            client_order_id="tour_run_AAPL",
            sleeve_budget_before=5_000.0,
            sleeve_budget_after=4_000.0,
        )

        settings = StrategySettings(
            portfolio_sleeves_enabled=True,
            sleeves=default_sleeves_config(),
            tickers=["AAPL"],
        )
        broker = MagicMock()
        broker.get_open_orders.return_value = []
        broker.get_open_symbols.return_value = set()
        broker.submit_buy_notional.return_value = SimpleNamespace(
            order_id="o1", status="accepted", side="buy", order_type="limit"
        )
        broker.wait_for_order_status.return_value = {
            "id": "o1",
            "status": "filled",
            "side": "buy",
            "type": "limit",
            "filled_qty": 10.0,
            "filled_avg_price": 100.0,
        }
        ctx = MagicMock()
        ctx.settings = settings
        ctx.broker_adapter = broker
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
        ctx.sleeve_ctx.budget_remaining[TOURNAMENT_SLEEVE_ID] = 5_000.0
        ctx.rank_ai_gate_scores = {"AAPL": {"score": 0.43, "percentile": 0.91}}
        ctx.ticker_data = {"AAPL": MagicMock()}
        ctx.price_data_freshness = {"AAPL": (True, "")}
        ctx.positions_by_symbol = {}
        ctx.dust_min_usd = 1.0
        ctx.account = {"portfolio_value": 100_000.0}
        ctx.orders_submitted = 0
        ctx.live_order_count = 0
        ctx.submitted_notional_today = 0.0
        ctx.cash = 20_000.0
        ctx.current_gross_exposure = 0.0
        ctx.guard_open_symbols = set()
        ctx.open_symbols = set()
        ctx.buy_summary_rows = []
        ctx.can_submit_orders = True
        ctx.api_error_count = 0

        run_tournament_buy_pipeline(ctx)

        submitted_calls = [
            call for call in mock_audit.call_args_list
            if call.kwargs.get("event_type") == "BUY_SUBMITTED"
        ]
        self.assertEqual(len(submitted_calls), 1)
        kwargs = submitted_calls[0].kwargs
        self.assertEqual(kwargs["rank_ai_score"], 0.43)
        self.assertEqual(kwargs["rank_ai_percentile"], 0.91)

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
