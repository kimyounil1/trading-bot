"""Read/write execution_audit.csv with a stable column schema."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import EXECUTION_AUDIT_LOG_PATH

EXECUTION_AUDIT_COLUMNS: tuple[str, ...] = (
    "timestamp",
    "event_type",
    "ticker",
    "action",
    "status",
    "reason",
    "profile_name",
    "regime",
    "signal",
    "ai_score",
    "rank_ai_score",
    "rank_ai_percentile",
    "llm_verdict",
    "order_id",
    "order_type",
    "side",
    "notional",
    "quantity",
    "filled_qty",
    "filled_avg_price",
    "decision_id",
    "run_id",
    "broker",
    "environment",
    "config_hash",
    "model_version",
    "rank_model_version",
    "risk_block_reason",
    "order_intent_id",
    "broker_order_id",
)

_LEGACY_EXTRA_COLUMNS: tuple[str, ...] = ("rank_ai_score", "rank_ai_percentile")
_V2_EXTRA_COLUMNS: tuple[str, ...] = (
    "decision_id",
    "run_id",
    "broker",
    "environment",
    "config_hash",
    "model_version",
    "rank_model_version",
    "risk_block_reason",
    "order_intent_id",
    "broker_order_id",
)


def read_execution_audit_csv(path: str | Path) -> pd.DataFrame:
    """Parse audit rows by header name; append trailing rank columns when present."""
    path = Path(path)
    if not path.is_file():
        return pd.DataFrame(columns=list(EXECUTION_AUDIT_COLUMNS))

    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    if len(rows) <= 1:
        return pd.DataFrame(columns=list(EXECUTION_AUDIT_COLUMNS))

    header = [cell.strip() for cell in rows[0]]
    records: list[dict[str, Any]] = []
    for fields in rows[1:]:
        if not fields:
            continue
        record = {column: None for column in EXECUTION_AUDIT_COLUMNS}
        for index, column in enumerate(header):
            if index < len(fields) and column in record:
                record[column] = fields[index]
        extra = fields[len(header) :]
        extra_index = 0
        for column in (*_LEGACY_EXTRA_COLUMNS, *_V2_EXTRA_COLUMNS):
            if column in header:
                continue
            if extra_index < len(extra):
                record[column] = extra[extra_index]
                extra_index += 1
        records.append(record)
    return pd.DataFrame.from_records(records)


def normalize_execution_audit_file(path: str | Path = EXECUTION_AUDIT_LOG_PATH) -> Path:
    """Rewrite audit log with the canonical header and column order."""
    path = Path(path)
    if not path.is_file():
        return path
    df = read_execution_audit_csv(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df = df.reindex(columns=list(EXECUTION_AUDIT_COLUMNS))
    df.to_csv(path, index=False)
    return path
