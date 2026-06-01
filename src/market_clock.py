from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from src.alpaca_client import get_trading_client
from src.trading_session import (
    SessionState,
    TradingSession,
    orders_allowed_for_session,
    resolve_trading_session,
)

if TYPE_CHECKING:
    from src.settings import StrategySettings


@dataclass
class MarketClock:
    is_open: bool
    timestamp: str
    next_open: str
    next_close: str
    session: TradingSession = TradingSession.CLOSED
    broker_provider: str = "alpaca"
    extended_hours_enabled: bool = False
    orders_allowed: bool = False

    @property
    def is_regular_session(self) -> bool:
        return self.session == TradingSession.REGULAR


def _fallback_clock() -> MarketClock:
    now = datetime.now(timezone.utc)
    iso = now.isoformat(timespec="seconds")
    return MarketClock(
        is_open=False,
        timestamp=iso,
        next_open=iso,
        next_close=iso,
        session=TradingSession.CLOSED,
        orders_allowed=False,
    )


def get_market_clock(settings: Optional["StrategySettings"] = None) -> MarketClock:
    broker_provider = "alpaca"
    extended_hours_enabled = False
    enabled_trading_sessions = ("regular",)
    day_market_start_kst = "10:00"
    day_market_end_kst = "18:00"

    if settings is not None:
        broker_provider = str(getattr(settings, "broker_provider", "alpaca"))
        extended_hours_enabled = bool(getattr(settings, "extended_hours_enabled", False))
        enabled_trading_sessions = tuple(
            getattr(settings, "enabled_trading_sessions", ("regular",))
        )
        day_market_start_kst = str(getattr(settings, "day_market_start_kst", "10:00"))
        day_market_end_kst = str(getattr(settings, "day_market_end_kst", "18:00"))

    client = get_trading_client()

    try:
        clock = client.get_clock()
    except Exception:
        fallback = _fallback_clock()
        session_state = resolve_trading_session(
            fallback.timestamp,
            broker_provider=broker_provider,
            day_market_start_kst=day_market_start_kst,
            day_market_end_kst=day_market_end_kst,
        )
        return MarketClock(
            is_open=False,
            timestamp=fallback.timestamp,
            next_open=fallback.next_open,
            next_close=fallback.next_close,
            session=session_state.session,
            broker_provider=broker_provider,
            extended_hours_enabled=extended_hours_enabled,
            orders_allowed=orders_allowed_for_session(
                session_state,
                extended_hours_enabled=extended_hours_enabled,
                enabled_trading_sessions=enabled_trading_sessions,
            ),
        )

    timestamp = str(clock.timestamp)
    session_state = resolve_trading_session(
        timestamp,
        broker_provider=broker_provider,
        day_market_start_kst=day_market_start_kst,
        day_market_end_kst=day_market_end_kst,
    )
    allowed = orders_allowed_for_session(
        session_state,
        extended_hours_enabled=extended_hours_enabled,
        enabled_trading_sessions=enabled_trading_sessions,
    )

    return MarketClock(
        is_open=bool(clock.is_open),
        timestamp=timestamp,
        next_open=str(clock.next_open),
        next_close=str(clock.next_close),
        session=session_state.session,
        broker_provider=broker_provider,
        extended_hours_enabled=extended_hours_enabled,
        orders_allowed=allowed,
    )


def print_market_clock(settings: Optional["StrategySettings"] = None) -> MarketClock:
    clock = get_market_clock(settings)

    print("Market clock")
    print("-" * 80)
    print(f"broker_provider={clock.broker_provider}")
    print(f"session={clock.session.value}")
    print(f"is_open={clock.is_open}")
    print(f"orders_allowed={clock.orders_allowed}")
    print(f"extended_hours_enabled={clock.extended_hours_enabled}")
    print(f"timestamp={clock.timestamp}")
    print(f"next_open={clock.next_open}")
    print(f"next_close={clock.next_close}")

    return clock
