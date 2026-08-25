"""Persistent symbol → portfolio sleeve mapping."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable, Mapping

from src.portfolio_sleeves import CORE_SLEEVE_ID, TOURNAMENT_SLEEVE_ID

REGISTRY_PATH = Path("data/sleeve_positions.json")


def _normalize_symbol(symbol: str) -> str:
    return str(symbol).strip().upper()


def _normalize_sleeve(sleeve_id: str) -> str:
    return str(sleeve_id).strip().lower()


def load_sleeve_position_map(path: Path = REGISTRY_PATH) -> dict[str, str]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Warning: failed to load sleeve position registry {path}: {exc}")
        return {}
    if not isinstance(payload, dict):
        return {}
    return {
        _normalize_symbol(symbol): _normalize_sleeve(sleeve_id)
        for symbol, sleeve_id in payload.items()
        if symbol and sleeve_id
    }


def save_sleeve_position_map(
    mapping: dict[str, str],
    *,
    path: Path = REGISTRY_PATH,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = {
        _normalize_symbol(symbol): _normalize_sleeve(sleeve_id)
        for symbol, sleeve_id in mapping.items()
        if symbol and sleeve_id
    }
    temp_path = path.with_suffix(f"{path.suffix}.tmp")
    temp_path.write_text(
        json.dumps(normalized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    with temp_path.open("r+", encoding="utf-8") as handle:
        handle.flush()
        os.fsync(handle.fileno())
    temp_path.replace(path)


def tag_symbol(
    symbol: str,
    sleeve_id: str,
    *,
    path: Path = REGISTRY_PATH,
) -> None:
    mapping = load_sleeve_position_map(path)
    mapping[_normalize_symbol(symbol)] = _normalize_sleeve(sleeve_id)
    save_sleeve_position_map(mapping, path=path)


def untag_symbol(symbol: str, *, path: Path = REGISTRY_PATH) -> None:
    mapping = load_sleeve_position_map(path)
    mapping.pop(_normalize_symbol(symbol), None)
    save_sleeve_position_map(mapping, path=path)


_BUY_AUDIT_EVENTS = frozenset({"BUY_SUBMITTED", "BUY_FILL", "BUY_STATUS", "SLEEVE_RETAG"})
_VALID_SLEEVES = frozenset({CORE_SLEEVE_ID, TOURNAMENT_SLEEVE_ID})


def last_sleeves_from_audit_frame(
    audit_df: Any,
    symbols: Iterable[str] | None = None,
) -> dict[str, str]:
    """Last BUY_* sleeve_id per ticker (and execution_ticker when present)."""
    if audit_df is None or getattr(audit_df, "empty", True):
        return {}
    if "sleeve_id" not in getattr(audit_df, "columns", ()):
        return {}

    frame = audit_df
    if "profile_name" in frame.columns:
        frame = frame[frame["profile_name"].astype(str) != "TEST_PROFILE"]
    if "event_type" in frame.columns:
        frame = frame[frame["event_type"].astype(str).isin(_BUY_AUDIT_EVENTS)]
    sleeve = frame["sleeve_id"].astype(str).str.strip().str.lower()
    frame = frame.loc[sleeve.isin(_VALID_SLEEVES)].copy()
    if frame.empty:
        return {}
    frame["_sleeve"] = sleeve.loc[frame.index]
    tickers = frame["ticker"].astype(str).str.upper() if "ticker" in frame.columns else None
    if tickers is None:
        return {}
    if "execution_ticker" in frame.columns:
        execution = frame["execution_ticker"].astype(str).str.upper()
        tickers = execution.where(
            ~execution.isin({"", "NAN", "NONE", "NAT"}),
            tickers,
        )
    frame["_symbol"] = tickers
    if "timestamp" in frame.columns:
        frame = frame.sort_values("timestamp")
    last = frame.groupby("_symbol", sort=False)["_sleeve"].last()
    result = {
        _normalize_symbol(symbol): _normalize_sleeve(sleeve_id)
        for symbol, sleeve_id in last.items()
        if symbol and str(symbol) not in {"NAN", "NONE", "NAT"}
    }
    if symbols is not None:
        wanted = {_normalize_symbol(symbol) for symbol in symbols}
        result = {symbol: sleeve_id for symbol, sleeve_id in result.items() if symbol in wanted}
    return result


def last_audit_sleeves_for_symbols(
    open_symbols: Iterable[str],
    *,
    audit_path: Path | None = None,
) -> dict[str, str]:
    wanted = {_normalize_symbol(symbol) for symbol in open_symbols if symbol}
    if not wanted:
        return {}
    path = Path(audit_path) if audit_path is not None else Path("logs/execution_audit.csv")
    if not path.is_file():
        return {}
    try:
        import pandas as pd

        audit_df = pd.read_csv(path, dtype=str, low_memory=False)
    except Exception as exc:
        print(f"Warning: failed to load execution audit for sleeve recovery {path}: {exc}")
        return {}
    return last_sleeves_from_audit_frame(audit_df, wanted)


def bootstrap_open_positions(
    open_symbols: set[str] | list[str],
    *,
    default_sleeve: str = CORE_SLEEVE_ID,
    inferred_sleeves: Mapping[str, str] | None = None,
    path: Path = REGISTRY_PATH,
) -> dict[str, str]:
    """Tag untagged open symbols from audit inference, else default_sleeve."""
    mapping = load_sleeve_position_map(path)
    inferred = {
        _normalize_symbol(symbol): _normalize_sleeve(sleeve_id)
        for symbol, sleeve_id in (inferred_sleeves or {}).items()
        if symbol and sleeve_id
    }
    changed = False
    for symbol in open_symbols:
        key = _normalize_symbol(symbol)
        if not key:
            continue
        if key not in mapping:
            mapping[key] = inferred.get(key, _normalize_sleeve(default_sleeve))
            changed = True
    if changed:
        save_sleeve_position_map(mapping, path=path)
    return mapping
