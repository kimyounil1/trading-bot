from __future__ import annotations

import html
from datetime import datetime

import requests

from src.config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    TELEGRAM_ENABLED,
)
from src.notification_settings import (
    telegram_enabled,
    run_summary_enabled,
    order_notifications_enabled,
    error_notifications_enabled,
)


def telegram_is_configured() -> bool:
    return bool(
        TELEGRAM_ENABLED
        and telegram_enabled()
        and TELEGRAM_BOT_TOKEN
        and TELEGRAM_CHAT_ID
    )


def send_telegram_message(message: str, parse_mode: str = "HTML") -> bool:
    if not telegram_is_configured():
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }

    response = requests.post(url, data=payload, timeout=10)
    response.raise_for_status()

    data = response.json()
    return bool(data.get("ok"))


def escape(value: object) -> str:
    return html.escape(str(value))


def notify_info(title: str, body: str) -> bool:
    timestamp = datetime.now().isoformat(timespec="seconds")

    message = (
        f"🤖 <b>{escape(title)}</b>\n"
        f"<code>{escape(timestamp)}</code>\n\n"
        f"{escape(body)}"
    )

    return send_telegram_message(message)


def notify_order(
    action: str,
    ticker: str,
    status: str,
    order_id: str,
    reason: str = "",
    filled_qty: str = "",
    filled_avg_price: str = "",
) -> bool:
    if not order_notifications_enabled():
        return False

    timestamp = datetime.now().isoformat(timespec="seconds")

    message = (
        f"📈 <b>Trading Bot Order</b>\n"
        f"<code>{escape(timestamp)}</code>\n\n"
        f"<b>Action:</b> {escape(action)}\n"
        f"<b>Ticker:</b> {escape(ticker)}\n"
        f"<b>Status:</b> {escape(status)}\n"
        f"<b>Order ID:</b> <code>{escape(order_id)}</code>\n"
        f"<b>Reason:</b> {escape(reason)}\n"
        f"<b>Filled Qty:</b> {escape(filled_qty)}\n"
        f"<b>Filled Avg Price:</b> {escape(filled_avg_price)}"
    )

    return send_telegram_message(message)


def notify_error(title: str, error: Exception | str) -> bool:
    if not error_notifications_enabled():
        return False

    timestamp = datetime.now().isoformat(timespec="seconds")

    message = (
        f"🚨 <b>{escape(title)}</b>\n"
        f"<code>{escape(timestamp)}</code>\n\n"
        f"<pre>{escape(error)}</pre>"
    )

    return send_telegram_message(message)


def notify_run_summary(
    market_is_open: bool,
    execute_orders: bool,
    cash: float,
    portfolio_value: float,
    positions_count: int,
    exit_summary: str,
    buy_summary: str,
) -> bool:
    if not run_summary_enabled():
        return False

    timestamp = datetime.now().isoformat(timespec="seconds")

    message = (
        f"📋 <b>Trading Bot Run Summary</b>\n"
        f"<code>{escape(timestamp)}</code>\n\n"
        f"<b>Execute:</b> {escape(execute_orders)}\n"
        f"<b>Market Open:</b> {escape(market_is_open)}\n"
        f"<b>Cash:</b> ${cash:,.2f}\n"
        f"<b>Portfolio:</b> ${portfolio_value:,.2f}\n"
        f"<b>Positions:</b> {escape(positions_count)}\n\n"
        f"<b>Exit Check</b>\n"
        f"<pre>{escape(exit_summary)}</pre>\n\n"
        f"<b>Buy Check</b>\n"
        f"<pre>{escape(buy_summary)}</pre>"
    )

    return send_telegram_message(message)
