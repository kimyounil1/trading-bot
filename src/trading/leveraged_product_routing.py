"""Route an underlying BUY signal to a directly linked 2x-long product."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.daily_bar_session import check_price_frame_freshness
from src.data_loader import load_price_data_batch
from src.instrument_meta import (
    preferred_leveraged_long_product,
    register_discovered_leveraged_product,
)


@dataclass(frozen=True)
class LeveragedProductRoute:
    signal_ticker: str
    execution_ticker: str
    reference_price: float
    leveraged: bool
    reason: str
    route_allowed: bool = True


def _latest_price(frame: Any) -> float:
    for column in ("close", "adj_close"):
        if column in frame.columns:
            value = float(frame[column].iloc[-1])
            if value > 0:
                return value
    raise ValueError("leveraged product price data has no positive close")


def _underlying_route(
    ctx: Any,
    ticker: str,
    reason: str,
    *,
    fallback_price: float | None = None,
    route_allowed: bool = True,
) -> LeveragedProductRoute:
    frame = ctx.ticker_data[ticker]
    try:
        reference_price = _latest_price(frame)
    except (IndexError, KeyError, TypeError, ValueError):
        if fallback_price is None or float(fallback_price) <= 0:
            raise
        reference_price = float(fallback_price)
    return LeveragedProductRoute(
        signal_ticker=ticker,
        execution_ticker=ticker,
        reference_price=reference_price,
        leveraged=False,
        reason=reason,
        route_allowed=route_allowed,
    )


def _load_fresh_product_frame(ctx: Any, product: str) -> tuple[Any | None, str]:
    if product not in ctx.ticker_data:
        try:
            loaded = load_price_data_batch([product], period="2y")
            ctx.ticker_data.update(loaded)
        except Exception as exc:
            return None, f"price data unavailable: {exc}"
    frame = ctx.ticker_data.get(product)
    if frame is None or frame.empty:
        return None, "price data is empty"
    fresh, freshness_reason = check_price_frame_freshness(frame, ctx.market_clock)
    ctx.price_data_freshness[product] = (fresh, freshness_reason)
    if not fresh:
        return None, f"price data not fresh: {freshness_reason}"
    return frame, ""


def _average_dollar_volume(frame: Any, lookback: int = 20) -> float:
    close_column = "close" if "close" in frame.columns else "adj_close"
    if close_column not in frame.columns or "volume" not in frame.columns:
        return 0.0
    values = (frame[close_column] * frame["volume"]).tail(lookback).dropna()
    return float(values.mean()) if not values.empty else 0.0


def _discover_product(ctx: Any, source: str) -> tuple[str | None, str, bool]:
    """Return (product, reason, lookup_succeeded)."""
    try:
        candidates = ctx.broker_adapter.discover_leveraged_long_products(source)
    except Exception as exc:
        return None, f"leveraged product discovery failed: {exc}", False
    if not candidates:
        return None, "no direct 2x-long product mapped or discovered", True

    eligible: list[tuple[str, float]] = []
    validation_errors: list[str] = []
    for candidate in candidates:
        product = str(candidate.get("symbol") or "").strip().upper()
        if not product:
            continue
        try:
            asset = ctx.broker_adapter.get_asset_info(product)
        except Exception as exc:
            validation_errors.append(f"{product}: {exc}")
            continue
        if not bool(asset.get("active")) or not bool(asset.get("tradable")):
            continue
        security_type = str(asset.get("security_type") or "").upper()
        leverage_factor = asset.get("leverage_factor")
        if security_type and security_type != "ETF":
            continue
        if leverage_factor not in (None, ""):
            try:
                if float(leverage_factor) != 2.0:
                    continue
            except (TypeError, ValueError):
                validation_errors.append(
                    f"{product}: invalid leverage factor {leverage_factor}"
                )
                continue
        frame, data_error = _load_fresh_product_frame(ctx, product)
        if frame is None:
            validation_errors.append(f"{product}: {data_error}")
            continue
        eligible.append((product, _average_dollar_volume(frame)))

    if not eligible:
        if validation_errors:
            return None, "; ".join(validation_errors), False
        return None, "discovered products are not active/tradable on broker", True

    if len(eligible) == 1:
        return eligible[0][0], "unique broker-discovered direct 2x-long product", True
    liquid = [item for item in eligible if item[1] > 0]
    if not liquid:
        symbols = ",".join(symbol for symbol, _ in eligible)
        return None, f"multiple discovered products but liquidity unavailable: {symbols}", False
    liquid.sort(key=lambda item: (-item[1], item[0]))
    return liquid[0][0], "highest 20-day average dollar volume", True


def resolve_leveraged_product_route(
    ctx: Any,
    ticker: str,
    *,
    signal: str = "BUY",
    fallback_price: float | None = None,
    allow_leveraged: bool = True,
) -> LeveragedProductRoute:
    """Prefer a direct 2x-long ETF, with an explicit ordinary-stock fallback."""
    source = str(ticker).strip().upper()
    settings = ctx.settings
    if signal != "BUY":
        return _underlying_route(
            ctx,
            source,
            f"signal is {signal}",
            fallback_price=fallback_price,
        )
    if not allow_leveraged:
        return _underlying_route(
            ctx,
            source,
            "rank quality risk blocked leveraged product; ordinary-stock fallback",
            fallback_price=fallback_price,
        )
    if not bool(getattr(settings, "prefer_leveraged_products", False)):
        return _underlying_route(
            ctx,
            source,
            "leveraged product preference disabled",
            fallback_price=fallback_price,
        )
    if not bool(getattr(settings, "allow_leveraged_etfs", False)):
        return _underlying_route(
            ctx,
            source,
            "leveraged ETF buys disabled",
            fallback_price=fallback_price,
        )

    product = preferred_leveraged_long_product(
        source,
        allowlist=list(getattr(settings, "leveraged_etf_allowlist", [])),
    )
    if product is None:
        if not bool(getattr(settings, "auto_discover_leveraged_products", False)):
            return _underlying_route(
                ctx,
                source,
                "no direct 2x-long product mapped; auto discovery disabled",
                fallback_price=fallback_price,
            )
        product, discovery_reason, lookup_succeeded = _discover_product(ctx, source)
        if product is None:
            return _underlying_route(
                ctx,
                source,
                discovery_reason,
                fallback_price=fallback_price,
                route_allowed=lookup_succeeded,
            )
        try:
            register_discovered_leveraged_product(product, source, multiple=2.0)
        except (OSError, ValueError) as exc:
            return _underlying_route(
                ctx,
                source,
                f"{product} metadata persistence failed: {exc}",
                fallback_price=fallback_price,
                route_allowed=False,
            )
        product_reason = f"broker-discovered 2x-long product {product} ({discovery_reason})"
    else:
        product_reason = f"direct 2x-long product {product}"

    try:
        asset = ctx.broker_adapter.get_asset_info(product)
    except Exception as exc:
        return _underlying_route(
            ctx,
            source,
            f"{product} broker availability check failed: {exc}",
            fallback_price=fallback_price,
            route_allowed=False,
        )
    if not bool(asset.get("active")) or not bool(asset.get("tradable")):
        return _underlying_route(
            ctx,
            source,
            f"{product} is not active/tradable",
            fallback_price=fallback_price,
        )
    security_type = str(asset.get("security_type") or "").upper()
    leverage_factor = asset.get("leverage_factor")
    try:
        broker_meta_valid = (
            (not security_type or security_type == "ETF")
            and (
                leverage_factor in (None, "")
                or float(leverage_factor) == 2.0
            )
        )
    except (TypeError, ValueError):
        broker_meta_valid = False
    if not broker_meta_valid:
        return _underlying_route(
            ctx,
            source,
            f"{product} broker metadata does not confirm a 2x ETF",
            fallback_price=fallback_price,
            route_allowed=False,
        )

    product_frame, data_error = _load_fresh_product_frame(ctx, product)
    if product_frame is None:
        return _underlying_route(
            ctx,
            source,
            f"{product} {data_error}",
            fallback_price=fallback_price,
            route_allowed=False,
        )

    return LeveragedProductRoute(
        signal_ticker=source,
        execution_ticker=product,
        reference_price=_latest_price(product_frame),
        leveraged=True,
        reason=product_reason,
    )
