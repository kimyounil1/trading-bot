from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.brokers.alpaca import AlpacaBrokerAdapter
from src.brokers.base import OrderSubmission
from src.brokers.paper import PaperBrokerAdapter
from src.market_clock import MarketClock
from src.trading.exit_pipeline import _cleanup_dust_position
from src.trading_session import TradingSession


def _clock(session: TradingSession) -> MarketClock:
    return MarketClock(
        is_open=session == TradingSession.REGULAR,
        timestamp="2026-07-13T10:00:00-04:00",
        next_open="",
        next_close="",
        session=session,
        orders_allowed=True,
    )


def test_alpaca_regular_full_exit_uses_close_position_api() -> None:
    order = MagicMock(id="o1", status="filled", side="sell", type="market")
    with patch(
        "src.alpaca_client.close_position_by_symbol", return_value=order
    ) as close_position:
        submission = AlpacaBrokerAdapter().submit_sell_qty(
            "AAPL",
            15.8465388,
            limit_price=100.0,
            market_clock=_clock(TradingSession.REGULAR),
            slippage_pct=0.005,
            client_order_id="exit_1_AAPL",
            close_all=True,
        )

    assert submission.order_id == "o1"
    close_position.assert_called_once_with(
        "AAPL",
        qty=None,
        client_order_id="exit_1_AAPL",
        close_all=True,
    )


def test_alpaca_extended_full_exit_preserves_full_close_mode() -> None:
    order = MagicMock(id="o2", status="new", side="sell", type="limit")
    with patch(
        "src.alpaca_client.submit_limit_sell_qty_order", return_value=order
    ) as submit_limit:
        AlpacaBrokerAdapter().submit_sell_qty(
            "AAPL",
            0.000000497,
            limit_price=100.0,
            market_clock=_clock(TradingSession.OVERNIGHT),
            slippage_pct=0.005,
            client_order_id="dust_1_AAPL",
            close_all=True,
        )

    assert submit_limit.call_args.kwargs["close_all"] is True


def test_paper_full_exit_removes_fractional_remainder() -> None:
    broker = PaperBrokerAdapter(cash=1_000.0, prices={"AAPL": 3.0})
    broker.submit_buy_notional(
        "AAPL",
        100.0,
        limit_price=3.0,
        market_clock=_clock(TradingSession.REGULAR),
        slippage_pct=0.0,
    )
    position = broker.get_positions()[0]

    broker.submit_sell_qty(
        "AAPL",
        float(position["qty"]) - 0.0000004,
        limit_price=3.0,
        market_clock=_clock(TradingSession.REGULAR),
        slippage_pct=0.0,
        close_all=True,
    )

    assert broker.get_positions() == []


def test_dust_cleanup_skips_duplicate_open_sell_order() -> None:
    broker = MagicMock()
    sleeve_ctx = SimpleNamespace(
        open_orders=[
            {
                "id": "pending-1",
                "symbol": "RBLX",
                "side": "SELL",
                "status": "ACCEPTED",
            }
        ],
        record_exit=MagicMock(),
    )
    ctx = SimpleNamespace(
        dust_min_usd=5.0,
        exit_summary_rows=[],
        sleeve_ctx=sleeve_ctx,
        audit_ctx=SimpleNamespace(as_audit_fields=lambda: {}),
        profile_name="TEST",
        current_regime="BULL",
        can_submit_orders=True,
        broker_adapter=broker,
        market_clock=_clock(TradingSession.OVERNIGHT),
        extended_slippage=0.005,
        run_id="run1",
        live_order_count=0,
        api_error_count=0,
        execute_orders=True,
        positions_by_symbol={"RBLX": {}},
        open_symbols={"RBLX"},
        guard_open_symbols=set(),
        partial_exit_taken={},
    )

    handled = _cleanup_dust_position(
        ctx,
        {"symbol": "RBLX", "qty": 0.000000497, "market_value": 0.00003},
    )

    assert handled is True
    broker.submit_sell_qty.assert_not_called()


def test_dust_cleanup_records_pending_instead_of_claiming_fill() -> None:
    broker = MagicMock()
    broker.submit_sell_qty.return_value = OrderSubmission(
        order_id="pending-2", status="ACCEPTED", side="SELL", order_type="LIMIT"
    )
    broker.wait_for_order_status.return_value = {
        "id": "pending-2",
        "status": "NEW",
        "side": "SELL",
        "type": "LIMIT",
        "filled_qty": "0",
        "filled_avg_price": "",
    }
    sleeve_ctx = SimpleNamespace(open_orders=[], record_exit=MagicMock())
    ctx = SimpleNamespace(
        dust_min_usd=5.0,
        exit_summary_rows=[],
        sleeve_ctx=sleeve_ctx,
        audit_ctx=SimpleNamespace(as_audit_fields=lambda: {}),
        profile_name="TEST",
        current_regime="BULL",
        can_submit_orders=True,
        broker_adapter=broker,
        market_clock=_clock(TradingSession.OVERNIGHT),
        extended_slippage=0.005,
        run_id="run1",
        live_order_count=0,
        api_error_count=0,
        execute_orders=True,
        positions_by_symbol={"RBLX": {}},
        open_symbols={"RBLX"},
        guard_open_symbols=set(),
        partial_exit_taken={},
    )

    _cleanup_dust_position(
        ctx,
        {
            "symbol": "RBLX",
            "qty": 0.000000497,
            "market_value": 0.00003,
            "current_price": 55.0,
        },
    )

    assert broker.submit_sell_qty.call_args.kwargs["close_all"] is True
    sleeve_ctx.record_exit.assert_not_called()
    assert sleeve_ctx.open_orders[0]["id"] == "pending-2"
