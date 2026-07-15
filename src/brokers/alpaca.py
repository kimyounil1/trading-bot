"""Alpaca paper broker adapter."""

from __future__ import annotations

from math import floor
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

    def get_asset_info(self, ticker: str) -> dict[str, Any]:
        from src.alpaca_client import get_asset_summary

        return get_asset_summary(ticker)

    def discover_leveraged_long_products(
        self,
        underlying: str,
    ) -> list[dict[str, Any]]:
        from src.alpaca_client import discover_leveraged_long_assets

        return discover_leveraged_long_assets(underlying)

    def get_open_orders(self, *, limit: int = 100) -> list[dict[str, Any]]:
        from src.alpaca_client import get_open_orders

        return get_open_orders(limit=limit)

    def get_recent_closed_orders(self, *, limit: int = 50) -> list[dict[str, Any]]:
        from src.alpaca_client import get_recent_closed_orders

        return get_recent_closed_orders(limit=limit)

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
            get_asset_summary,
            submit_limit_buy_notional_order,
            submit_market_buy_qty_order,
            submit_market_buy_notional_order,
        )

        asset = get_asset_summary(ticker)
        if not asset["active"] or not asset["tradable"]:
            raise ValueError(f"Asset is not tradable: {ticker}")
        fractionable = bool(asset["fractionable"])

        if market_clock.is_regular_session and fractionable:
            order = submit_market_buy_notional_order(
                ticker,
                notional,
                client_order_id=client_order_id,
            )
        elif market_clock.is_regular_session:
            order = submit_market_buy_qty_order(
                ticker,
                notional,
                reference_price=limit_price,
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
                whole_shares=not fractionable,
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
        close_all: bool = False,
    ) -> OrderSubmission:
        from src.alpaca_client import (
            close_position_by_symbol,
            get_asset_summary,
            submit_limit_sell_qty_order,
        )

        if not close_all:
            asset = get_asset_summary(ticker)
            if not asset["active"] or not asset["tradable"]:
                raise ValueError(f"Asset is not tradable: {ticker}")
            if not bool(asset["fractionable"]):
                qty = float(floor(qty))
                if qty <= 0:
                    raise ValueError(
                        f"Non-fractionable sell quantity is below one share: {ticker}"
                    )

        if market_clock.is_regular_session:
            order = close_position_by_symbol(
                ticker,
                qty=None if close_all else qty,
                client_order_id=client_order_id,
                close_all=close_all,
            )
        else:
            order = submit_limit_sell_qty_order(
                ticker,
                qty,
                limit_price,
                slippage_pct=slippage_pct,
                client_order_id=client_order_id,
                extended_hours=True,
                close_all=close_all,
            )
        if order is None:
            raise ValueError(f"No sell order submitted for {ticker}")
        return OrderSubmission(
            order_id=str(order.id),
            status=str(order.status),
            side=str(order.side),
            order_type=str(order.type),
        )
