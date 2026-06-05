"""Broker adapters: Alpaca (paper API), in-memory paper/fake, Toss stub."""

from __future__ import annotations

from typing import Any

from src.brokers.alpaca import AlpacaBrokerAdapter
from src.brokers.base import BrokerAdapter, OrderSubmission
from src.brokers.paper import PaperBrokerAdapter
from src.brokers.toss import TossBrokerAdapter

__all__ = [
    "AlpacaBrokerAdapter",
    "BrokerAdapter",
    "OrderSubmission",
    "PaperBrokerAdapter",
    "TossBrokerAdapter",
    "broker_account_snapshot",
    "get_broker_adapter",
]


def broker_account_snapshot(provider: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Account + positions via adapter (CMS/reporting helper)."""
    adapter = get_broker_adapter(provider)
    return adapter.get_account(), adapter.get_positions()


def get_broker_adapter(provider: str) -> BrokerAdapter:
    normalized = str(provider).strip().lower()
    if normalized == "toss":
        return TossBrokerAdapter()
    if normalized in {"paper", "fake"}:
        return PaperBrokerAdapter()
    if normalized != "alpaca":
        raise ValueError(f"Unsupported broker_provider: {provider}")
    return AlpacaBrokerAdapter()
