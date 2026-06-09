"""Persistent symbol → portfolio sleeve mapping."""

from __future__ import annotations

import json
import os
from pathlib import Path

from src.portfolio_sleeves import CORE_SLEEVE_ID

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


def bootstrap_open_positions(
    open_symbols: set[str] | list[str],
    *,
    default_sleeve: str = CORE_SLEEVE_ID,
    path: Path = REGISTRY_PATH,
) -> dict[str, str]:
    """Assign untagged open symbols to default_sleeve (first-run migration)."""
    mapping = load_sleeve_position_map(path)
    changed = False
    for symbol in open_symbols:
        key = _normalize_symbol(symbol)
        if not key:
            continue
        if key not in mapping:
            mapping[key] = _normalize_sleeve(default_sleeve)
            changed = True
    if changed:
        save_sleeve_position_map(mapping, path=path)
    return mapping
