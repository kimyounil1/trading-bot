"""Backward-compatible re-exports; prefer src.brokers."""

from src.brokers import (
    AlpacaBrokerAdapter,
    BrokerAdapter,
    OrderSubmission,
    PaperBrokerAdapter,
    TossBrokerAdapter,
    get_broker_adapter,
)

__all__ = [
    "AlpacaBrokerAdapter",
    "BrokerAdapter",
    "OrderSubmission",
    "PaperBrokerAdapter",
    "TossBrokerAdapter",
    "get_broker_adapter",
]
