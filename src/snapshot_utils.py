from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def serialize_settings(settings: Any) -> dict[str, Any]:
    if settings is None:
        return {}
    if hasattr(settings, "__dataclass_fields__"):
        return asdict(settings)
    if isinstance(settings, dict):
        return settings
    raise TypeError(f"Unsupported settings type: {type(settings)}")


def build_snapshot_payload(
    *,
    period: str,
    tickers: list[str],
    settings: Any,
    result: dict[str, Any],
    equity_rows: int,
    trade_rows: int,
    extra_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "period": period,
        "tickers": tickers,
        "settings": serialize_settings(settings),
        "result": result,
        "equity_rows": equity_rows,
        "trade_rows": trade_rows,
    }
    if extra_fields:
        payload.update(extra_fields)
    return payload


def save_snapshot_payload(
    payload: dict[str, Any],
    output_path: str | Path,
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)
    return path
