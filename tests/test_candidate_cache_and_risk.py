import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from src.candidate_cache import build_data_quality_rows, load_latest_candidate_cache_full
from src.risk_manager import apply_buy_safety_limits
from src.settings import StrategySettings


class CandidateCacheAndRiskTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
