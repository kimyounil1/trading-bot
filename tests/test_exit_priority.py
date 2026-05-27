import unittest

import numpy as np
import pandas as pd

from src.main import _resolve_full_exit_reason
from src.portfolio_backtester import run_portfolio_backtest


def _price_frame(close_values: np.ndarray) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=len(close_values)),
            "open": close_values,
            "high": close_values + 1.0,
            "low": close_values - 1.0,
            "close": close_values,
            "adj_close": close_values,
            "volume": np.full(len(close_values), 1000.0),
        }
    )


class ExitPriorityTest(unittest.TestCase):
    def test_resolve_full_exit_reason_prioritizes_stop_loss_over_ai_exit(self) -> None:
        reason = _resolve_full_exit_reason(
            unrealized_plpc=-0.08,
            stop_loss_pct=0.05,
            take_profit_pct=0.10,
            trailing_drawdown=0.06,
            trailing_stop_pct=0.05,
            signal="SELL",
            ai_exit_triggered=True,
        )

        self.assertEqual(reason, "stop loss triggered")

    def test_resolve_full_exit_reason_prioritizes_trailing_stop_over_sell_signal(self) -> None:
        reason = _resolve_full_exit_reason(
            unrealized_plpc=0.02,
            stop_loss_pct=0.05,
            take_profit_pct=0.10,
            trailing_drawdown=0.07,
            trailing_stop_pct=0.05,
            signal="SELL",
            ai_exit_triggered=False,
        )

        self.assertEqual(reason, "trailing stop triggered")

    def test_resolve_full_exit_reason_prioritizes_ai_exit_over_take_profit(self) -> None:
        reason = _resolve_full_exit_reason(
            unrealized_plpc=0.12,
            stop_loss_pct=0.05,
            take_profit_pct=0.10,
            trailing_drawdown=0.0,
            trailing_stop_pct=0.05,
            signal="HOLD",
            ai_exit_triggered=True,
        )

        self.assertEqual(reason, "ai exit triggered")

    def test_run_portfolio_backtest_uses_ai_exit_before_take_profit(self) -> None:
        rows = 90
        close_values = np.concatenate(
            [
                np.linspace(100.0, 125.0, 70),
                np.linspace(126.0, 135.0, 20),
            ]
        )
        stock_df = _price_frame(close_values)
        ai_scores = np.concatenate(
            [
                np.full(75, 0.9),
                np.full(15, 0.2),
            ]
        )
        ai_score_frame = pd.DataFrame(
            {
                "date": stock_df["date"],
                "ai_score": ai_scores,
            }
        )

        result, _, trades_df = run_portfolio_backtest(
            ticker_data={"AAPL": stock_df},
            initial_cash=10000.0,
            max_positions=1,
            target_position_pct=0.5,
            transaction_cost_pct=0.0,
            ma_fast=10,
            ma_slow=50,
            rsi_buy_limit=101,
            use_ai_score=True,
            ai_score_buy_threshold=0.55,
            ai_score_frames={"AAPL": ai_score_frame},
            stop_loss_pct=0.0,
            take_profit_pct=0.10,
            trailing_stop_pct=0.0,
            ai_exit_enabled=True,
            ai_exit_threshold=0.30,
        )

        self.assertGreaterEqual(result.trades, 1)
        self.assertIn("AI_EXIT", trades_df["exit_reason"].tolist())
        self.assertNotIn("TAKE_PROFIT", trades_df["exit_reason"].tolist())


if __name__ == "__main__":
    unittest.main()
