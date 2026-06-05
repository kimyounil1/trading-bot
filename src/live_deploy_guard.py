"""Double-confirm guards before live order submission."""

from __future__ import annotations

import os


CONFIRM_PHRASE = "YES_I_UNDERSTAND"


def is_live_trading_env() -> bool:
    return os.environ.get("TRADING_ENV", "").strip().lower() == "live"


def allow_live_trading_env_flag() -> bool:
    return os.environ.get("ALLOW_LIVE_TRADING", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def live_confirm_phrase_ok() -> bool:
    return os.environ.get("CONFIRM_LIVE_TRADING", "").strip() == CONFIRM_PHRASE


def assert_live_execution_allowed(*, execute: bool, trading_environment: str) -> None:
    """Raise if live execute is attempted without explicit operator confirmation."""
    if not execute:
        return
    live = trading_environment == "live" or is_live_trading_env()
    if not live:
        return
    if allow_live_trading_env_flag() or live_confirm_phrase_ok():
        return
    raise RuntimeError(
        "Live execution blocked: set TRADING_ENV=live and either "
        "CONFIRM_LIVE_TRADING=YES_I_UNDERSTAND or ALLOW_LIVE_TRADING=true"
    )
