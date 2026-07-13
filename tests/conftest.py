"""Pytest session defaults — keep unit tests free of live LLM calls,
and keep test runs from polluting the production CSV logs
(logs/execution_audit.csv etc. feed live analysis reports)."""

from __future__ import annotations

import os
import tempfile


def pytest_configure() -> None:
    os.environ.setdefault("TRADING_BOT_SKIP_LLM", "1")
    # Test runs must never inherit a developer's live Telegram setting.
    os.environ["TELEGRAM_ENABLED"] = "False"

    log_dir = tempfile.mkdtemp(prefix="trading-bot-test-logs-")
    os.environ.setdefault("EXECUTION_AUDIT_LOG_PATH", os.path.join(log_dir, "execution_audit.csv"))
    os.environ.setdefault("SIGNAL_LOG_PATH", os.path.join(log_dir, "signals.csv"))
    os.environ.setdefault("ORDER_LOG_PATH", os.path.join(log_dir, "orders.csv"))
