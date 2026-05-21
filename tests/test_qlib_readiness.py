import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from src.data_loader import load_cached_price_data_batch
from src.generate_baseline_snapshot import main as generate_baseline_snapshot_main
from src.portfolio_backtester import PortfolioBacktestResult, run_portfolio_backtest
from src.qlib_adapter import export_qlib_ready_data, to_qlib_ready_frame
from src.settings import StrategySettings


def _sample_price_frame(rows: int = 260) -> pd.DataFrame:
    values = np.arange(rows, dtype=float)
    return pd.DataFrame(
        {
            "date": pd.date_range("2023-01-01", periods=rows),
            "open": values + 1.0,
            "high": values + 2.0,
            "low": values + 0.5,
            "close": values + 1.5,
            "adj_close": (values + 1.5) * 1.01,
            "volume": values + 100.0,
        }
    )


class QlibReadinessTest(unittest.TestCase):
    def test_to_qlib_ready_frame_normalizes_columns(self) -> None:
        qlib_df = to_qlib_ready_frame("aapl", _sample_price_frame(5))

        self.assertEqual(
            qlib_df.columns.tolist(),
            ["instrument", "datetime", "open", "high", "low", "close", "volume", "factor"],
        )
        self.assertEqual(qlib_df["instrument"].unique().tolist(), ["AAPL"])
        self.assertTrue((qlib_df["factor"] > 0).all())

    def test_export_qlib_ready_data_writes_csvs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            written_paths = export_qlib_ready_data(
                {"AAPL": _sample_price_frame(5), "MSFT": _sample_price_frame(5)},
                temp_dir,
            )

            self.assertEqual(len(written_paths), 2)
            for path in written_paths:
                self.assertTrue(Path(path).exists())

    def test_load_cached_price_data_batch_uses_cache_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_root = Path(temp_dir) / "raw"
            for ticker in ("AAPL", "MSFT"):
                target = cache_root / ticker / "2y.csv"
                target.parent.mkdir(parents=True, exist_ok=True)
                _sample_price_frame(5).to_csv(target, index=False)

            with patch("src.data_loader.PRICE_CACHE_DIR", cache_root):
                result = load_cached_price_data_batch(["AAPL", "MSFT"], period="2y")

            self.assertEqual(sorted(result.keys()), ["AAPL", "MSFT"])
            self.assertEqual(len(result["AAPL"]), 5)

    def test_generate_baseline_snapshot_writes_metadata(self) -> None:
        settings = StrategySettings(
            tickers=["AAPL", "MSFT"],
            ma_fast=10,
            ma_slow=50,
            rsi_buy_limit=65,
            max_position_pct=0.1,
            max_total_positions=4,
            stop_loss_pct=0.05,
            take_profit_pct=0.1,
            max_test_order_amount=1000.0,
            max_orders_per_run=2,
            max_daily_order_amount=2000.0,
            buy_cooldown_days=1,
            use_ai_score=False,
            ai_score_buy_threshold=0.45,
            market_regime_filter_enabled=False,
            market_regime_ticker="SPY",
            market_regime_ma_fast=50,
            market_regime_ma_slow=200,
        )
        result = PortfolioBacktestResult(
            initial_cash=10000.0,
            final_equity=10800.0,
            total_return=0.08,
            max_drawdown=-0.05,
            trades=4,
            win_rate=0.5,
            benchmark_return=0.06,
        )
        equity_df = pd.DataFrame({"date": ["2024-01-01"], "equity": [10000.0]})
        trades_df = pd.DataFrame({"ticker": ["AAPL"]})

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "logs" / "baselines" / "current_strategy"

            with patch("src.generate_baseline_snapshot.load_settings", return_value=settings), patch(
                "src.generate_baseline_snapshot.load_cached_price_data_batch",
                return_value={"AAPL": _sample_price_frame(5), "MSFT": _sample_price_frame(5)},
            ), patch(
                "src.generate_baseline_snapshot.run_portfolio_backtest",
                return_value=(result, equity_df, trades_df),
            ), patch(
                "src.generate_baseline_snapshot.save_portfolio_backtest_outputs"
            ) as save_outputs_mock, patch(
                "src.generate_baseline_snapshot.export_qlib_ready_data",
                return_value=[output_dir / "qlib_ready" / "AAPL.csv"],
            ), patch(
                "src.generate_baseline_snapshot.Path",
                side_effect=lambda value="logs/baselines/current_strategy": output_dir
                if value == "logs/baselines/current_strategy"
                else Path(value),
            ):
                generate_baseline_snapshot_main()

            metadata_path = output_dir / "baseline_snapshot.json"
            self.assertTrue(metadata_path.exists())
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            self.assertEqual(metadata["tickers"], ["AAPL", "MSFT"])
            self.assertEqual(metadata["result"]["final_equity"], 10800.0)
            save_outputs_mock.assert_called_once()

    def test_run_portfolio_backtest_market_regime_filter_blocks_buys(self) -> None:
        stock_df = _sample_price_frame(260)
        benchmark_df = _sample_price_frame(260)
        benchmark_df["close"] = np.linspace(300.0, 100.0, 260)
        benchmark_df["adj_close"] = benchmark_df["close"]

        result, equity_df, trades_df = run_portfolio_backtest(
            ticker_data={"AAPL": stock_df},
            benchmark_df=benchmark_df,
            initial_cash=10000.0,
            max_positions=1,
            target_position_pct=0.5,
            transaction_cost_pct=0.001,
            ma_fast=10,
            ma_slow=50,
            rsi_buy_limit=101,
            market_regime_filter_enabled=True,
            market_regime_ma_fast=50,
            market_regime_ma_slow=200,
        )

        self.assertEqual(result.trades, 0)
        self.assertTrue(trades_df.empty)
        self.assertTrue((equity_df["positions_count"] == 0).all())


if __name__ == "__main__":
    unittest.main()
