import unittest
from unittest.mock import patch

import pandas as pd

from src.portfolio_backtester import PortfolioBacktestResult
from src.settings import StrategySettings
from src.train_ai_model import _run_threshold_retune


def _sample_frame(rows: int = 320) -> pd.DataFrame:
    values = list(range(rows))
    return pd.DataFrame(
        {
            "date": pd.date_range("2025-01-01", periods=rows),
            "open": values,
            "high": [v + 1 for v in values],
            "low": [v - 1 for v in values],
            "close": [100 + v for v in values],
            "volume": [1000 + v for v in values],
        }
    )


class ThresholdRetuneTest(unittest.TestCase):
    def test_run_threshold_retune_picks_best_threshold_pair(self) -> None:
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
            use_ai_score=True,
            ai_score_buy_threshold=0.55,
            market_regime_filter_enabled=False,
            market_regime_ticker="SPY",
            market_regime_ma_fast=50,
            market_regime_ma_slow=200,
            ai_exit_enabled=True,
            ai_exit_dynamic_enabled=False,
        )
        ticker_data = {"AAPL": _sample_frame()}

        def fake_backtest(**kwargs):
            buy_thr = float(kwargs["ai_score_buy_threshold"])
            exit_thr = float(kwargs["ai_exit_threshold"])
            total_return = 1.0 - abs(buy_thr - 0.50) - abs(exit_thr - 0.30)
            return (
                PortfolioBacktestResult(
                    initial_cash=10000.0,
                    final_equity=10000.0 * (1.0 + total_return),
                    total_return=total_return,
                    max_drawdown=-0.10,
                    trades=10,
                    win_rate=0.60,
                    benchmark_return=0.10,
                    sharpe_ratio=total_return,
                ),
                pd.DataFrame(),
                pd.DataFrame(),
            )

        with patch("src.train_ai_model.run_portfolio_backtest", side_effect=fake_backtest):
            report, results_df = _run_threshold_retune(
                settings=settings,
                ticker_data=ticker_data,
                vix_df=None,
                macro_df=None,
            )

        self.assertEqual(report["best_buy_threshold"], 0.50)
        self.assertEqual(report["best_exit_threshold"], 0.30)
        self.assertFalse(results_df.empty)


if __name__ == "__main__":
    unittest.main()
