from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

from src.trading.leveraged_product_routing import resolve_leveraged_product_route


class _Broker:
    def __init__(
        self,
        *,
        tradable: bool = True,
        discovered: list[dict] | None = None,
        discovery_error: Exception | None = None,
    ):
        self.tradable = tradable
        self.discovered = discovered or []
        self.discovery_error = discovery_error

    def get_asset_info(self, ticker: str):
        return {
            "symbol": ticker,
            "active": True,
            "tradable": self.tradable,
            "fractionable": False,
        }

    def discover_leveraged_long_products(self, underlying: str):
        if self.discovery_error is not None:
            raise self.discovery_error
        return list(self.discovered)


def _frame(close: float, volume: float = 1_000.0) -> pd.DataFrame:
    return pd.DataFrame(
        {"close": [close], "adj_close": [close], "volume": [volume]}
    )


def _context(
    *,
    tradable: bool = True,
    auto_discover: bool = False,
    discovered: list[dict] | None = None,
    discovery_error: Exception | None = None,
):
    return SimpleNamespace(
        settings=SimpleNamespace(
            prefer_leveraged_products=True,
            allow_leveraged_etfs=True,
            auto_discover_leveraged_products=auto_discover,
            leveraged_etf_allowlist=["PLUL"],
        ),
        ticker_data={
            "PLUG": _frame(2.2),
            "PLUL": _frame(8.4),
            "RIG": _frame(5.2),
            "NOK": _frame(12.0),
            "LNOK": _frame(48.0),
        },
        broker_adapter=_Broker(
            tradable=tradable,
            discovered=discovered,
            discovery_error=discovery_error,
        ),
        market_clock=object(),
        price_data_freshness={},
    )


@patch(
    "src.trading.leveraged_product_routing.check_price_frame_freshness",
    return_value=(True, "fresh"),
)
def test_routes_to_tradable_direct_product(_freshness):
    route = resolve_leveraged_product_route(_context(), "PLUG")
    assert route.execution_ticker == "PLUL"
    assert route.reference_price == 8.4
    assert route.leveraged is True


def test_falls_back_when_no_direct_product_exists():
    route = resolve_leveraged_product_route(_context(), "RIG")
    assert route.execution_ticker == "RIG"
    assert route.leveraged is False
    assert "no direct" in route.reason


def test_falls_back_when_product_is_not_tradable():
    route = resolve_leveraged_product_route(_context(tradable=False), "PLUG")
    assert route.execution_ticker == "PLUG"
    assert route.leveraged is False


def test_quality_risk_can_force_ordinary_stock_fallback():
    route = resolve_leveraged_product_route(
        _context(),
        "PLUG",
        allow_leveraged=False,
    )

    assert route.execution_ticker == "PLUG"
    assert route.leveraged is False
    assert route.route_allowed is True
    assert "rank quality risk" in route.reason


@patch(
    "src.trading.leveraged_product_routing.register_discovered_leveraged_product"
)
@patch(
    "src.trading.leveraged_product_routing.check_price_frame_freshness",
    return_value=(True, "fresh"),
)
def test_auto_discovers_and_persists_lnok(_freshness, register_product):
    ctx = _context(
        auto_discover=True,
        discovered=[{"symbol": "LNOK", "name": "2X Long NOK ETF"}],
    )

    route = resolve_leveraged_product_route(ctx, "NOK")

    assert route.execution_ticker == "LNOK"
    assert route.leveraged is True
    assert route.route_allowed is True
    register_product.assert_called_once_with("LNOK", "NOK", multiple=2.0)


def test_discovery_api_error_blocks_ordinary_stock_fallback():
    route = resolve_leveraged_product_route(
        _context(
            auto_discover=True,
            discovery_error=ConnectionError("catalog unavailable"),
        ),
        "RIG",
    )

    assert route.execution_ticker == "RIG"
    assert route.leveraged is False
    assert route.route_allowed is False
    assert "discovery failed" in route.reason
