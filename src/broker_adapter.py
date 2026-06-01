"""Broker adapters: Alpaca today, Toss stub for future Open API."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from src.market_clock import MarketClock


@dataclass(frozen=True)
class OrderSubmission:
    order_id: str
    status: str
    side: str
    order_type: str


class BrokerAdapter(ABC):
    provider: str

    @abstractmethod
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
        raise NotImplementedError

    @abstractmethod
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
        raise NotImplementedError


class AlpacaBrokerAdapter(BrokerAdapter):
    provider = "alpaca"

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


class TossBrokerAdapter(BrokerAdapter):
    """Placeholder for future Toss Securities Open API integration."""

    provider = "toss"

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
        raise NotImplementedError(
            "Toss Securities Open API is not wired yet. "
            "Set broker_provider='alpaca' until Toss integration lands."
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
        raise NotImplementedError(
            "Toss Securities Open API is not wired yet. "
            "Set broker_provider='alpaca' until Toss integration lands."
        )


def get_broker_adapter(provider: str) -> BrokerAdapter:
    normalized = str(provider).strip().lower()
    if normalized == "toss":
        return TossBrokerAdapter()
    if normalized != "alpaca":
        raise ValueError(f"Unsupported broker_provider: {provider}")
    return AlpacaBrokerAdapter()
