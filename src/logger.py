from pathlib import Path
from datetime import datetime

import pandas as pd

from src.config import SIGNAL_LOG_PATH, ORDER_LOG_PATH, EXECUTION_AUDIT_LOG_PATH
from src.execution_audit_io import (
    EXECUTION_AUDIT_COLUMNS,
    normalize_execution_audit_file,
)


def log_signal(
    ticker: str,
    signal: str,
    close: float,
    ma20: float,
    ma50: float,
    rsi: float,
    ai_score: float = None,
) -> None:
    log_file = Path(SIGNAL_LOG_PATH)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    row = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "ticker": ticker,
        "signal": signal,
        "ai_score": round(float(ai_score), 4) if ai_score is not None else None,
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
        "filled_qty": "",
        "filled_avg_price": "",
        "event": "SUBMITTED",
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
        "reason": reason,
        "filled_qty": filled_qty,
        "filled_avg_price": filled_avg_price,
        "event": "STATUS_CHECK",
    }

    df = pd.DataFrame([row])
    write_header = not log_file.exists()
    df.to_csv(log_file, mode="a", header=write_header, index=False)


def log_execution_audit(
    event_type: str,
    ticker: str,
    action: str,
    status: str,
    reason: str = "",
    *,
    profile_name: str = "",
    regime: str = "",
    signal: str = "",
    ai_score: float = None,
    rank_ai_score: float = None,
    rank_ai_percentile: float = None,
    llm_verdict: str = "",
    order_id: str = "",
    order_type: str = "",
    side: str = "",
    notional: float = None,
    quantity: float = None,
    filled_qty: float = None,
    filled_avg_price: float = None,
    decision_id: str = "",
    run_id: str = "",
    broker: str = "",
    environment: str = "",
    config_hash: str = "",
    model_version: str = "",
    rank_model_version: str = "",
    risk_block_reason: str = "",
    order_intent_id: str = "",
    broker_order_id: str = "",
) -> None:
    log_file = Path(EXECUTION_AUDIT_LOG_PATH)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    def _round_or_none(value, digits: int):
        if value is None or value == "" or str(value).lower() in {"none", "null"}:
            return None
        return round(float(value), digits)

    row = {column: None for column in EXECUTION_AUDIT_COLUMNS}
    row.update(
        {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "event_type": event_type,
            "ticker": ticker,
            "action": action,
            "status": status,
            "reason": reason,
            "profile_name": profile_name,
            "regime": regime,
            "signal": signal,
            "ai_score": _round_or_none(ai_score, 4),
            "rank_ai_score": _round_or_none(rank_ai_score, 4),
            "rank_ai_percentile": _round_or_none(rank_ai_percentile, 4),
            "llm_verdict": llm_verdict,
            "order_id": order_id,
            "order_type": order_type,
            "side": side,
            "notional": _round_or_none(notional, 2),
            "quantity": _round_or_none(quantity, 4),
            "filled_qty": _round_or_none(filled_qty, 4),
            "filled_avg_price": _round_or_none(filled_avg_price, 4),
            "decision_id": decision_id or None,
            "run_id": run_id or None,
            "broker": broker or None,
            "environment": environment or None,
            "config_hash": config_hash or None,
            "model_version": model_version or None,
            "rank_model_version": rank_model_version or None,
            "risk_block_reason": risk_block_reason or None,
            "order_intent_id": order_intent_id or None,
            "broker_order_id": broker_order_id or (order_id or None),
        }
    )

    if log_file.exists() and log_file.stat().st_size > 0:
        lines = log_file.read_text(encoding="utf-8").splitlines()
        if lines:
            first_line = lines[0]
            expected = ",".join(EXECUTION_AUDIT_COLUMNS)
            if first_line.strip() != expected:
                normalize_execution_audit_file(log_file)

    df = pd.DataFrame([row], columns=list(EXECUTION_AUDIT_COLUMNS))
    write_header = not log_file.exists() or log_file.stat().st_size == 0
    df.to_csv(log_file, mode="a", header=write_header, index=False)
