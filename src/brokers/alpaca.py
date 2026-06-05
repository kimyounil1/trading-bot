"""Alpaca paper broker adapter."""

from __future__ import annotations

from typing import Any, Optional

from src.brokers.base import BrokerAdapter, OrderSubmission
from src.market_clock import MarketClock


class AlpacaBrokerAdapter(BrokerAdapter):
    provider = "alpaca"

    def get_account(self) -> dict[str, Any]:
        from src.alpaca_client import get_account_summary

        return get_account_summary()

    def get_positions(self) -> list[dict[str, Any]]:
        from src.alpaca_client import get_positions_summary

        return get_positions_summary()

    def get_open_orders(self, *, limit: int = 100) -> list[dict[str, Any]]:
        from src.alpaca_client import get_open_orders

        return get_open_orders(limit=limit)

    def get_order_status(self, order_id: str) -> dict[str, Any]:
        from src.alpaca_client import get_order_summary

        return get_order_summary(order_id)

    def cancel_order(self, order_id: str) -> dict[str, Any]:
        from src.alpaca_client import cancel_order_by_id

        return cancel_order_by_id(order_id)

    def wait_for_order_status(
        self,
        order_id: str,
        *,
        max_attempts: int = 5,
        sleep_seconds: float = 1.0,
    ) -> dict[str, Any]:
        from src.alpaca_client import wait_for_order_status

        return wait_for_order_status(
            order_id,
            max_attempts=max_attempts,
            sleep_seconds=sleep_seconds,
        )

    def submit_buy_notional(
        self,
        ticker: str,
        notional: float,
        *,
        limit_price: float,
        market_clock: MarketClock,
        slippage_pct: float,
        client_order_id: Optional[str] = None,
    ) -> OrderSubmission:
        from src.alpaca_client import (
            submit_limit_buy_notional_order,
            submit_market_buy_notional_order,
        )

        if market_clock.is_regular_session:
            order = submit_market_buy_notional_order(
                ticker,
                notional,
                client_order_id=client_order_id,
            )
        else:
            order = submit_limit_buy_notional_order(
                ticker,
                notional,
                limit_price,
                slippage_pct=slippage_pct,
                client_order_id=client_order_id,
                extended_hours=True,
            )
        return OrderSubmission(
            order_id=str(order.id),
            status=str(order.status),
            side=str(order.side),
            order_type=str(order.type),
        )

    def submit_sell_qty(
        self,
        ticker: str,
        qty: float,
        *,
        limit_price: float,
        market_clock: MarketClock,
        slippage_pct: float,
        client_order_id: Optional[str] = None,
    ) -> OrderSubmission:
        from src.alpaca_client import close_position_by_symbol, submit_limit_sell_qty_order

        if market_clock.is_regular_session:
            order = close_position_by_symbol(
                ticker,
                qty=qty,
                client_order_id=client_order_id,
            )
        else:
            order = submit_limit_sell_qty_order(
                ticker,
                qty,
                limit_price,
                slippage_pct=slippage_pct,
                client_order_id=client_order_id,
                extended_hours=True,
            )
        if order is None:
            raise ValueError(f"No sell order submitted for {ticker}")
        return OrderSubmission(
            order_id=str(order.id),
            status=str(order.status),
            side=str(order.side),
            order_type=str(order.type),
        )
