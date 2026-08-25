"""Instrument metadata (ETF / leveraged ETF) for sizing and buy gates."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REGISTRY_PATH = Path("config/instrument_registry.json")
DISCOVERED_REGISTRY_PATH = Path("data/runtime/discovered_instruments.json")

DEFAULT_META = {
    "kind": "stock",
    "multiple": 1.0,
    "underlying": "",
    "direction": "long",
}

_BASKET_UNDERLYING_KINDS = frozenset({"etf", "leveraged_etf", "index"})


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
_discovered_registry_cache: dict[str, InstrumentMeta] | None = None


def load_discovered_instrument_registry(
    path: Path | None = None,
) -> dict[str, InstrumentMeta]:
    target = path or DISCOVERED_REGISTRY_PATH
    if not target.is_file():
        return {}
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid discovered instrument registry {target}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{target} must be a JSON object")
    registry: dict[str, InstrumentMeta] = {}
    for ticker, meta in payload.items():
        if not isinstance(meta, dict):
            raise ValueError(f"Discovered registry entry for {ticker} must be an object")
        registry[str(ticker).strip().upper()] = _parse_meta(meta)
    return registry


def _discovered_registry() -> dict[str, InstrumentMeta]:
    global _discovered_registry_cache
    if _discovered_registry_cache is None:
        _discovered_registry_cache = load_discovered_instrument_registry()
    return _discovered_registry_cache


def register_discovered_leveraged_product(
    symbol: str,
    underlying: str,
    *,
    multiple: float = 2.0,
    path: Path | None = None,
) -> None:
    """Persist broker-validated metadata so later runs keep safe exit/risk mapping."""
    global _discovered_registry_cache
    product = str(symbol).strip().upper()
    source = str(underlying).strip().upper()
    if not product or not source or float(multiple) <= 1.0:
        raise ValueError("discovered leveraged product metadata is invalid")

    target = path or DISCOVERED_REGISTRY_PATH
    discovered = load_discovered_instrument_registry(target)
    meta = InstrumentMeta(
        kind="leveraged_etf",
        multiple=float(multiple),
        underlying=source,
        direction="long",
    )
    if discovered.get(product) == meta:
        _discovered_registry_cache = discovered
        return
    discovered[product] = meta
    payload = {
        ticker: {
            "kind": meta.kind,
            "multiple": meta.multiple,
            "underlying": meta.underlying,
            "direction": meta.direction,
        }
        for ticker, meta in sorted(discovered.items())
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target.with_suffix(f"{target.suffix}.tmp")
    try:
        temp_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temp_path.replace(target)
    except OSError as exc:
        raise OSError(f"Unable to persist discovered instrument {product}: {exc}") from exc
    _discovered_registry_cache = discovered


def is_discovered_instrument(ticker: str) -> bool:
    return str(ticker).strip().upper() in _discovered_registry()


def get_instrument(ticker: str, registry: dict[str, InstrumentMeta] | None = None) -> InstrumentMeta:
    global _registry_cache
    reg = registry if registry is not None else (_registry_cache or load_instrument_registry())
    if registry is None and _registry_cache is None:
        _registry_cache = reg
    key = str(ticker).strip().upper()
    if key in reg:
        return reg[key]
    if registry is None and key in _discovered_registry():
        return _discovered_registry()[key]
    return _parse_meta(DEFAULT_META)


def clear_instrument_registry_cache() -> None:
    global _registry_cache, _discovered_registry_cache
    _registry_cache = None
    _discovered_registry_cache = None


def count_leveraged_etf_positions(open_symbols: set[str]) -> int:
    return sum(1 for sym in open_symbols if get_instrument(sym).is_leveraged_etf)


def is_single_name_leveraged(
    ticker: str,
    registry: dict[str, InstrumentMeta] | None = None,
) -> bool:
    """True for 2x/3x products whose underlying is a stock, not an index/sector ETF."""
    meta = get_instrument(ticker, registry)
    if not meta.is_leveraged_etf:
        return False
    underlying = str(meta.underlying or "").strip().upper()
    if not underlying:
        return False
    underlying_meta = get_instrument(underlying, registry)
    return underlying_meta.kind not in _BASKET_UNDERLYING_KINDS


def preferred_leveraged_long_product(
    underlying: str,
    *,
    allowlist: list[str] | None = None,
    registry: dict[str, InstrumentMeta] | None = None,
) -> str | None:
    """Return the preferred direct 2x-long product for an underlying ticker."""
    source = str(underlying).strip().upper()
    reg = registry if registry is not None else {
        **_discovered_registry(),
        **load_instrument_registry(),
    }
    candidates = {
        symbol
        for symbol, meta in reg.items()
        if meta.is_leveraged_etf
        and meta.direction == "long"
        and meta.abs_multiple == 2.0
        and meta.underlying == source
    }
    if not candidates:
        return None

    preferred = [
        str(symbol).strip().upper()
        for symbol in (allowlist or [])
        if str(symbol).strip()
    ]
    if preferred:
        allowlisted = next((symbol for symbol in preferred if symbol in candidates), None)
        if allowlisted is not None:
            return allowlisted
        discovered = sorted(symbol for symbol in candidates if is_discovered_instrument(symbol))
        return discovered[0] if discovered else None
    return sorted(candidates)[0]


def signal_source_ticker(ticker: str) -> str:
    """Use the underlying signal for a direct long leveraged product."""
    symbol = str(ticker).strip().upper()
    meta = get_instrument(symbol)
    if meta.is_leveraged_etf and meta.direction == "long" and meta.underlying:
        return meta.underlying
    return symbol


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
    allow_single_name_leveraged_products: bool = False,
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
        if not allow_single_name_leveraged_products and is_single_name_leveraged(ticker):
            return (
                False,
                f"{kind_tag}; single-name leveraged ETF buys disabled",
            )
        allowed_symbols = {
            str(symbol).strip().upper()
            for symbol in (leveraged_etf_allowlist or [])
            if str(symbol).strip()
        }
        if (
            allowed_symbols
            and str(ticker).strip().upper() not in allowed_symbols
            and not is_discovered_instrument(ticker)
        ):
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
