from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.alpaca_client import (
    discover_leveraged_long_assets,
    get_active_us_equity_assets,
    reset_asset_catalog_cache,
)


def _asset(symbol: str, name: str):
    return SimpleNamespace(
        symbol=symbol,
        name=name,
        status="ACTIVE",
        tradable=True,
        fractionable=False,
        marginable=True,
    )


def setup_function() -> None:
    reset_asset_catalog_cache()


def test_alpaca_asset_catalog_is_cached(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "src.alpaca_client.ASSET_CATALOG_CACHE_PATH",
        tmp_path / "alpaca_asset_catalog.json",
    )
    client = MagicMock()
    client.get_all_assets.return_value = [
        _asset("LNOK", "Defiance Daily Target 2X Long NOK ETF")
    ]
    with patch("src.alpaca_client.get_trading_client", return_value=client):
        first = get_active_us_equity_assets()
        reset_asset_catalog_cache()
        second = get_active_us_equity_assets()

    assert first == second
    client.get_all_assets.assert_called_once()


@patch("src.alpaca_client.get_active_us_equity_assets")
def test_discovery_matches_exact_underlying_token(mock_assets) -> None:
    mock_assets.return_value = [
        {
            "symbol": "LNOK",
            "name": "Defiance Daily Target 2X Long NOK ETF",
            "active": True,
            "tradable": True,
        },
        {
            "symbol": "AIBU",
            "name": "Direxion Daily AI and Big Data Bull 2X ETF",
            "active": True,
            "tradable": True,
        },
    ]

    assert [row["symbol"] for row in discover_leveraged_long_assets("NOK")] == [
        "LNOK"
    ]
    assert discover_leveraged_long_assets("DATA") == []
