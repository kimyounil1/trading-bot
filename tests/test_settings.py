import tempfile
import unittest
from pathlib import Path

from src.settings import (
    StrategySettings,
    apply_dynamic_profile,
    load_settings,
    save_settings,
    validate_settings,
)


class SettingsTest(unittest.TestCase):
    def test_validate_settings_accepts_recent_runtime_fields(self) -> None:
        settings = StrategySettings(
            tickers=[" aapl "],
            ma_fast=10,
            ma_slow=50,
            rsi_buy_limit=65,
            max_position_pct=0.25,
            max_total_positions=4,
            stop_loss_pct=0.05,
            take_profit_pct=0.10,
            max_test_order_amount=1000.0,
            max_orders_per_run=2,
            max_daily_order_amount=2000.0,
            buy_cooldown_days=1,
            use_ai_score=True,
            ai_score_buy_threshold=0.55,
            market_regime_filter_enabled=True,
            market_regime_ticker=" spy ",
            market_regime_ma_fast=50,
            market_regime_ma_slow=200,
            trailing_stop_pct=0.08,
            take_profit_partial_pct=0.15,
            partial_exit_ratio=0.5,
            leverage_factor=1.5,
            max_gross_exposure_pct=1.2,
            min_cash_buffer_pct=0.10,
            max_single_name_loss_pct=0.02,
            crowding_guard_enabled=True,
            crowding_lookback_days=30,
            crowding_max_positions=2,
            crowding_momentum_threshold=0.12,
            crowding_trend_gap_threshold=0.04,
            dynamic_universe_enabled=True,
            dynamic_count=30,
            rebalance_threshold_pct=0.20,
            sector_rotation_enabled=True,
        )

        validated = validate_settings(settings)

        self.assertEqual(validated.tickers, ["AAPL"])
        self.assertEqual(validated.market_regime_ticker, "SPY")
        self.assertEqual(validated.trailing_stop_pct, 0.08)
        self.assertEqual(validated.dynamic_count, 30)
        self.assertEqual(validated.max_gross_exposure_pct, 1.2)
        self.assertEqual(validated.crowding_lookback_days, 30)

    def test_validate_settings_rejects_invalid_recent_runtime_fields(self) -> None:
        settings = StrategySettings(
            tickers=["AAPL"],
            ma_fast=10,
            ma_slow=50,
            rsi_buy_limit=65,
            max_position_pct=0.25,
            max_total_positions=4,
            stop_loss_pct=0.05,
            take_profit_pct=0.10,
            max_test_order_amount=1000.0,
            max_orders_per_run=2,
            max_daily_order_amount=2000.0,
            buy_cooldown_days=1,
            use_ai_score=False,
            ai_score_buy_threshold=0.55,
            market_regime_filter_enabled=False,
            market_regime_ticker="SPY",
            market_regime_ma_fast=50,
            market_regime_ma_slow=200,
            trailing_stop_pct=1.2,
            partial_exit_ratio=0.0,
            leverage_factor=0.0,
            max_gross_exposure_pct=2.0,
            min_cash_buffer_pct=1.2,
            max_single_name_loss_pct=0.0,
            crowding_lookback_days=0,
            crowding_max_positions=0,
            crowding_momentum_threshold=-0.1,
            crowding_trend_gap_threshold=-0.1,
            dynamic_count=0,
            rebalance_threshold_pct=-0.1,
        )

        with self.assertRaisesRegex(ValueError, "trailing_stop_pct must be between 0 and 1"):
            validate_settings(settings)

    def test_save_and_load_settings_round_trip(self) -> None:
        settings = StrategySettings(
            tickers=["aapl", "msft"],
            ma_fast=10,
            ma_slow=50,
            rsi_buy_limit=65,
            max_position_pct=0.25,
            max_total_positions=4,
            stop_loss_pct=0.05,
            take_profit_pct=0.10,
            max_test_order_amount=1000.0,
            max_orders_per_run=2,
            max_daily_order_amount=2000.0,
            buy_cooldown_days=1,
            use_ai_score=True,
            ai_score_buy_threshold=0.55,
            market_regime_filter_enabled=True,
            market_regime_ticker="spy",
            market_regime_ma_fast=50,
            market_regime_ma_slow=200,
            trailing_stop_pct=0.07,
            take_profit_partial_pct=0.12,
            partial_exit_ratio=0.4,
            leverage_factor=1.2,
            max_gross_exposure_pct=1.1,
            min_cash_buffer_pct=0.08,
            max_single_name_loss_pct=0.015,
            crowding_guard_enabled=True,
            crowding_lookback_days=45,
            crowding_max_positions=3,
            crowding_momentum_threshold=0.10,
            crowding_trend_gap_threshold=0.03,
            dynamic_universe_enabled=True,
            dynamic_count=25,
            rebalance_threshold_pct=0.15,
            sector_rotation_enabled=True,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "strategy_config.json"
            save_settings(settings, path=path)
            loaded = load_settings(path=path)

        self.assertEqual(loaded.tickers, ["AAPL", "MSFT"])
        self.assertEqual(loaded.market_regime_ticker, "SPY")
        self.assertEqual(loaded.trailing_stop_pct, 0.07)
        self.assertEqual(loaded.partial_exit_ratio, 0.4)
        self.assertEqual(loaded.dynamic_count, 25)
        self.assertEqual(loaded.max_gross_exposure_pct, 1.1)
        self.assertEqual(loaded.min_cash_buffer_pct, 0.08)
        self.assertEqual(loaded.max_single_name_loss_pct, 0.015)
        self.assertEqual(loaded.crowding_lookback_days, 45)
        self.assertEqual(loaded.crowding_max_positions, 3)

    def test_load_repo_strategy_config_accepts_position_sizing_keys(self) -> None:
        from src.settings import CONFIG_PATH

        if not CONFIG_PATH.exists():
            self.skipTest(f"missing {CONFIG_PATH}")
        loaded = load_settings(path=CONFIG_PATH)
        self.assertEqual(loaded.max_single_order_pct, 0.35)
        self.assertEqual(loaded.max_daily_order_pct, 0.45)
        self.assertTrue(loaded.conviction_sizing_enabled)
        self.assertTrue(loaded.rank_ai_buy_gate_enabled)
        self.assertEqual(loaded.rank_ai_buy_gate_top_bucket_pct, 0.15)
        self.assertEqual(loaded.rank_ai_buy_gate_min_score_quantile, 0.85)
        self.assertEqual(loaded.ma_fast, 30)
        self.assertEqual(loaded.ma_slow, 200)
        self.assertEqual(loaded.rsi_buy_limit, 100.0)
        self.assertFalse(loaded.allow_leveraged_etfs)
        self.assertEqual(loaded.leveraged_etf_allowlist, [])
        self.assertTrue(loaded.margin_leverage_paper_enabled)
        self.assertTrue(loaded.conditional_margin_leverage_enabled)
        self.assertEqual(loaded.conditional_margin_leverage_bull_factor, 2.0)
        self.assertEqual(loaded.conditional_margin_leverage_defensive_factor, 1.0)
        self.assertEqual(loaded.conditional_margin_leverage_vix_max, 22.0)

        bull_settings, profile_name = apply_dynamic_profile(loaded, "BULL")
        self.assertEqual(profile_name, "AGGRESSIVE")
        self.assertEqual(bull_settings.ma_fast, 30)
        self.assertEqual(bull_settings.ma_slow, 200)
        self.assertEqual(bull_settings.rsi_buy_limit, 100.0)

    def test_load_settings_rejects_unknown_json_keys(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "strategy_config.json"
            path.write_text(
                """
                {
                  "tickers": ["AAPL"],
                  "ma_fast": 10,
                  "ma_slow": 50,
                  "rsi_buy_limit": 65,
                  "unknown_flag": true
                }
                """.strip(),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "Unknown keys"):
                load_settings(path=path)

    def test_apply_dynamic_profile_rejects_invalid_profile_schema(self) -> None:
        settings = StrategySettings(
            tickers=["AAPL"],
            ma_fast=10,
            ma_slow=50,
            rsi_buy_limit=65,
            max_position_pct=0.25,
            max_total_positions=4,
            stop_loss_pct=0.05,
            take_profit_pct=0.10,
            max_test_order_amount=1000.0,
            max_orders_per_run=2,
            max_daily_order_amount=2000.0,
            buy_cooldown_days=1,
            use_ai_score=False,
            ai_score_buy_threshold=0.55,
            market_regime_filter_enabled=False,
            market_regime_ticker="SPY",
            market_regime_ma_fast=50,
            market_regime_ma_slow=200,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "strategy_profiles.json"
            path.write_text(
                """
                {
                  "profiles": {
                    "AGGRESSIVE": {
                      "max_total_positions": 3,
                      "bad_key": 123
                    }
                  },
                  "regime_mapping": {
                    "BULL": "AGGRESSIVE"
                  },
                  "manual_override": null
                }
                """.strip(),
                encoding="utf-8",
            )

            updated_settings, profile_name = apply_dynamic_profile(
                settings,
                "BULL",
                profiles_path=path,
            )

        self.assertIn("DEFAULT (error:", profile_name)
        self.assertIn("unknown keys", profile_name)
        self.assertEqual(updated_settings.name, settings.name)


if __name__ == "__main__":
    unittest.main()
