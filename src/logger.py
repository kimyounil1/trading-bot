from pathlib import Path
from datetime import datetime

import pandas as pd

from src.config import LOG_PATH, ORDER_LOG_PATH


def log_signal(
    ticker: str,
    signal: str,
    close: float,
    ma20: float,
    ma50: float,
    rsi: float,
) -> None:
    log_file = Path(LOG_PATH)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    row = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "ticker": ticker,
        "signal": signal,
        "close": round(float(close), 4),
        "ma20": round(float(ma20), 4),
        "ma50": round(float(ma50), 4),
        "rsi": round(float(rsi), 4),
    }

    df = pd.DataFrame([row])
    write_header = not log_file.exists()
    df.to_csv(log_file, mode="a", header=write_header, index=False)


def log_order(
    ticker: str,
    notional: float,
    order_id: str,
    status: str,
    side: str,
    order_type: str,
    reason: str = "",
) -> None:
    log_file = Path(ORDER_LOG_PATH)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    row = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "ticker": ticker,
        "notional": round(float(notional), 2),
        "order_id": order_id,
        "status": status,
        "side": side,
        "order_type": order_type,
        "reason": reason,
    }

    df = pd.DataFrame([row])
    write_header = not log_file.exists()
    df.to_csv(log_file, mode="a", header=write_header, index=False)


def log_order_status(
    ticker: str,
    order_id: str,
    status: str,
    side: str,
    order_type: str,
    filled_qty: str,
    filled_avg_price: str,
    reason: str = "",
) -> None:
    log_file = Path(ORDER_LOG_PATH)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    row = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "ticker": ticker,
        "notional": 0.0,
        "order_id": order_id,
        "status": status,
        "side": side,
        "order_type": order_type,
        "filled_qty": filled_qty,
        "filled_avg_price": filled_avg_price,
        "reason": reason,
        "event": "STATUS_CHECK",
    }

    df = pd.DataFrame([row])
    write_header = not log_file.exists()
    df.to_csv(log_file, mode="a", header=write_header, index=False)
