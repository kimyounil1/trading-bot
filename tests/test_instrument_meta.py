"""Instrument registry and leverage gates ([AGY])."""

import pandas as pd
import src.instrument_meta as instrument_meta

from src.instrument_meta import (
    check_instrument_buy_allowed,
    clear_instrument_registry_cache,
    get_instrument,
    is_discovered_instrument,
    is_single_name_leveraged,
    load_instrument_registry,
    preferred_leveraged_long_product,
    register_discovered_leveraged_product,
    signal_source_ticker,
)
from src.risk_manager import apply_effective_leverage_exposure_limits


def setup_function() -> None:
    clear_instrument_registry_cache()


def test_registry_marks_tqqq_leveraged():
    meta = get_instrument("TQQQ")
    assert meta.is_leveraged_etf
    assert meta.abs_multiple == 3.0


def test_leveraged_buy_blocked_by_default():
    allowed, reason = check_instrument_buy_allowed("TQQQ", set())
    assert allowed is False
    assert "allow_leveraged_etfs=false" in reason


def test_leveraged_buy_allowed_when_enabled_and_vix_low():
    vix = pd.DataFrame({"close": [20.0]})
    allowed, _ = check_instrument_buy_allowed(
        "TQQQ",
        set(),
        allow_leveraged_etfs=True,
        leveraged_etf_allowlist=["TQQQ"],
        max_leveraged_etf_positions=1,
        block_leveraged_etfs_vix_above=28.0,
        vix_df=vix,
    )
    assert allowed is True


def test_leveraged_buy_blocked_outside_allowlist():
    allowed, reason = check_instrument_buy_allowed(
        "SOXS",
        set(),
        allow_leveraged_etfs=True,
        leveraged_etf_allowlist=["SOXL"],
    )
    assert allowed is False
    assert "allowlist" in reason


def test_leveraged_buy_blocked_when_vix_high():
    vix = pd.DataFrame({"close": [35.0]})
    allowed, reason = check_instrument_buy_allowed(
        "SOXL",
        set(),
        allow_leveraged_etfs=True,
        leveraged_etf_allowlist=["SOXL"],
        block_leveraged_etfs_vix_above=28.0,
        vix_df=vix,
    )
    assert allowed is False
    assert "VIX" in reason


def test_effective_leverage_exposure_cap():
    positions = {
        "AAPL": {"market_value": 4000.0},
        "TQQQ": {"market_value": 3000.0},
    }
    decision = apply_effective_leverage_exposure_limits(
        ticker="NVDA",
        order_amount=2000.0,
        portfolio_value=10000.0,
        positions_by_symbol=positions,
    )
    assert decision.allowed is False


def test_registry_loads():
    reg = load_instrument_registry()
    assert "SPY" in reg
    assert reg["SPY"].kind == "etf"


def test_preferred_direct_2x_product_uses_allowlist_order():
    assert preferred_leveraged_long_product(
        "PLUG",
        allowlist=["PLUL"],
    ) == "PLUL"
    assert signal_source_ticker("PLUL") == "PLUG"


def test_missing_direct_2x_product_returns_none():
    assert preferred_leveraged_long_product("RIG", allowlist=["PLUL"]) is None


def test_discovered_product_persists_and_bypasses_static_allowlist(
    tmp_path,
    monkeypatch,
):
    path = tmp_path / "discovered_instruments.json"
    monkeypatch.setattr(instrument_meta, "DISCOVERED_REGISTRY_PATH", path)
    clear_instrument_registry_cache()

    register_discovered_leveraged_product("XYZL", "XYZ", multiple=2.0)
    clear_instrument_registry_cache()

    meta = get_instrument("XYZL")
    assert meta.is_leveraged_etf
    assert meta.underlying == "XYZ"
    assert signal_source_ticker("XYZL") == "XYZ"
    assert is_discovered_instrument("XYZL") is True
    allowed, _ = check_instrument_buy_allowed(
        "XYZL",
        set(),
        allow_leveraged_etfs=True,
        allow_single_name_leveraged_products=True,
        leveraged_etf_allowlist=["PLUL"],
    )
    assert allowed is True


def test_index_and_sector_leverage_are_not_single_name():
    assert is_single_name_leveraged("TQQQ") is False
    assert is_single_name_leveraged("SOXL") is False
    assert is_single_name_leveraged("AAPL") is False
    assert is_single_name_leveraged("AMDL") is True
    assert is_single_name_leveraged("NVDL") is True


def test_single_name_leveraged_buy_blocked_even_if_allowlisted():
    allowed, reason = check_instrument_buy_allowed(
        "AMDL",
        set(),
        allow_leveraged_etfs=True,
        leveraged_etf_allowlist=["AMDL", "TQQQ", "SOXL"],
    )
    assert allowed is False
    assert "single-name" in reason


def test_index_leveraged_buy_still_allowed():
    vix = pd.DataFrame({"close": [20.0]})
    for ticker in ("TQQQ", "SOXL"):
        allowed, _ = check_instrument_buy_allowed(
            ticker,
            set(),
            allow_leveraged_etfs=True,
            leveraged_etf_allowlist=["TQQQ", "SOXL"],
            max_leveraged_etf_positions=2,
            block_leveraged_etfs_vix_above=28.0,
            vix_df=vix,
        )
        assert allowed is True


def test_discovered_single_name_product_blocked_by_default(
    tmp_path,
    monkeypatch,
):
    path = tmp_path / "discovered_instruments.json"
    monkeypatch.setattr(instrument_meta, "DISCOVERED_REGISTRY_PATH", path)
    clear_instrument_registry_cache()
    register_discovered_leveraged_product("XYZL", "XYZ", multiple=2.0)
    clear_instrument_registry_cache()

    allowed, reason = check_instrument_buy_allowed(
        "XYZL",
        set(),
        allow_leveraged_etfs=True,
        leveraged_etf_allowlist=["TQQQ"],
    )
    assert allowed is False
    assert "single-name" in reason
