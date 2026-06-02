"""Pytest session defaults — keep unit tests free of live LLM calls."""

from __future__ import annotations

import os


def pytest_configure() -> None:
    os.environ.setdefault("TRADING_BOT_SKIP_LLM", "1")
