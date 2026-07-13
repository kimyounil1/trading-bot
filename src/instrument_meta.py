"""Instrument metadata (ETF / leveraged ETF) for sizing and buy gates."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REGISTRY_PATH = Path("config/instrument_registry.json")

DEFAULT_META = {
    "kind": "stock",
    "multiple": 1.0,
    "underlying": "",
    "direction": "long",
}


@dataclass(frozen=True)
class InstrumentMeta:
    kind: str
    multiple: float
    underlying: str
    direction: str

    @property
    def abs_multiple(self) -> float:
        return abs(float(self.multiple))

    @property
    def is_leveraged_etf(self) -> bool:
        return self.kind == "leveraged_etf"

    @property
    def instrument_kind(self) -> str:
        return self.kind


def _parse_meta(raw: dict[str, Any]) -> InstrumentMeta:
    return InstrumentMeta(
        kind=str(raw.get("kind", "stock")),
        multiple=float(raw.get("multiple", 1.0)),
        underlying=str(raw.get("underlying", "")).upper(),
        direction=str(raw.get("direction", "long")),
    )


def load_instrument_registry(path: Path = REGISTRY_PATH) -> dict[str, InstrumentMeta]:
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must be a JSON object")
    registry: dict[str, InstrumentMeta] = {}
    for ticker, meta in payload.items():
        if not isinstance(meta, dict):
            raise ValueError(f"Registry entry for {ticker} must be an object")
        registry[str(ticker).strip().upper()] = _parse_meta(meta)
    return registry


_registry_cache: dict[str, InstrumentMeta] | None = None


def get_instrument(ticker: str, registry: dict[str, InstrumentMeta] | None = None) -> InstrumentMeta:
    global _registry_cache
    reg = registry if registry is not None else (_registry_cache or load_instrument_registry())
    if registry is None and _registry_cache is None:
        _registry_cache = reg
    key = str(ticker).strip().upper()
    if key in reg:
        return reg[key]
    return _parse_meta(DEFAULT_META)


def clear_instrument_registry_cache() -> None:
    global _registry_cache
    _registry_cache = None


def count_leveraged_etf_positions(open_symbols: set[str]) -> int:
    return sum(1 for sym in open_symbols if get_instrument(sym).is_leveraged_etf)


def current_effective_leverage_exposure(
    positions_by_symbol: dict[str, dict[str, Any]],
) -> float:
    total = 0.0
    for symbol, position in positions_by_symbol.items():
        meta = get_instrument(symbol)
        market_value = float(position.get("market_value", 0.0) or 0.0)
        total += market_value * meta.abs_multiple
    return total


def adjust_position_cap_for_instrument(
    max_position_pct: float,
    ticker: str,
) -> float:
    meta = get_instrument(ticker)
    if meta.abs_multiple <= 1.0:
        return max_position_pct
    return max_position_pct / meta.abs_multiple


def _latest_vix_close(vix_df) -> float | None:
    if vix_df is None or getattr(vix_df, "empty", True):
        return None
    if "close" not in vix_df.columns:
        return None
    try:
        return float(vix_df["close"].iloc[-1])
    except (TypeError, ValueError, IndexError):
        return None


def check_instrument_buy_allowed(
    ticker: str,
    open_symbols: set[str],
    *,
    allow_leveraged_etfs: bool = False,
    leveraged_etf_allowlist: list[str] | None = None,
    max_leveraged_etf_positions: int = 1,
    block_leveraged_etfs_vix_above: float = 0.0,
    vix_df=None,
) -> tuple[bool, str]:
    meta = get_instrument(ticker)
    kind_tag = f"instrument_kind={meta.instrument_kind}"

    if meta.is_leveraged_etf:
        if not allow_leveraged_etfs:
            return (
                False,
                f"{kind_tag}; leveraged ETF buys disabled (allow_leveraged_etfs=false)",
            )
        allowed_symbols = {
            str(symbol).strip().upper()
            for symbol in (leveraged_etf_allowlist or [])
            if str(symbol).strip()
        }
        if allowed_symbols and str(ticker).strip().upper() not in allowed_symbols:
            return (
                False,
                f"{kind_tag}; leveraged ETF not in allowlist",
            )
        vix_floor = float(block_leveraged_etfs_vix_above or 0.0)
        if vix_floor > 0:
            vix_close = _latest_vix_close(vix_df)
            if vix_close is not None and vix_close >= vix_floor:
                return (
                    False,
                    f"{kind_tag}; VIX {vix_close:.2f} >= block threshold {vix_floor:.2f}",
                )
        held = count_leveraged_etf_positions(open_symbols)
        if held >= max(1, int(max_leveraged_etf_positions)):
            return (
                False,
                f"{kind_tag}; max leveraged ETF positions reached ({held}/{max_leveraged_etf_positions})",
            )

    return True, kind_tag


def format_audit_reason(base_reason: str, ticker: str) -> str:
    meta = get_instrument(ticker)
    prefix = f"instrument_kind={meta.instrument_kind}"
    if not base_reason:
        return prefix
    if base_reason.startswith("instrument_kind="):
        return base_reason
    return f"{prefix}; {base_reason}"
