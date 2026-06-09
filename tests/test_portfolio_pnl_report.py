"""Tests for live portfolio P&L snapshot."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

import pandas as pd

from src.portfolio_pnl_report import (
    compute_fifo_realized_pnl,
    compute_period_pnls,
    format_positions,
    merge_trade_history,
    portfolio_history_to_frame,
)


class PortfolioPnlReportTest(unittest.TestCase):
    def test_compute_period_pnls(self) -> None:
        now = datetime(2026, 6, 9, tzinfo=timezone.utc)
        history = pd.DataFrame(
            {
                "date": pd.to_datetime(
                    ["2026-06-01", "2026-06-05", "2026-06-08"],
                    utc=True,
                ),
                "equity": [100_000.0, 101_000.0, 99_000.0],
            }
        )
        today, week, month, all_time = compute_period_pnls(
            current_equity=98_500.0,
            last_equity=99_000.0,
            history_1w=history,
            history_1m=history,
            history_all=history,
            now=now,
        )
        self.assertEqual(today.pnl_usd, -500.0)
        self.assertLess(today.pnl_pct, 0)
        self.assertEqual(all_time.start_equity, 100_000.0)
        self.assertEqual(all_time.end_equity, 98_500.0)

    def test_format_positions(self) -> None:
        rows = format_positions(
            [
                {
                    "symbol": "AAPL",
                    "qty": 10,
                    "current_price": 200.0,
                    "market_value": 2000.0,
                    "cost_basis": 1800.0,
                    "unrealized_pl": 200.0,
                    "unrealized_plpc": 0.1111,
                }
            ]
        )
        self.assertEqual(rows[0]["ticker"], "AAPL")
        self.assertEqual(rows[0]["avg_cost"], 180.0)
        self.assertAlmostEqual(rows[0]["unrealized_plpc"], 11.11, places=1)

    def test_merge_trade_history_dedupes_order_id(self) -> None:
        alpaca = [
            {
                "timestamp": "2026-06-08T10:00:00Z",
                "ticker": "AAPL",
                "side": "BUY",
                "side_ko": "매수",
                "qty": 1,
                "price": 100,
                "notional": 100,
                "order_id": "abc",
                "status": "FILLED",
                "reason": "",
                "source": "alpaca",
            }
        ]
        csv_rows = [
            {
                "timestamp": "2026-06-08T09:00:00Z",
                "ticker": "AAPL",
                "side": "BUY",
                "side_ko": "매수",
                "qty": 1,
                "price": 100,
                "notional": 100,
                "order_id": "abc",
                "status": "FILLED",
                "reason": "old",
                "source": "orders_csv",
            }
        ]
        merged = merge_trade_history(alpaca, csv_rows, limit=10)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["source"], "alpaca")

    def test_portfolio_history_to_frame(self) -> None:
        class Hist:
            timestamp = [1_700_000_000, 1_700_086_400]
            equity = [100_000.0, 100_500.0]
            profit_loss = [0.0, 500.0]
            profit_loss_pct = [0.0, 0.005]

        frame = portfolio_history_to_frame(Hist())
        self.assertEqual(len(frame), 2)
        self.assertEqual(float(frame["equity"].iloc[-1]), 100_500.0)

    def test_compute_fifo_realized_pnl(self) -> None:
        trades = [
            {
                "timestamp": "2026-06-01T10:00:00Z",
                "ticker": "AAPL",
                "side": "BUY",
                "qty": 10,
                "price": 100.0,
                "order_id": "b1",
                "reason": "",
            },
            {
                "timestamp": "2026-06-02T10:00:00Z",
                "ticker": "AAPL",
                "side": "SELL",
                "qty": 10,
                "price": 110.0,
                "order_id": "s1",
                "reason": "take profit",
            },
        ]
        summary = compute_fifo_realized_pnl(
            trades,
            now=datetime(2026, 6, 2, 12, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(summary.total_usd, 100.0)
        self.assertEqual(summary.by_ticker[0]["ticker"], "AAPL")
        self.assertEqual(summary.by_ticker[0]["realized_pl"], 100.0)
        self.assertEqual(len(summary.events), 1)
        self.assertEqual(summary.events[0]["return_pct"], 10.0)


if __name__ == "__main__":
    unittest.main()
