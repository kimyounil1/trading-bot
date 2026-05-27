import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from src.candidate_cache import (
    build_data_quality_rows,
    get_dynamic_universe,
    load_latest_candidate_cache_full,
)
from src.risk_manager import (
    apply_buy_safety_limits,
    apply_factor_crowding_limits,
    apply_portfolio_exposure_limits,
    check_additional_buy_allowed,
)
from src.settings import StrategySettings


class CandidateCacheAndRiskTest(unittest.TestCase):
    @staticmethod
    def _price_frame(close_values: list[float]) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "date": pd.date_range("2026-01-01", periods=len(close_values)),
                "open": close_values,
                "high": [value + 1.0 for value in close_values],
                "low": [value - 1.0 for value in close_values],
                "close": close_values,
                "adj_close": close_values,
                "volume": [1000.0] * len(close_values),
            }
        )

    def test_build_data_quality_rows_flags_short_history_and_errors(self) -> None:
        short_df = pd.DataFrame(
            {
                "date": pd.date_range("2026-01-01", periods=10),
                "open": range(10),
                "high": range(10),
                "low": range(10),
                "close": range(10),
                "volume": range(10),
            }
        )

        quality_df, errors_df = build_data_quality_rows(
            ["AAPL", "MSFT"],
            {"AAPL": short_df},
        )

        self.assertEqual(len(quality_df), 2)
        self.assertEqual(
            quality_df.loc[quality_df["ticker"] == "AAPL", "data_status"].iloc[0],
            "WARN",
        )
        self.assertEqual(
            quality_df.loc[quality_df["ticker"] == "MSFT", "data_status"].iloc[0],
            "ERROR",
        )
        self.assertEqual(set(errors_df["ticker"]), {"AAPL", "MSFT"})

    def test_apply_buy_safety_limits_blocks_cooldown_and_daily_limit(self) -> None:
        settings = StrategySettings(
            tickers=["AAPL"],
            ma_fast=10,
            ma_slow=50,
            rsi_buy_limit=65,
            max_position_pct=0.4,
            max_total_positions=2,
            stop_loss_pct=0.05,
            take_profit_pct=0.1,
            max_test_order_amount=10.0,
            max_orders_per_run=1,
            max_daily_order_amount=100.0,
            buy_cooldown_days=2,
            use_ai_score=False,
            ai_score_buy_threshold=0.55,
            market_regime_filter_enabled=False,
            market_regime_ticker="SPY",
            market_regime_ma_fast=50,
            market_regime_ma_slow=200,
        )

        with patch("src.risk_manager.load_settings", return_value=settings):
            cooldown = apply_buy_safety_limits(
                ticker="AAPL",
                order_amount=10.0,
                submitted_notional_today=0.0,
                recent_buy_symbols={"AAPL"},
            )
            daily_limit = apply_buy_safety_limits(
                ticker="MSFT",
                order_amount=20.0,
                submitted_notional_today=90.0,
                recent_buy_symbols=set(),
            )

        self.assertFalse(cooldown.allowed)
        self.assertIn("cooldown", cooldown.reason)
        self.assertFalse(daily_limit.allowed)
        self.assertIn("daily order amount limit", daily_limit.reason)

    def test_check_additional_buy_allowed_targets_position_allocation(self) -> None:
        settings = StrategySettings(
            tickers=["NVDA"],
            ma_fast=10,
            ma_slow=50,
            rsi_buy_limit=65,
            max_position_pct=0.1,
            max_total_positions=2,
            stop_loss_pct=0.05,
            take_profit_pct=0.1,
            max_test_order_amount=1000.0,
            max_orders_per_run=1,
            max_daily_order_amount=1000.0,
            buy_cooldown_days=1,
            use_ai_score=False,
            ai_score_buy_threshold=0.55,
            market_regime_filter_enabled=False,
            market_regime_ticker="SPY",
            market_regime_ma_fast=50,
            market_regime_ma_slow=200,
        )

        with patch("src.risk_manager.load_settings", return_value=settings):
            under_target = check_additional_buy_allowed(
                signal="BUY",
                cash=1000.0,
                portfolio_value=10000.0,
                current_position_value=250.0,
            )
            at_target = check_additional_buy_allowed(
                signal="BUY",
                cash=1000.0,
                portfolio_value=10000.0,
                current_position_value=1000.0,
            )

        self.assertTrue(under_target.allowed)
        self.assertEqual(under_target.reason, "add to existing position allowed")
        self.assertEqual(under_target.target_amount, 750.0)
        self.assertFalse(at_target.allowed)
        self.assertEqual(at_target.reason, "position target allocation reached")

    def test_load_latest_candidate_cache_full_reads_optional_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir)
            (cache_dir / "latest_meta.json").write_text('{"tickers":["AAPL"]}', encoding="utf-8")
            pd.DataFrame({"ticker": ["AAPL"]}).to_csv(cache_dir / "latest_exit.csv", index=False)
            pd.DataFrame({"ticker": ["MSFT"]}).to_csv(cache_dir / "latest_buy.csv", index=False)
            pd.DataFrame({"ticker": ["AAPL"], "data_status": ["OK"]}).to_csv(
                cache_dir / "latest_quality.csv",
                index=False,
            )
            pd.DataFrame({"ticker": ["MSFT"], "data_status": ["ERROR"]}).to_csv(
                cache_dir / "latest_errors.csv",
                index=False,
            )

            with patch("src.candidate_cache.LATEST_META_PATH", cache_dir / "latest_meta.json"), patch(
                "src.candidate_cache.LATEST_EXIT_PATH", cache_dir / "latest_exit.csv"
            ), patch(
                "src.candidate_cache.LATEST_BUY_PATH", cache_dir / "latest_buy.csv"
            ), patch(
                "src.candidate_cache.LATEST_QUALITY_PATH", cache_dir / "latest_quality.csv"
            ), patch(
                "src.candidate_cache.LATEST_ERRORS_PATH", cache_dir / "latest_errors.csv"
            ):
                meta, exit_df, buy_df, quality_df, errors_df = load_latest_candidate_cache_full()

        self.assertEqual(meta["tickers"], ["AAPL"])
        self.assertEqual(exit_df["ticker"].tolist(), ["AAPL"])
        self.assertEqual(buy_df["ticker"].tolist(), ["MSFT"])
        self.assertEqual(quality_df["data_status"].tolist(), ["OK"])
        self.assertEqual(errors_df["data_status"].tolist(), ["ERROR"])

    def test_get_dynamic_universe_writes_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir)
            with patch(
                "src.candidate_cache._fetch_trending_tickers_with_meta",
                return_value=(["NVDA", "AMD", None], "unit_test_source"),
            ), patch(
                "src.candidate_cache.CACHE_DIR", cache_dir
            ), patch(
                "src.candidate_cache.LATEST_META_PATH", cache_dir / "latest_meta.json"
            ):
                universe = get_dynamic_universe(["AAPL", "msft", "^VIX"], limit=3)
                meta = json.loads((cache_dir / "latest_meta.json").read_text(encoding="utf-8"))

        self.assertEqual(set(universe), {"AAPL", "MSFT", "NVDA", "AMD"})
        self.assertEqual(meta["source"], "unit_test_source")
        self.assertEqual(meta["static_count"], 3)
        self.assertEqual(meta["trending_count"], 2)
        self.assertEqual(meta["final_count"], 4)
        self.assertIn("generated_at", meta)

    def test_apply_portfolio_exposure_limits_blocks_risk_breaches(self) -> None:
        settings = StrategySettings(
            tickers=["AAPL"],
            ma_fast=10,
            ma_slow=50,
            rsi_buy_limit=65,
            max_position_pct=0.4,
            max_total_positions=2,
            stop_loss_pct=0.10,
            take_profit_pct=0.1,
            max_test_order_amount=10.0,
            max_orders_per_run=1,
            max_daily_order_amount=100.0,
            buy_cooldown_days=2,
            use_ai_score=False,
            ai_score_buy_threshold=0.55,
            market_regime_filter_enabled=False,
            market_regime_ticker="SPY",
            market_regime_ma_fast=50,
            market_regime_ma_slow=200,
            leverage_factor=1.5,
            max_gross_exposure_pct=1.2,
            min_cash_buffer_pct=0.10,
            max_single_name_loss_pct=0.02,
        )

        with patch("src.risk_manager.load_settings", return_value=settings):
            gross = apply_portfolio_exposure_limits(
                ticker="AAPL",
                order_amount=300.0,
                cash=1000.0,
                portfolio_value=1000.0,
                buying_power=5000.0,
                current_gross_exposure=950.0,
            )
            cash_buffer = apply_portfolio_exposure_limits(
                ticker="AAPL",
                order_amount=150.0,
                cash=200.0,
                portfolio_value=1000.0,
                buying_power=5000.0,
                current_gross_exposure=200.0,
            )
            single_name = apply_portfolio_exposure_limits(
                ticker="AAPL",
                order_amount=250.0,
                cash=1000.0,
                portfolio_value=1000.0,
                buying_power=5000.0,
                current_gross_exposure=200.0,
                current_position_value=0.0,
            )

        self.assertFalse(gross.allowed)
        self.assertIn("gross exposure limit", gross.reason)
        self.assertFalse(cash_buffer.allowed)
        self.assertIn("cash buffer", cash_buffer.reason)
        self.assertFalse(single_name.allowed)
        self.assertIn("single-name max loss", single_name.reason)

    def test_apply_factor_crowding_limits_blocks_overcrowded_momentum_trade(self) -> None:
        settings = StrategySettings(
            tickers=["AAPL", "MSFT", "NVDA"],
            ma_fast=10,
            ma_slow=50,
            rsi_buy_limit=65,
            max_position_pct=0.4,
            max_total_positions=3,
            stop_loss_pct=0.05,
            take_profit_pct=0.1,
            max_test_order_amount=10.0,
            max_orders_per_run=1,
            max_daily_order_amount=100.0,
            buy_cooldown_days=1,
            use_ai_score=False,
            ai_score_buy_threshold=0.55,
            market_regime_filter_enabled=False,
            market_regime_ticker="SPY",
            market_regime_ma_fast=50,
            market_regime_ma_slow=200,
            crowding_guard_enabled=True,
            crowding_lookback_days=20,
            crowding_max_positions=2,
            crowding_momentum_threshold=0.15,
            crowding_trend_gap_threshold=0.05,
        )
        strong_uptrend = list(range(100, 161))
        ticker_data = {
            "AAPL": self._price_frame(strong_uptrend),
            "MSFT": self._price_frame([value * 1.01 for value in strong_uptrend]),
            "NVDA": self._price_frame([value * 1.02 for value in strong_uptrend]),
        }

        with patch("src.risk_manager.load_settings", return_value=settings):
            decision = apply_factor_crowding_limits(
                ticker="NVDA",
                open_symbols={"AAPL", "MSFT"},
                ticker_data=ticker_data,
            )

        self.assertFalse(decision.allowed)
        self.assertIn("crowding limit reached", decision.reason)

    def test_apply_factor_crowding_limits_allows_non_crowded_candidate(self) -> None:
        settings = StrategySettings(
            tickers=["AAPL", "MSFT", "TLT"],
            ma_fast=10,
            ma_slow=50,
            rsi_buy_limit=65,
            max_position_pct=0.4,
            max_total_positions=3,
            stop_loss_pct=0.05,
            take_profit_pct=0.1,
            max_test_order_amount=10.0,
            max_orders_per_run=1,
            max_daily_order_amount=100.0,
            buy_cooldown_days=1,
            use_ai_score=False,
            ai_score_buy_threshold=0.55,
            market_regime_filter_enabled=False,
            market_regime_ticker="SPY",
            market_regime_ma_fast=50,
            market_regime_ma_slow=200,
            crowding_guard_enabled=True,
            crowding_lookback_days=20,
            crowding_max_positions=2,
            crowding_momentum_threshold=0.15,
            crowding_trend_gap_threshold=0.05,
        )
        strong_uptrend = list(range(100, 161))
        flat_series = [100.0] * 61
        ticker_data = {
            "AAPL": self._price_frame(strong_uptrend),
            "MSFT": self._price_frame([value * 1.01 for value in strong_uptrend]),
            "TLT": self._price_frame(flat_series),
        }

        with patch("src.risk_manager.load_settings", return_value=settings):
            decision = apply_factor_crowding_limits(
                ticker="TLT",
                open_symbols={"AAPL", "MSFT"},
                ticker_data=ticker_data,
            )

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.reason, "candidate not crowding-sensitive")


if __name__ == "__main__":
    unittest.main()
