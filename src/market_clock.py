from dataclasses import dataclass
from datetime import datetime, timezone

from src.alpaca_client import get_trading_client


@dataclass
class MarketClock:
    is_open: bool
    timestamp: str
    next_open: str
    next_close: str


def get_market_clock() -> MarketClock:
    client = get_trading_client()

    try:
        clock = client.get_clock()
    except Exception as exc:
        # Dry-run and reporting paths should not die just because Alpaca is unreachable.
        now = datetime.now(timezone.utc)
        return MarketClock(
            is_open=False,
            timestamp=now.isoformat(timespec="seconds"),
            next_open=now.isoformat(timespec="seconds"),
            next_close=now.isoformat(timespec="seconds"),
        )

    return MarketClock(
        is_open=bool(clock.is_open),
        timestamp=str(clock.timestamp),
        next_open=str(clock.next_open),
        next_close=str(clock.next_close),
    )


def print_market_clock() -> MarketClock:
    clock = get_market_clock()

    print("Market clock")
    print("-" * 80)
    print(f"is_open={clock.is_open}")
    print(f"timestamp={clock.timestamp}")
    print(f"next_open={clock.next_open}")
    print(f"next_close={clock.next_close}")

    return clock
