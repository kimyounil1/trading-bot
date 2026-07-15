"""Toss Securities Open API broker adapter — read-only phase.

Read paths (account, holdings, orders, quotes) are wired to the live Toss
Open API via src.brokers.toss_client. Order mutations (submit/cancel) remain
guarded stubs so the adapter cannot place a live order until explicitly built
and reviewed. is_live_capable() stays False until then.
"""

from __future__ import annotations

from typing import Any, Optional

from src.brokers.base import BrokerAdapter, OrderSubmission
from src.brokers.toss_client import (
    get_buying_power,
    get_holdings,
    get_order,
    get_orders,
    get_stocks,
    resolve_account_seq,
)
from src.market_clock import MarketClock

_ORDER_STUB_MSG = (
    "Toss order mutation is not implemented (read-only phase). "
    "Reads (account/holdings/orders/quotes) are live; order submit/cancel are "
    "intentionally disabled until the order path is built and reviewed."
)

_OPEN_ORDER_STATUS = "OPEN"
_CLOSED_ORDER_STATUS = "CLOSED"


def _first(mapping: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if mapping.get(key) not in (None, ""):
            return mapping[key]
    return default


def _amount(value: Any) -> Any:
    """Toss money fields may be a scalar or {'amount': ...} object."""
    if isinstance(value, dict):
        return _first(value, "amount", "value")
    return value


class TossBrokerAdapter(BrokerAdapter):
    provider = "toss"

    def is_live_capable(self) -> bool:
        # Reads are live, but order submission is not implemented yet.
        return False

    def get_account(self) -> dict[str, Any]:
        account_seq = resolve_account_seq()
        buying_power = get_buying_power()
        return {
            "provider": "toss",
            "account_seq": account_seq,
            "buying_power": buying_power,
        }

    def get_positions(self) -> list[dict[str, Any]]:
        positions: list[dict[str, Any]] = []
        for holding in get_holdings():
            symbol = _first(holding, "symbol", "ticker", "stockCode", "code", default="")
            qty = _first(holding, "quantity", "qty", "balanceQuantity", "holdingQuantity", default=0)
            avg_price = _first(
                holding,
                "averagePurchasePrice",
                "averagePrice",
                "avgPrice",
                "purchasePrice",
            )
            profit_loss = holding.get("profitLoss")
            positions.append(
                {
                    "symbol": str(symbol).upper(),
                    "market": _first(holding, "marketCountry", "market", default=""),
                    "currency": _first(holding, "currency", default=""),
                    "qty": qty,
                    "avg_price": avg_price,
                    "last_price": _first(holding, "lastPrice", "currentPrice"),
                    "market_value": _amount(
                        _first(holding, "marketValue", "evaluationAmount", "valuation")
                    ),
                    "pnl": _amount(profit_loss) if profit_loss is not None else None,
                    "pnl_rate": profit_loss.get("rate") if isinstance(profit_loss, dict) else None,
                    "_raw": holding,
                }
            )
        return positions

    def get_asset_info(self, ticker: str) -> dict[str, Any]:
        symbol = str(ticker).strip().upper()
        rows = get_stocks([symbol])
        if not rows:
            return {
                "symbol": symbol,
                "active": False,
                "tradable": False,
                "fractionable": False,
            }
        row = rows[0]
        status = str(row.get("status") or "").upper()
        leverage_raw = row.get("leverageFactor")
        try:
            leverage_factor = float(leverage_raw) if leverage_raw not in (None, "") else 1.0
        except (TypeError, ValueError):
            leverage_factor = 1.0
        return {
            "symbol": symbol,
            "name": str(row.get("englishName") or row.get("name") or ""),
            "active": status == "ACTIVE",
            "tradable": status == "ACTIVE",
            "fractionable": False,
            "marginable": False,
            "security_type": str(row.get("securityType") or "").upper(),
            "leverage_factor": leverage_factor,
            "market": str(row.get("market") or ""),
        }

    def discover_leveraged_long_products(
        self,
        underlying: str,
    ) -> list[dict[str, Any]]:
        # Toss can validate known symbols but cannot enumerate its stock master.
        # Use Alpaca's US-equity catalog for discovery, then verify every result
        # against Toss's live /stocks metadata before returning it.
        from src.alpaca_client import discover_leveraged_long_assets

        verified: list[dict[str, Any]] = []
        for candidate in discover_leveraged_long_assets(underlying):
            info = self.get_asset_info(str(candidate["symbol"]))
            if (
                info.get("active")
                and info.get("tradable")
                and info.get("security_type") == "ETF"
                and float(info.get("leverage_factor") or 0.0) == 2.0
            ):
                verified.append({**candidate, **info})
        return verified

    def get_open_orders(self, *, limit: int = 100) -> list[dict[str, Any]]:
        return get_orders(status=_OPEN_ORDER_STATUS, limit=limit)

    def get_recent_closed_orders(self, *, limit: int = 50) -> list[dict[str, Any]]:
        return get_orders(status=_CLOSED_ORDER_STATUS, limit=limit)

    def get_order_status(self, order_id: str) -> dict[str, Any]:
        return get_order(order_id)

    def cancel_order(self, order_id: str) -> dict[str, Any]:
        raise NotImplementedError(_ORDER_STUB_MSG)

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
        raise NotImplementedError(_ORDER_STUB_MSG)

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
        raise NotImplementedError(_ORDER_STUB_MSG)
