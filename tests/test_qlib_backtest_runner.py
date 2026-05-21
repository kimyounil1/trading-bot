import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.qlib_backtest_runner import (
    apply_signal_execution_constraints,
    build_close_price_lookup,
    build_strategy_signal_from_price_data,
    build_momentum_signal_from_qlib_ready,
    compute_report_metrics,
    extract_trades_from_positions,
    infer_backtest_window,
    load_qlib_ready_price_frame,
    load_strategy_settings_from_json,
    load_signal_frame,
    run_custom_signal_backtest,
)
from src.settings import StrategySettings


class QlibBacktestRunnerTest(unittest.TestCase):
    def test_load_signal_frame_normalizes_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "signal.csv"
            pd.DataFrame(
                {
                    "datetime": ["2024-01-01", "2024-01-01"],
                    "instrument": ["aapl", "msft"],
                    "score": [0.1, 0.2],
                }
            ).to_csv(path, index=False)

            frame = load_signal_frame(path)

        self.assertEqual(frame.index.names, ["datetime", "instrument"])
        self.assertEqual(frame.columns.tolist(), ["score"])

    def test_build_momentum_signal_from_qlib_ready(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "AAPL.csv"
            pd.DataFrame(
                {
                    "instrument": ["AAPL"] * 5,
                    "datetime": pd.date_range("2024-01-01", periods=5).astype(str),
                    "close": [10, 11, 12, 13, 14],
                }
            ).to_csv(path, index=False)

            signal = build_momentum_signal_from_qlib_ready(temp_dir, momentum_window=2)

        self.assertGreater(len(signal), 0)
        self.assertEqual(signal.index.names, ["datetime", "instrument"])

    def test_infer_backtest_window(self) -> None:
        index = pd.MultiIndex.from_tuples(
            [
                (pd.Timestamp("2024-01-03"), "AAPL"),
                (pd.Timestamp("2024-01-05"), "MSFT"),
            ],
            names=["datetime", "instrument"],
        )
        signal = pd.DataFrame({"score": [0.1, 0.2]}, index=index)

        start_time, end_time = infer_backtest_window(signal)
        self.assertEqual(start_time, "2024-01-03")
        self.assertEqual(end_time, "2024-01-03")

    def test_compute_report_metrics(self) -> None:
        report = pd.DataFrame(
            {
                "return": [0.01, -0.02, 0.03],
                "bench": [0.005, -0.01, 0.02],
                "cost": [0.001, 0.001, 0.001],
                "turnover": [0.2, 0.0, 0.3],
            }
        )

        metrics = compute_report_metrics(report, initial_cash=10000.0)

        self.assertIn("final_equity", metrics)
        self.assertEqual(metrics["trades"], 2)
        self.assertLess(metrics["max_drawdown"], 0)

    def test_load_qlib_ready_price_frame_and_lookup(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "AAPL.csv"
            pd.DataFrame(
                {
                    "instrument": ["AAPL", "AAPL"],
                    "datetime": ["2024-01-01", "2024-01-02"],
                    "close": [10.0, 11.0],
                }
            ).to_csv(path, index=False)

            frame = load_qlib_ready_price_frame(temp_dir)
            lookup = build_close_price_lookup(frame)

        self.assertEqual(len(frame), 2)
        self.assertEqual(lookup[(pd.Timestamp("2024-01-02"), "AAPL")], 11.0)

    def test_extract_trades_from_positions(self) -> None:
        class DummyPosition:
            def __init__(self, position):
                self.position = position

        positions = {
            pd.Timestamp("2024-01-01"): DummyPosition(
                {"cash": 1000.0, "now_account_value": 1000.0}
            ),
            pd.Timestamp("2024-01-02"): DummyPosition(
                {
                    "cash": 500.0,
                    "now_account_value": 1000.0,
                    "AAPL": {"amount": 10.0, "price": 50.0, "weight": 0.5, "count_day": 1},
                }
            ),
            pd.Timestamp("2024-01-03"): DummyPosition(
                {"cash": 1100.0, "now_account_value": 1100.0}
            ),
        }
        lookup = {
            (pd.Timestamp("2024-01-03"), "AAPL"): 60.0,
        }

        trades = extract_trades_from_positions(positions, lookup)

        self.assertEqual(len(trades), 1)
        self.assertEqual(trades.iloc[0]["ticker"], "AAPL")
        self.assertAlmostEqual(trades.iloc[0]["return_pct"], 0.2)

    def test_build_strategy_signal_from_price_data(self) -> None:
        rows = 80
        upward = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=rows),
                "open": range(1, rows + 1),
                "high": range(2, rows + 2),
                "low": range(1, rows + 1),
                "close": range(2, rows + 2),
                "adj_close": range(2, rows + 2),
                "volume": [1000] * rows,
            }
        )
        settings = StrategySettings(
            tickers=["AAPL"],
            ma_fast=10,
            ma_slow=50,
            rsi_buy_limit=101,
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

        signal = build_strategy_signal_from_price_data({"AAPL": upward}, settings)

        self.assertGreater(len(signal), 0)
        self.assertEqual(signal.index.names, ["datetime", "instrument"])

    def test_apply_signal_execution_constraints(self) -> None:
        index = pd.MultiIndex.from_tuples(
            [
                (pd.Timestamp("2024-01-01"), "AAPL"),
                (pd.Timestamp("2024-01-01"), "MSFT"),
                (pd.Timestamp("2024-01-02"), "AAPL"),
                (pd.Timestamp("2024-01-02"), "MSFT"),
                (pd.Timestamp("2024-01-03"), "AAPL"),
                (pd.Timestamp("2024-01-03"), "GOOG"),
            ],
            names=["datetime", "instrument"],
        )
        signal = pd.DataFrame(
            {"score": [0.9, 0.8, 0.7, 0.95, 0.85, 0.75]},
            index=index,
        )

        constrained = apply_signal_execution_constraints(
            signal,
            max_active_signals=2,
            max_new_signals_per_day=1,
            cooldown_days=1,
        )

        expected_rows = [
            (pd.Timestamp("2024-01-01"), "AAPL"),
            (pd.Timestamp("2024-01-02"), "AAPL"),
            (pd.Timestamp("2024-01-02"), "MSFT"),
            (pd.Timestamp("2024-01-03"), "AAPL"),
            (pd.Timestamp("2024-01-03"), "GOOG"),
        ]
        self.assertEqual(list(constrained.index), expected_rows)

    def test_load_strategy_settings_from_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "settings.json"
            path.write_text('{"tickers":["aapl"],"ma_fast":10,"ma_slow":50}', encoding="utf-8")
            settings = load_strategy_settings_from_json(path)

        self.assertEqual(settings.tickers, ["AAPL"])

    def test_run_custom_signal_backtest_applies_limits(self) -> None:
        settings = StrategySettings(
            tickers=["AAPL", "MSFT"],
            ma_fast=10,
            ma_slow=50,
            rsi_buy_limit=65,
            max_position_pct=0.5,
            max_total_positions=1,
            stop_loss_pct=0.05,
            take_profit_pct=0.1,
            max_test_order_amount=1000.0,
            max_orders_per_run=1,
            max_daily_order_amount=10000.0,
            buy_cooldown_days=1,
            use_ai_score=False,
            ai_score_buy_threshold=0.45,
            market_regime_filter_enabled=False,
            market_regime_ticker="SPY",
            market_regime_ma_fast=50,
            market_regime_ma_slow=200,
        )
        signal_index = pd.MultiIndex.from_tuples(
            [
                (pd.Timestamp("2024-01-01"), "AAPL"),
                (pd.Timestamp("2024-01-01"), "MSFT"),
                (pd.Timestamp("2024-01-02"), "MSFT"),
                (pd.Timestamp("2024-01-03"), "AAPL"),
            ],
            names=["datetime", "instrument"],
        )
        signal_frame = pd.DataFrame(
            {"score": [0.9, 0.8, 0.85, 0.95]},
            index=signal_index,
        )
        price_frame = pd.DataFrame(
            {
                "datetime": pd.to_datetime(
                    [
                        "2024-01-01",
                        "2024-01-01",
                        "2024-01-02",
                        "2024-01-02",
                        "2024-01-03",
                        "2024-01-03",
                    ]
                ),
                "instrument": ["AAPL", "MSFT", "AAPL", "MSFT", "AAPL", "MSFT"],
                "close": [10.0, 20.0, 11.0, 19.0, 12.0, 18.0],
            }
        )

        result, equity_df, trades_df = run_custom_signal_backtest(
            signal_frame=signal_frame,
            price_frame=price_frame,
            settings=settings,
            initial_cash=10000.0,
            open_cost=0.0,
            close_cost=0.0,
            start_time="2024-01-01",
            end_time="2024-01-03",
        )

        self.assertEqual(len(equity_df), 3)
        self.assertEqual(result["trades"], 2)
        self.assertEqual(trades_df["ticker"].tolist(), ["AAPL", "MSFT"])
        self.assertTrue(result["final_equity"] > 10000.0)


if __name__ == "__main__":
    unittest.main()
