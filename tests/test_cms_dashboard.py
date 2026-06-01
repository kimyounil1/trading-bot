import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pandas as pd

from src.broker_adapter import OrderSubmission
from src.cms_helpers import (
    cache_age_minutes,
    classify_buy_candidates,
    count_filled_today,
    is_executable_buy_row,
    money,
    order_display_columns,
    order_is_filled,
    orders_to_frame,
    partition_alpaca_orders,
    pct,
    sort_buy_candidates,
)
from src.trading_session import TradingSession


ROOT_DIR = Path(__file__).resolve().parents[1]


def _open_clock(*, orders_allowed: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        is_open=True,
        orders_allowed=orders_allowed,
        session=TradingSession.OVERNIGHT,
        timestamp="2026-06-01T04:00:00Z",
        next_open="2026-06-01T09:30:00-04:00",
        next_close="2026-06-01T16:00:00-04:00",
        broker_provider="alpaca",
        extended_hours_enabled=True,
    )


def _load_streamlit_app_module():
    st_mock = MagicMock()
    tab_cm = MagicMock()
    tab_cm.__enter__ = MagicMock(return_value=tab_cm)
    tab_cm.__exit__ = MagicMock(return_value=False)
    st_mock.tabs.side_effect = lambda labels: [tab_cm for _ in labels]

    def _columns_mock(spec):
        count = len(spec) if isinstance(spec, list) else int(spec)
        return [MagicMock() for _ in range(count)]

    st_mock.columns.side_effect = _columns_mock

    module_name = "cms_streamlit_app_test_module"
    with patch.dict(sys.modules, {"streamlit": st_mock}):
        if module_name in sys.modules:
            return sys.modules[module_name]
        spec = importlib.util.spec_from_file_location(
            module_name,
            ROOT_DIR / "app/streamlit_app.py",
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module


class CmsHelpersTest(unittest.TestCase):
    def test_money_and_pct_formatting(self) -> None:
        self.assertEqual(money(1234.5), "$1,234.50")
        self.assertEqual(pct(0.1234), "12.34%")

    def test_order_is_filled(self) -> None:
        self.assertTrue(order_is_filled("OrderStatus.FILLED"))
        self.assertFalse(order_is_filled("OrderStatus.PARTIALLY_FILLED"))
        self.assertFalse(order_is_filled("OrderStatus.CANCELED"))

    def test_is_executable_buy_row_respects_orders_allowed(self) -> None:
        row = pd.Series(
            {
                "order_amount": 100.0,
                "execution_label": "WOULD_SUBMIT_IF_EXECUTED",
            }
        )
        self.assertTrue(is_executable_buy_row(row, _open_clock(orders_allowed=True)))
        self.assertFalse(is_executable_buy_row(row, _open_clock(orders_allowed=False)))

    def test_is_executable_buy_row_rejects_zero_amount(self) -> None:
        row = pd.Series(
            {
                "order_amount": 0.0,
                "execution_label": "WOULD_SUBMIT_IF_EXECUTED",
            }
        )
        self.assertFalse(is_executable_buy_row(row, _open_clock()))

    def test_cache_age_minutes_handles_utc_and_naive_timestamps(self) -> None:
        now = pd.Timestamp("2026-06-01T05:00:00Z")
        age = cache_age_minutes("2026-06-01T04:30:00Z", now=now)
        self.assertAlmostEqual(age, 30.0, places=1)
        age_naive = cache_age_minutes("2026-06-01T04:30:00", now=now)
        self.assertAlmostEqual(age_naive, 30.0, places=1)
        self.assertEqual(cache_age_minutes(None, now=now), float("inf"))

    def test_orders_to_frame_preserves_columns(self) -> None:
        orders = [
            {
                "symbol": "AMT",
                "side": "BUY",
                "type": "LIMIT",
                "qty": "10",
                "filled_qty": "0",
                "fill_pct": 0.0,
                "limit_price": "215.5",
                "status_simple": "NEW",
                "extended_hours": True,
                "submitted_at": "2026-06-01T04:00:00Z",
                "id": "abc",
            }
        ]
        frame = orders_to_frame(orders, order_display_columns()["open"])
        self.assertEqual(frame.loc[0, "symbol"], "AMT")
        self.assertEqual(len(frame.columns), len(order_display_columns()["open"]))

    def test_partition_alpaca_orders(self) -> None:
        open_orders = [
            {"status_simple": "NEW"},
            {"status_simple": "PARTIALLY_FILLED"},
        ]
        closed_orders = [
            {"status": "OrderStatus.FILLED", "filled_at": "2026-06-01T04:00:00Z"},
            {"status": "OrderStatus.CANCELED"},
        ]
        filled, other, partial = partition_alpaca_orders(open_orders, closed_orders)
        self.assertEqual(len(filled), 1)
        self.assertEqual(len(other), 1)
        self.assertEqual(len(partial), 1)

    def test_count_filled_today(self) -> None:
        now = pd.Timestamp("2026-06-01T12:00:00Z")
        orders = [
            {"status": "OrderStatus.FILLED", "filled_at": "2026-06-01T10:00:00Z"},
            {"status": "OrderStatus.FILLED", "filled_at": "2026-05-31T10:00:00Z"},
            {"status": "OrderStatus.CANCELED", "filled_at": "2026-06-01T10:00:00Z"},
        ]
        self.assertEqual(count_filled_today(orders, now=now), 1)

    def test_classify_buy_candidates(self) -> None:
        clock = _open_clock()
        buy_df = pd.DataFrame(
            [
                {
                    "ticker": "AAPL",
                    "order_amount": 100.0,
                    "execution_label": "WOULD_SUBMIT_IF_EXECUTED",
                    "would_submit_if_execute": True,
                },
                {
                    "ticker": "MSFT",
                    "order_amount": 100.0,
                    "execution_label": "NOT_ALLOWED",
                    "would_submit_if_execute": False,
                },
                {
                    "ticker": "BAD",
                    "order_amount": 0.0,
                    "execution_label": "NOT_ALLOWED",
                    "error": "missing price data",
                },
            ]
        )
        executable, blocked, errors = classify_buy_candidates(buy_df, clock)
        self.assertEqual(executable["ticker"].tolist(), ["AAPL"])
        self.assertEqual(blocked["ticker"].tolist(), ["MSFT"])
        self.assertEqual(errors["ticker"].tolist(), ["BAD"])

    def test_sort_buy_candidates(self) -> None:
        buy_df = pd.DataFrame(
            {
                "ticker": ["A", "B", "C"],
                "ai_score": [0.4, 0.9, 0.6],
                "would_submit_if_execute": [False, True, True],
            }
        )
        sorted_df = sort_buy_candidates(buy_df)
        self.assertEqual(sorted_df.iloc[0]["ticker"], "B")


class CmsDashboardIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cms = _load_streamlit_app_module()

    def test_save_dry_run_snapshot_writes_sections(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            patched_root = Path(temp_dir)
            exit_df = pd.DataFrame({"ticker": ["NVDA"], "should_exit": [True]})
            buy_df = pd.DataFrame({"ticker": ["AAPL"], "signal": ["BUY"]})
            with patch.object(self.cms, "ROOT_DIR", patched_root):
                output_path = self.cms.save_dry_run_snapshot(exit_df, buy_df)

            self.assertTrue(output_path.exists())
            saved = pd.read_csv(output_path)
            self.assertEqual(set(saved["section"]), {"exit_check", "buy_check"})

    def test_get_recent_order_ids_from_log(self) -> None:
        log_df = pd.DataFrame(
            {
                "order_id": ["id-1", "id-2", "id-2", "id-3"],
                "ticker": ["A", "B", "B", "C"],
            }
        )
        with patch.object(self.cms, "read_csv_if_exists", return_value=log_df):
            order_ids = self.cms.get_recent_order_ids(limit=2)

        self.assertEqual(order_ids, ["id-2", "id-3"])

    def test_execute_cms_paper_actions_buy_and_exit(self) -> None:
        clock = _open_clock()
        settings = SimpleNamespace(
            broker_provider="alpaca",
            max_orders_per_run=2,
            extended_hours_limit_slippage_pct=0.005,
        )
        exit_df = pd.DataFrame(
            [{"ticker": "NVDA", "should_exit": True, "exit_reason": "stop loss"}]
        )
        buy_df = pd.DataFrame(
            [
                {
                    "ticker": "AAPL",
                    "order_amount": 100.0,
                    "close": 150.0,
                    "execution_label": "WOULD_SUBMIT_IF_EXECUTED",
                    "reason": "signal buy",
                }
            ]
        )
        mock_broker = MagicMock()
        mock_broker.submit_sell_qty.return_value = OrderSubmission(
            order_id="sell-1",
            status="ACCEPTED",
            side="SELL",
            order_type="LIMIT",
        )
        mock_broker.submit_buy_notional.return_value = OrderSubmission(
            order_id="buy-1",
            status="ACCEPTED",
            side="BUY",
            order_type="LIMIT",
        )

        with patch.object(
            self.cms,
            "get_broker_adapter",
            return_value=mock_broker,
        ), patch.object(
            self.cms,
            "get_positions_summary",
            return_value=[
                {
                    "symbol": "NVDA",
                    "qty": 2.0,
                    "current_price": 900.0,
                    "market_value": 1800.0,
                }
            ],
        ), patch.object(
            self.cms,
            "wait_for_order_status",
            side_effect=[
                {
                    "id": "sell-1",
                    "status": "OrderStatus.FILLED",
                    "side": "SELL",
                    "type": "LIMIT",
                    "filled_qty": "2",
                    "filled_avg_price": "900",
                },
                {
                    "id": "buy-1",
                    "status": "OrderStatus.NEW",
                    "side": "BUY",
                    "type": "LIMIT",
                    "filled_qty": "0",
                    "filled_avg_price": "0",
                },
            ],
        ), patch.object(self.cms, "log_order"), patch.object(self.cms, "log_order_status"):
            result = self.cms.execute_cms_paper_actions(exit_df, buy_df, settings, clock)

        self.assertEqual(len(result), 2)
        self.assertEqual(set(result["action"]), {"CLOSE", "BUY"})
        buy_row = result[result["action"] == "BUY"].iloc[0]
        self.assertEqual(buy_row["note"], "limit order pending (extended/overnight)")

    def test_execute_cms_paper_actions_blocks_when_session_closed(self) -> None:
        clock = _open_clock(orders_allowed=False)
        settings = SimpleNamespace(
            broker_provider="alpaca",
            max_orders_per_run=1,
            extended_hours_limit_slippage_pct=0.005,
        )
        with self.assertRaisesRegex(RuntimeError, "주문이 허용되지 않습니다"):
            self.cms.execute_cms_paper_actions(
                pd.DataFrame(),
                pd.DataFrame(),
                settings,
                clock,
            )

    def test_load_latest_candidate_cache_full_with_real_cache_if_present(self) -> None:
        cache_meta = ROOT_DIR / "logs/candidate_cache/latest_meta.json"
        if not cache_meta.exists():
            self.skipTest("candidate cache not generated yet")

        meta, exit_df, buy_df, quality_df, errors_df = (
            self.cms.load_latest_candidate_cache_full()
        )
        self.assertIn("generated_at", meta)
        self.assertIsInstance(buy_df, pd.DataFrame)
        self.assertIsInstance(quality_df, pd.DataFrame)
        self.assertIsInstance(errors_df, pd.DataFrame)

    def test_render_alpaca_order_board_smoke(self) -> None:
        open_orders = [
            {
                "symbol": "AMT",
                "side": "BUY",
                "type": "LIMIT",
                "qty": "10",
                "filled_qty": "0",
                "fill_pct": 0.0,
                "limit_price": "215.5",
                "status": "OrderStatus.NEW",
                "status_simple": "NEW",
                "extended_hours": True,
                "submitted_at": "2026-06-01T04:00:00Z",
                "id": "abc",
            }
        ]
        closed_orders = [
            {
                "symbol": "DIA",
                "side": "BUY",
                "type": "MARKET",
                "qty": "1",
                "filled_qty": "1",
                "filled_avg_price": "420.1",
                "status": "OrderStatus.FILLED",
                "status_simple": "FILLED",
                "extended_hours": False,
                "submitted_at": "2026-06-01T03:00:00Z",
                "filled_at": "2026-06-01T03:01:00Z",
                "id": "def",
            }
        ]
        with patch.object(self.cms, "get_open_orders", return_value=open_orders), patch.object(
            self.cms,
            "get_recent_closed_orders",
            return_value=closed_orders,
        ), patch.object(self.cms, "read_csv_if_exists", return_value=pd.DataFrame()):
            self.cms.render_alpaca_order_board(closed_limit=20)


class CmsCandidateCacheDashboardTest(unittest.TestCase):
    def test_generate_candidate_cache_module_runs(self) -> None:
        cache_meta = ROOT_DIR / "logs/candidate_cache/latest_meta.json"
        if not cache_meta.exists():
            self.skipTest("candidate cache not generated yet")

        meta = json.loads(cache_meta.read_text(encoding="utf-8"))
        self.assertIn("orders_allowed", meta)
        self.assertIn("trading_session", meta)

        buy_df = pd.read_csv(ROOT_DIR / "logs/candidate_cache/latest_buy.csv")
        if buy_df.empty:
            return
        self.assertIn("execution_label", buy_df.columns)
        self.assertIn("ai_score_status", buy_df.columns)


if __name__ == "__main__":
    unittest.main()
