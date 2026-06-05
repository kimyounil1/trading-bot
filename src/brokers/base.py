"""Broker adapter contract (Alpaca, paper/fake, Toss stub)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

from src.market_clock import MarketClock


@dataclass(frozen=True)
class OrderSubmission:
    order_id: str
    status: str
    side: str
    order_type: str


class BrokerAdapter(ABC):
    """Minimal broker surface for account reads and order lifecycle."""

    provider: str

    @abstractmethod
    def get_account(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_positions(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    def get_open_symbols(self) -> set[str]:
        return {str(position["symbol"]).upper() for position in self.get_positions()}

    @abstractmethod
    def get_open_orders(self, *, limit: int = 100) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_order_status(self, order_id: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def cancel_order(self, order_id: str) -> dict[str, Any]:
        raise NotImplementedError

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

    def wait_for_order_status(
        self,
        order_id: str,
        *,
        max_attempts: int = 5,
        sleep_seconds: float = 1.0,
    ) -> dict[str, Any]:
        raise NotImplementedError(f"{self.provider} does not implement wait_for_order_status")

    def is_live_capable(self) -> bool:
        """False for stubs/fake brokers that must not back live trading."""
        return True
