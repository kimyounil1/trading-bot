"""In-memory fake broker for tests and dry-run adapter checks."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from src.brokers.base import BrokerAdapter, OrderSubmission
from src.market_clock import MarketClock


@dataclass
class _PaperPosition:
    symbol: str
    qty: float
    current_price: float

    @property
    def market_value(self) -> float:
        return self.qty * self.current_price

    def to_summary(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "qty": self.qty,
            "current_price": self.current_price,
            "market_value": self.market_value,
            "cost_basis": self.market_value,
            "unrealized_pl": 0.0,
            "unrealized_plpc": 0.0,
        }


@dataclass
class _PaperOrder:
    order_id: str
    client_order_id: str
    symbol: str
    side: str
    order_type: str
    status: str
    notional: float = 0.0
    qty: float = 0.0
    limit_price: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.order_id,
            "client_order_id": self.client_order_id,
            "symbol": self.symbol,
            "status": self.status,
            "status_simple": self.status.upper(),
            "side": self.side,
            "type": self.order_type,
            "qty": str(self.qty) if self.qty else "",
            "filled_qty": str(self.qty) if self.status == "FILLED" else "0",
            "notional": str(self.notional) if self.notional else "",
            "limit_price": str(self.limit_price) if self.limit_price else "",
        }


@dataclass
class PaperBrokerAdapter(BrokerAdapter):
    """Deterministic broker with no external API."""

    provider: str = "paper"
    cash: float = 100_000.0
    last_equity: float = 100_000.0
    prices: dict[str, float] = field(default_factory=dict)
    positions: dict[str, _PaperPosition] = field(default_factory=dict)
    orders: dict[str, _PaperOrder] = field(default_factory=dict)
    client_ids: set[str] = field(default_factory=set)
    fail_submit: bool = False

    def is_live_capable(self) -> bool:
        return False

    def _portfolio_value(self) -> float:
        pos_value = sum(p.market_value for p in self.positions.values())
        return self.cash + pos_value

    def get_account(self) -> dict[str, Any]:
        pv = self._portfolio_value()
        return {
            "account_number": "paper-0001",
            "status": "ACTIVE",
            "currency": "USD",
            "cash": float(self.cash),
            "portfolio_value": float(pv),
            "last_equity": float(self.last_equity),
            "buying_power": float(self.cash),
            "positions_count": len(self.positions),
        }

    def get_positions(self) -> list[dict[str, Any]]:
        return [p.to_summary() for p in self.positions.values()]

    def get_open_orders(self, *, limit: int = 100) -> list[dict[str, Any]]:
        open_statuses = {"NEW", "ACCEPTED", "PENDING_NEW", "PARTIALLY_FILLED"}
        rows = [
            o.to_dict()
            for o in self.orders.values()
            if o.status.upper() in open_statuses
        ]
        return rows[:limit]

    def get_recent_closed_orders(self, *, limit: int = 50) -> list[dict[str, Any]]:
        open_statuses = {"NEW", "ACCEPTED", "PENDING_NEW", "PARTIALLY_FILLED"}
        rows = [
            o.to_dict()
            for o in self.orders.values()
            if o.status.upper() not in open_statuses
        ]
        return list(reversed(rows[-limit:]))

    def get_order_status(self, order_id: str) -> dict[str, Any]:
        order = self.orders[order_id]
        summary = order.to_dict()
        return {
            "id": summary["id"],
            "symbol": summary["symbol"],
            "status": summary["status"],
            "side": summary["side"],
            "type": summary["type"],
            "notional": summary.get("notional", ""),
            "qty": summary.get("qty", ""),
            "filled_qty": summary.get("filled_qty", ""),
            "filled_avg_price": "",
            "limit_price": summary.get("limit_price", ""),
            "extended_hours": False,
            "submitted_at": "",
            "filled_at": "",
        }

    def cancel_order(self, order_id: str) -> dict[str, Any]:
        order = self.orders[order_id]
        order.status = "CANCELED"
        return self.get_order_status(order_id)

    def wait_for_order_status(
        self,
        order_id: str,
        *,
        max_attempts: int = 5,
        sleep_seconds: float = 1.0,
    ) -> dict[str, Any]:
        summary = self.get_order_status(order_id)
        return {
            "id": summary["id"],
            "symbol": summary["symbol"],
            "status": summary["status"],
            "side": summary["side"],
            "type": summary["type"],
            "filled_qty": summary.get("filled_qty") or "0",
            "filled_avg_price": summary.get("filled_avg_price") or "",
        }

    def _price(self, ticker: str, limit_price: float) -> float:
        key = str(ticker).upper()
        if key in self.prices and self.prices[key] > 0:
            return float(self.prices[key])
        if limit_price > 0:
            return float(limit_price)
        return 100.0

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
        if self.fail_submit:
            raise ConnectionError("paper broker submit failure (test)")
        cid = client_order_id or f"paper_{uuid.uuid4().hex[:12]}"
        if cid in self.client_ids:
            existing = next(
                (o for o in self.orders.values() if o.client_order_id == cid),
                None,
            )
            if existing is not None:
                return OrderSubmission(
                    order_id=existing.order_id,
                    status=existing.status,
                    side=existing.side,
                    order_type=existing.order_type,
                )
        if notional <= 0:
            raise ValueError("notional must be positive")

        price = self._price(ticker, limit_price)
        qty = notional / price
        symbol = str(ticker).upper()
        pos = self.positions.get(symbol)
        if pos is None:
            self.positions[symbol] = _PaperPosition(symbol=symbol, qty=qty, current_price=price)
        else:
            pos.qty += qty
            pos.current_price = price

        self.cash = max(0.0, self.cash - notional)
        order_id = f"paper_ord_{uuid.uuid4().hex[:10]}"
        order = _PaperOrder(
            order_id=order_id,
            client_order_id=cid,
            symbol=symbol,
            side="buy",
            order_type="market" if market_clock.is_regular_session else "limit",
            status="FILLED",
            notional=notional,
            qty=qty,
            limit_price=limit_price,
        )
        self.orders[order_id] = order
        self.client_ids.add(cid)
        return OrderSubmission(
            order_id=order_id,
            status=order.status,
            side=order.side,
            order_type=order.order_type,
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
        if self.fail_submit:
            raise ConnectionError("paper broker submit failure (test)")
        cid = client_order_id or f"paper_{uuid.uuid4().hex[:12]}"
        if cid in self.client_ids:
            existing = next(
                (o for o in self.orders.values() if o.client_order_id == cid),
                None,
            )
            if existing is not None:
                return OrderSubmission(
                    order_id=existing.order_id,
                    status=existing.status,
                    side=existing.side,
                    order_type=existing.order_type,
                )
        symbol = str(ticker).upper()
        pos = self.positions.get(symbol)
        if pos is None or qty <= 0:
            raise ValueError(f"No position to sell for {ticker}")
        sell_qty = min(qty, pos.qty)
        price = self._price(ticker, limit_price)
        pos.qty -= sell_qty
        if pos.qty <= 1e-9:
            del self.positions[symbol]
        self.cash += sell_qty * price

        order_id = f"paper_ord_{uuid.uuid4().hex[:10]}"
        order = _PaperOrder(
            order_id=order_id,
            client_order_id=cid,
            symbol=symbol,
            side="sell",
            order_type="market" if market_clock.is_regular_session else "limit",
            status="FILLED",
            qty=sell_qty,
            limit_price=limit_price,
        )
        self.orders[order_id] = order
        self.client_ids.add(cid)
        return OrderSubmission(
            order_id=order_id,
            status=order.status,
            side=order.side,
            order_type=order.order_type,
        )
