"""Regression tests for sleeve rebalance sell execution (2026-07-07 SELL_ERROR).

The production bug: _execute_sell_actions called broker.submit_sell_qty without the
keyword-only limit_price, crashing every tournament overweight trim. The fake broker
here mirrors the real AlpacaBrokerAdapter signature so a missing kwarg fails again.
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from typing import Optional

from src.sleeve_rebalance import SleeveRebalanceAction
from src.trading.sleeve_rebalance_pipeline import _execute_sell_actions


class _FakeSubmission(SimpleNamespace):
    pass


class _FakeBroker:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def submit_sell_qty(
        self,
        ticker: str,
        qty: float,
        *,
        limit_price: float,
        market_clock,
        slippage_pct: float,
        client_order_id: Optional[str] = None,
    ):
        self.calls.append(
            {"ticker": ticker, "qty": qty, "limit_price": limit_price}
        )
        return _FakeSubmission(
            order_id="o1", status="FILLED", side="sell", order_type="limit"
        )

    def wait_for_order_status(self, order_id: str) -> dict:
        return {
            "id": order_id,
            "status": "FILLED",
            "side": "sell",
            "type": "limit",
            "filled_qty": "1",
            "filled_avg_price": "10.0",
        }


class _FakeSleeveCtx:
    def audit_fields(self, *, sleeve_id: str) -> dict:
        return {}

    def record_exit(self, ticker: str) -> None:
        pass


class _FakeAuditCtx:
    def as_audit_fields(self) -> dict:
        return {}


def _make_ctx(positions: dict) -> SimpleNamespace:
    return SimpleNamespace(
        can_submit_orders=True,
        execute_orders=True,
        market_clock=SimpleNamespace(is_regular_session=True),
        extended_slippage=0.002,
        run_id="test-run",
        profile_name="TEST_PROFILE",
        current_regime="BULL",
        positions_by_symbol=positions,
        broker_adapter=_FakeBroker(),
        sleeve_ctx=_FakeSleeveCtx(),
        audit_ctx=_FakeAuditCtx(),
        exit_summary_rows=[],
        live_order_count=0,
        api_error_count=0,
    )


class SleeveRebalanceSellTest(unittest.TestCase):
    def test_trim_passes_limit_price_from_position(self) -> None:
        ctx = _make_ctx({"BB": {"qty": 100.0, "current_price": 4.2}})
        actions = [
            SleeveRebalanceAction(
                ticker="BB", sleeve_id="tournament", sell_qty=10.0, reason="trim"
            )
        ]
        _execute_sell_actions(ctx, actions, event_prefix="SLEEVE_TRIM")
        self.assertEqual(len(ctx.broker_adapter.calls), 1)
        self.assertAlmostEqual(ctx.broker_adapter.calls[0]["limit_price"], 4.2)
        self.assertEqual(ctx.api_error_count, 0)
        self.assertEqual(ctx.live_order_count, 1)

    def test_trim_skips_when_price_missing(self) -> None:
        ctx = _make_ctx({"BB": {"qty": 100.0}})
        actions = [
            SleeveRebalanceAction(
                ticker="BB", sleeve_id="tournament", sell_qty=10.0, reason="trim"
            )
        ]
        _execute_sell_actions(ctx, actions, event_prefix="SLEEVE_TRIM")
        self.assertEqual(len(ctx.broker_adapter.calls), 0)
        self.assertEqual(ctx.api_error_count, 0)
        self.assertTrue(any("no current price" in row for row in ctx.exit_summary_rows))


if __name__ == "__main__":
    unittest.main()
