from __future__ import annotations

import math
import time
from typing import Optional
from requests.exceptions import RequestException
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import LimitOrderRequest, MarketOrderRequest, ClosePositionRequest, GetOrdersRequest
from alpaca.trading.enums import OrderSide, TimeInForce, QueryOrderStatus

from src.config import ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_PAPER


def _safe_order_qty(qty: float) -> float:
    """Truncate qty down to 6 decimals so sell orders never exceed holdings."""
    safe = safe_order_qty_or_none(qty)
    if safe is None:
        raise ValueError("qty must be positive after truncation")
    return safe


def safe_order_qty_or_none(qty: float) -> float | None:
    """Return truncated qty, or None when dust-sized holdings round to zero."""
    scaled = math.floor(float(qty) * 1_000_000)
    if scaled <= 0:
        return None
    return scaled / 1_000_000


def get_trading_client() -> TradingClient:
    if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
        raise ValueError(
            "Missing Alpaca API keys. Please set ALPACA_API_KEY and "
            "ALPACA_SECRET_KEY in your .env file."
        )

    if not ALPACA_PAPER:
        raise ValueError("ALPACA_PAPER must be True for this project stage.")

    return TradingClient(
        api_key=ALPACA_API_KEY,
        secret_key=ALPACA_SECRET_KEY,
        paper=True,
    )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((RequestException, ConnectionError)),
    reraise=True
)
def get_account_summary() -> dict:
    client = get_trading_client()
    try:
        account = client.get_account()
        positions = client.get_all_positions()
    except RequestException as exc:
        raise ConnectionError(f"Unable to reach Alpaca paper API: {exc}") from exc

    return {
        "account_number": account.account_number,
        "status": str(account.status),
        "currency": account.currency,
        "cash": float(account.cash),
        "portfolio_value": float(account.portfolio_value),
        "last_equity": float(account.last_equity),
        "buying_power": float(account.buying_power),
        "positions_count": len(positions),
    }


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((RequestException, ConnectionError)),
    reraise=True
)
def get_open_symbols() -> set[str]:
    client = get_trading_client()
    try:
        positions = client.get_all_positions()
    except RequestException as exc:
        raise ConnectionError(f"Unable to reach Alpaca paper API: {exc}") from exc
    return {position.symbol for position in positions}


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((RequestException, ConnectionError)),
    reraise=True
)
def get_positions_summary() -> list[dict]:
    client = get_trading_client()
    try:
        positions = client.get_all_positions()
    except RequestException as exc:
        raise ConnectionError(f"Unable to reach Alpaca paper API: {exc}") from exc

    return [
        {
            "symbol": position.symbol,
            "qty": float(position.qty),
            "current_price": float(position.current_price),
            "market_value": float(position.market_value),
            "cost_basis": float(position.cost_basis),
            "unrealized_pl": float(position.unrealized_pl),
            "unrealized_plpc": float(position.unrealized_plpc),
        }
        for position in positions
    ]


def _optional_str(value) -> str:
    if value is None:
        return ""
    return str(value)


def _normalize_order_status(status: str) -> str:
    return str(status).replace("OrderStatus.", "").upper()


def order_is_open(status: str) -> bool:
    return _normalize_order_status(status) in {
        "NEW",
        "ACCEPTED",
        "PENDING_NEW",
        "PARTIALLY_FILLED",
        "PENDING_CANCEL",
        "PENDING_REPLACE",
        "SUSPENDED",
    }


def order_is_filled(status: str) -> bool:
    return _normalize_order_status(status) == "FILLED"


def serialize_alpaca_order(order) -> dict:
    limit_price = getattr(order, "limit_price", None)
    qty = getattr(order, "qty", None)
    filled_qty = getattr(order, "filled_qty", None)
    filled_avg_price = getattr(order, "filled_avg_price", None)

    qty_num = float(qty) if qty not in (None, "") else 0.0
    filled_qty_num = float(filled_qty) if filled_qty not in (None, "") else 0.0
    fill_pct = (filled_qty_num / qty_num * 100.0) if qty_num > 0 else 0.0

    return {
        "id": str(order.id),
        "client_order_id": _optional_str(getattr(order, "client_order_id", None)),
        "symbol": str(order.symbol),
        "status": str(order.status),
        "status_simple": _normalize_order_status(order.status),
        "side": str(order.side).replace("OrderSide.", ""),
        "type": str(order.type).replace("OrderType.", ""),
        "qty": _optional_str(qty),
        "filled_qty": _optional_str(filled_qty),
        "filled_avg_price": _optional_str(filled_avg_price),
        "limit_price": _optional_str(limit_price),
        "notional": _optional_str(getattr(order, "notional", None)),
        "extended_hours": bool(getattr(order, "extended_hours", False)),
        "submitted_at": _optional_str(order.submitted_at),
        "filled_at": _optional_str(order.filled_at),
        "updated_at": _optional_str(getattr(order, "updated_at", None)),
        "fill_pct": round(fill_pct, 2),
    }


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((RequestException, ConnectionError)),
    reraise=True,
)
def get_open_orders(limit: int = 100) -> list[dict]:
    client = get_trading_client()
    try:
        request_params = GetOrdersRequest(status=QueryOrderStatus.OPEN, limit=limit)
        orders = client.get_orders(request_params)
    except RequestException as exc:
        raise ConnectionError(f"Unable to reach Alpaca paper API: {exc}") from exc
    return [serialize_alpaca_order(order) for order in orders]


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((RequestException, ConnectionError)),
    reraise=True,
)
def get_recent_closed_orders(limit: int = 50) -> list[dict]:
    client = get_trading_client()
    try:
        request_params = GetOrdersRequest(status=QueryOrderStatus.CLOSED, limit=limit)
        orders = client.get_orders(request_params)
    except RequestException as exc:
        raise ConnectionError(f"Unable to reach Alpaca paper API: {exc}") from exc
    return [serialize_alpaca_order(order) for order in orders]


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((RequestException, ConnectionError)),
    reraise=True,
)
def get_order_summary(order_id: str) -> dict:
    client = get_trading_client()
    try:
        order = client.get_order_by_id(order_id)
    except RequestException as exc:
        raise ConnectionError(f"Unable to reach Alpaca paper API: {exc}") from exc

    summary = serialize_alpaca_order(order)
    return {
        "id": summary["id"],
        "symbol": summary["symbol"],
        "status": summary["status"],
        "side": summary["side"],
        "type": summary["type"],
        "notional": summary["notional"],
        "qty": summary["qty"],
        "filled_qty": summary["filled_qty"],
        "filled_avg_price": summary["filled_avg_price"],
        "limit_price": summary["limit_price"],
        "extended_hours": summary["extended_hours"],
        "submitted_at": summary["submitted_at"],
        "filled_at": summary["filled_at"],
    }


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((RequestException, ConnectionError)),
    reraise=True,
)
def cancel_order_by_id(order_id: str) -> dict:
    client = get_trading_client()
    try:
        order = client.cancel_order_by_id(order_id)
    except RequestException as exc:
        raise ConnectionError(f"Unable to reach Alpaca paper API: {exc}") from exc
    return serialize_alpaca_order(order)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((RequestException, ConnectionError)),
    reraise=True
)
def submit_market_buy_notional_order(
    ticker: str, 
    notional: float, 
    client_order_id: Optional[str] = None
):
    if notional <= 0:
        raise ValueError("notional must be positive")

    client = get_trading_client()

    order_request = MarketOrderRequest(
        symbol=ticker,
        notional=round(float(notional), 2),
        side=OrderSide.BUY,
        time_in_force=TimeInForce.DAY,
        client_order_id=client_order_id,
    )

    try:
        return client.submit_order(order_data=order_request)
    except RequestException as exc:
        raise ConnectionError(f"Unable to reach Alpaca paper API: {exc}") from exc


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((RequestException, ConnectionError)),
    reraise=True
)
def submit_limit_buy_notional_order(
    ticker: str,
    notional: float,
    limit_price: float,
    slippage_pct: float = 0.005,
    client_order_id: Optional[str] = None,
    extended_hours: bool = False,
):
    """지정가 매수 주문. limit_price 기준으로 수량을 계산해 제출한다.

    slippage_pct: limit_price에 더하는 여유 비율 (기본 0.5%).
                  즉시 체결 가능성을 높이면서 시장가 대비 슬리피지를 줄인다.
    """
    if notional <= 0:
        raise ValueError("notional must be positive")
    if limit_price <= 0:
        raise ValueError("limit_price must be positive")

    effective_limit = round(limit_price * (1 + slippage_pct), 2)
    qty = _safe_order_qty(notional / effective_limit)

    client = get_trading_client()
    order_request = LimitOrderRequest(
        symbol=ticker,
        qty=qty,
        limit_price=effective_limit,
        side=OrderSide.BUY,
        time_in_force=TimeInForce.DAY,
        client_order_id=client_order_id,
        extended_hours=extended_hours,
    )

    try:
        return client.submit_order(order_data=order_request)
    except RequestException as exc:
        raise ConnectionError(f"Unable to reach Alpaca paper API: {exc}") from exc


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((RequestException, ConnectionError)),
    reraise=True
)
def submit_limit_sell_qty_order(
    ticker: str,
    qty: float,
    limit_price: float,
    slippage_pct: float = 0.005,
    client_order_id: Optional[str] = None,
    extended_hours: bool = False,
):
    if qty <= 0:
        raise ValueError("qty must be positive")
    if limit_price <= 0:
        raise ValueError("limit_price must be positive")

    effective_limit = round(limit_price * (1 - slippage_pct), 2)
    if effective_limit <= 0:
        raise ValueError("effective limit price must be positive")

    client = get_trading_client()
    safe_qty = safe_order_qty_or_none(qty)
    if safe_qty is None:
        return close_position_by_symbol(
            ticker,
            qty=None,
            client_order_id=client_order_id,
        )

    order_request = LimitOrderRequest(
        symbol=ticker,
        qty=safe_qty,
        limit_price=effective_limit,
        side=OrderSide.SELL,
        time_in_force=TimeInForce.DAY,
        client_order_id=client_order_id,
        extended_hours=extended_hours,
    )

    try:
        return client.submit_order(order_data=order_request)
    except RequestException as exc:
        raise ConnectionError(f"Unable to reach Alpaca paper API: {exc}") from exc


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((RequestException, ConnectionError)),
    reraise=True
)
def close_position_by_symbol(
    ticker: str, 
    qty: Optional[float] = None, 
    client_order_id: Optional[str] = None
):
    client = get_trading_client()
    try:
        # If client_order_id is provided, we use submit_order for idempotency.
        # Note: close_position API (DELETE /positions) does not support client_order_id.
        if client_order_id:
            from alpaca.trading.requests import MarketOrderRequest
            from alpaca.trading.enums import OrderSide, TimeInForce

            # If qty is None, we are closing the entire position.
            if qty is None:
                position = client.get_open_position(ticker)
                qty = float(position.qty)

            if qty <= 0:
                return None

            safe_qty = safe_order_qty_or_none(qty)
            if safe_qty is None:
                # Dust holdings: broker close API avoids sub-minimum qty orders.
                return client.close_position(ticker)

            order_request = MarketOrderRequest(
                symbol=ticker,
                qty=safe_qty,
                side=OrderSide.SELL,
                time_in_force=TimeInForce.DAY,
                client_order_id=client_order_id,
            )
            return client.submit_order(order_data=order_request)

        if qty is not None:
            safe_qty = safe_order_qty_or_none(qty)
            if safe_qty is None:
                return client.close_position(ticker)
            return client.close_position(
                ticker,
                close_options=ClosePositionRequest(qty=str(safe_qty)),
            )
        return client.close_position(ticker)
    except RequestException as exc:
        raise ConnectionError(f"Unable to reach Alpaca paper API: {exc}") from exc


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((RequestException, ConnectionError)),
    reraise=True
)
def wait_for_order_status(
    order_id: str,
    max_attempts: int = 5,
    sleep_seconds: float = 1.0,
) -> dict:
    client = get_trading_client()

    terminal_statuses = {
        "OrderStatus.FILLED",
        "OrderStatus.CANCELED",
        "OrderStatus.REJECTED",
        "OrderStatus.EXPIRED",
        "OrderStatus.DONE_FOR_DAY",
    }

    last_order = None

    for attempt in range(1, max_attempts + 1):
        try:
            order = client.get_order_by_id(order_id)
        except RequestException as exc:
            raise ConnectionError(f"Unable to reach Alpaca paper API: {exc}") from exc
        last_order = order

        status = str(order.status)

        if status in terminal_statuses:
            break

        time.sleep(sleep_seconds)

    return {
        "id": str(last_order.id),
        "symbol": last_order.symbol,
        "status": str(last_order.status),
        "side": str(last_order.side),
        "type": str(last_order.type),
        "notional": str(last_order.notional),
        "qty": str(last_order.qty),
        "filled_qty": str(last_order.filled_qty),
        "filled_avg_price": str(last_order.filled_avg_price),
        "submitted_at": str(last_order.submitted_at),
        "filled_at": str(last_order.filled_at),
    }


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((RequestException, ConnectionError)),
    reraise=True
)
def get_position_entry_date(ticker: str) -> Optional[datetime]:
    """해당 종목의 포지션이 처음 생성된(Fill) 날짜를 가져온다.
    Trading API의 get_orders를 활용해 가장 오래된 BUY 주문의 filled_at 시각을 반환한다.
    """
    client = get_trading_client()
    try:
        request_params = GetOrdersRequest(
            status=QueryOrderStatus.CLOSED,
            symbols=[ticker],
            side=OrderSide.BUY
        )
        orders = client.get_orders(request_params)
        if not orders:
            return None
        
        # filled_at이 있는 주문 중 가장 오래된 것 찾기
        filled_orders = [o for o in orders if hasattr(o, 'filled_at') and o.filled_at is not None]
        if not filled_orders:
            return None
            
        oldest_order = min(filled_orders, key=lambda x: x.filled_at)
        return oldest_order.filled_at
    except Exception as exc:
        print(f"Warning: Failed to fetch entry date for {ticker}: {exc}")
        return None

