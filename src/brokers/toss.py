"""Toss Securities Open API placeholder."""

from __future__ import annotations

from typing import Any, Optional

from src.brokers.base import BrokerAdapter, OrderSubmission
from src.market_clock import MarketClock

_STUB_MSG = (
    "Toss Securities Open API is not wired yet. "
    "Set broker_provider='alpaca' until Toss integration lands."
)


class TossBrokerAdapter(BrokerAdapter):
    provider = "toss"

    def is_live_capable(self) -> bool:
        return False

    def _stub(self) -> None:
        raise NotImplementedError(_STUB_MSG)

    def get_account(self) -> dict[str, Any]:
        self._stub()

    def get_positions(self) -> list[dict[str, Any]]:
        self._stub()

    def get_open_orders(self, *, limit: int = 100) -> list[dict[str, Any]]:
        self._stub()

    def get_order_status(self, order_id: str) -> dict[str, Any]:
        self._stub()

    def cancel_order(self, order_id: str) -> dict[str, Any]:
        self._stub()

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
        self._stub()

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
        self._stub()
