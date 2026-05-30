"""Universe profile loader ([AGY])."""

import os
from unittest import mock

import pytest

from src.universe_loader import (
    get_universe_profile,
    load_master_tickers,
    load_smoke_tickers,
    normalize_tickers,
    resolve_scan_tickers,
)


def test_normalize_tickers_dedupes_and_uppercases():
    assert normalize_tickers(["aapl", " AAPL ", "msft"]) == ["AAPL", "MSFT"]


def test_smoke_profile_uses_smoke_file():
    paper = ["ZZZZ", "AAAA"]
    smoke = resolve_scan_tickers(paper, profile="smoke")
    assert smoke == load_smoke_tickers()
    assert len(smoke) <= 15


def test_research_profile_loads_master_only():
    master = load_master_tickers()
    assert len(master) >= 200
    resolved = resolve_scan_tickers(["ONLY_ONE"], profile="research")
    assert resolved == master
    assert "ONLY_ONE" not in resolved


def test_paper_profile_keeps_config_tickers():
    cfg = ["NVDA", "MSFT"]
    assert resolve_scan_tickers(cfg, profile="paper") == ["NVDA", "MSFT"]


def test_invalid_profile_raises():
    with pytest.raises(ValueError, match="Unknown universe profile"):
        resolve_scan_tickers([], profile="invalid")


def test_get_universe_profile_from_env():
    with mock.patch.dict(os.environ, {"UNIVERSE_PROFILE": "smoke"}, clear=False):
        assert get_universe_profile() == "smoke"
