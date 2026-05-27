from __future__ import annotations

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import LimitOrderRequest, MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from typing import Optional
from requests.exceptions import RequestException

from src.config import ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_PAPER


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


def get_open_symbols() -> set[str]:
    client = get_trading_client()
    try:
        positions = client.get_all_positions()
    except RequestException as exc:
        raise ConnectionError(f"Unable to reach Alpaca paper API: {exc}") from exc
    return {position.symbol for position in positions}


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
            "market_value": float(position.market_value),
            "cost_basis": float(position.cost_basis),
            "unrealized_pl": float(position.unrealized_pl),
            "unrealized_plpc": float(position.unrealized_plpc),
        }
        for position in positions
    ]


def get_order_summary(order_id: str) -> dict:
    client = get_trading_client()
    try:
        order = client.get_order_by_id(order_id)
    except RequestException as exc:
        raise ConnectionError(f"Unable to reach Alpaca paper API: {exc}") from exc

    return {
        "id": str(order.id),
        "symbol": order.symbol,
        "status": str(order.status),
        "side": str(order.side),
        "type": str(order.type),
        "notional": str(order.notional),
        "qty": str(order.qty),
        "filled_qty": str(order.filled_qty),
        "filled_avg_price": str(order.filled_avg_price),
        "submitted_at": str(order.submitted_at),
        "filled_at": str(order.filled_at),
    }


def submit_market_buy_notional_order(ticker: str, notional: float):
    if notional <= 0:
        raise ValueError("notional must be positive")

    client = get_trading_client()

    order_request = MarketOrderRequest(
        symbol=ticker,
        notional=round(float(notional), 2),
        side=OrderSide.BUY,
        time_in_force=TimeInForce.DAY,
    )

    try:
        return client.submit_order(order_data=order_request)
    except RequestException as exc:
        raise ConnectionError(f"Unable to reach Alpaca paper API: {exc}") from exc


def submit_limit_buy_notional_order(
    ticker: str,
    notional: float,
    limit_price: float,
    slippage_pct: float = 0.005,
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
    qty = round(notional / effective_limit, 6)

    if qty <= 0:
        raise ValueError("calculated qty is zero or negative")

    client = get_trading_client()
    order_request = LimitOrderRequest(
        symbol=ticker,
        qty=qty,
        limit_price=effective_limit,
        side=OrderSide.BUY,
        time_in_force=TimeInForce.DAY,
    )

    try:
        return client.submit_order(order_data=order_request)
    except RequestException as exc:
        raise ConnectionError(f"Unable to reach Alpaca paper API: {exc}") from exc


def close_position_by_symbol(ticker: str, qty: Optional[float] = None):
    client = get_trading_client()
    try:
        if qty is not None:
            from alpaca.trading.requests import ClosePositionRequest
            return client.close_position(ticker, close_options=ClosePositionRequest(qty=str(qty)))
        return client.close_position(ticker)
    except RequestException as exc:
        raise ConnectionError(f"Unable to reach Alpaca paper API: {exc}") from exc


def wait_for_order_status(
    order_id: str,
    max_attempts: int = 5,
    sleep_seconds: float = 1.0,
) -> dict:
    import time

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
