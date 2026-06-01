"""US-equity trading session resolution for Alpaca and future Toss integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from enum import Enum
from typing import Iterable, Sequence
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
KST = ZoneInfo("Asia/Seoul")

ALL_ALPACA_EXTENDED_SESSIONS = (
    "pre_market",
    "after_hours",
    "overnight",
)
DEFAULT_ENABLED_ALPACA_SESSIONS = ("regular", *ALL_ALPACA_EXTENDED_SESSIONS)


class TradingSession(str, Enum):
    CLOSED = "closed"
    REGULAR = "regular"
    PRE_MARKET = "pre_market"
    AFTER_HOURS = "after_hours"
    OVERNIGHT = "overnight"
    DAY_MARKET = "day_market"


@dataclass(frozen=True)
class SessionState:
    session: TradingSession
    timestamp_et: datetime
    timestamp_kst: datetime
    is_regular_session: bool
    broker_provider: str

    @property
    def uses_limit_orders(self) -> bool:
        return self.session not in {TradingSession.CLOSED, TradingSession.REGULAR}

    def is_enabled(self, enabled_sessions: Sequence[str]) -> bool:
        normalized = {str(item).strip().lower() for item in enabled_sessions}
        if self.session == TradingSession.CLOSED:
            return False
        return self.session.value in normalized


def _minutes_since_midnight(dt: datetime) -> int:
    return dt.hour * 60 + dt.minute


def _in_minute_range(value: int, start: int, end: int) -> bool:
    if start <= end:
        return start <= value < end
    return value >= start or value < end


def resolve_alpaca_session(dt_et: datetime) -> TradingSession:
    weekday = dt_et.weekday()
    minute = _minutes_since_midnight(dt_et)

    pre_market = (4 * 60, 9 * 60 + 30)
    regular = (9 * 60 + 30, 16 * 60)
    after_hours = (16 * 60, 20 * 60)
    overnight = (20 * 60, 4 * 60)

    if weekday == 5:
        return TradingSession.CLOSED
    if weekday == 6 and minute < overnight[0]:
        return TradingSession.CLOSED
    if weekday == 6 and minute >= overnight[0]:
        return TradingSession.OVERNIGHT

    if _in_minute_range(minute, *pre_market):
        return TradingSession.PRE_MARKET
    if _in_minute_range(minute, *regular):
        return TradingSession.REGULAR
    if _in_minute_range(minute, *after_hours):
        return TradingSession.AFTER_HOURS
    if _in_minute_range(minute, *overnight):
        if weekday == 4 and minute >= overnight[0]:
            return TradingSession.CLOSED
        return TradingSession.OVERNIGHT
    return TradingSession.CLOSED


def _parse_hhmm(value: str, *, field_name: str) -> time:
    parts = str(value).strip().split(":")
    if len(parts) != 2:
        raise ValueError(f"{field_name} must use HH:MM format")
    hour, minute = int(parts[0]), int(parts[1])
    return time(hour=hour, minute=minute)


def resolve_toss_day_market_session(
    dt_kst: datetime,
    *,
    start_kst: str,
    end_kst: str,
) -> TradingSession | None:
    if dt_kst.weekday() >= 5:
        return None
    start = _parse_hhmm(start_kst, field_name="day_market_start_kst")
    end = _parse_hhmm(end_kst, field_name="day_market_end_kst")
    current = dt_kst.time().replace(second=0, microsecond=0)
    if start <= end:
        if start <= current < end:
            return TradingSession.DAY_MARKET
        return None
    if current >= start or current < end:
        return TradingSession.DAY_MARKET
    return None


def resolve_trading_session(
    timestamp: str | datetime,
    *,
    broker_provider: str = "alpaca",
    day_market_start_kst: str = "10:00",
    day_market_end_kst: str = "18:00",
) -> SessionState:
    if isinstance(timestamp, str):
        ts = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
    else:
        ts = timestamp
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=ET)
    dt_et = ts.astimezone(ET)
    dt_kst = ts.astimezone(KST)
    provider = str(broker_provider).strip().lower()

    if provider == "toss":
        day_market = resolve_toss_day_market_session(
            dt_kst,
            start_kst=day_market_start_kst,
            end_kst=day_market_end_kst,
        )
        if day_market is not None:
            session = day_market
        else:
            session = resolve_alpaca_session(dt_et)
    else:
        session = resolve_alpaca_session(dt_et)

    return SessionState(
        session=session,
        timestamp_et=dt_et,
        timestamp_kst=dt_kst,
        is_regular_session=session == TradingSession.REGULAR,
        broker_provider=provider,
    )


def orders_allowed_for_session(
    session_state: SessionState,
    *,
    extended_hours_enabled: bool,
    enabled_trading_sessions: Iterable[str],
) -> bool:
    if session_state.session == TradingSession.CLOSED:
        return False
    if session_state.session == TradingSession.REGULAR:
        return session_state.is_enabled(enabled_trading_sessions)
    if session_state.session == TradingSession.DAY_MARKET:
        return session_state.is_enabled(enabled_trading_sessions)
    if not extended_hours_enabled:
        return False
    return session_state.is_enabled(enabled_trading_sessions)
