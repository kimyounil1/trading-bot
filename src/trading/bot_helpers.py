"""Shared trading bot helpers (signals, peaks, audit wrappers)."""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.daily_bar_session import check_price_frame_freshness
from src.daily_bar_session import drop_incomplete_session_bar
from src.logger import log_execution_audit
from src.ml_model import predict_ai_score_from_bundle
from src.order_intent import AuditContext
from src.strategy import add_indicators, generate_signal

PEAKS_PATH = Path("data/trailing_peaks.json")

# Test alias
_check_price_frame_freshness = check_price_frame_freshness

def quarantine_corrupt_peaks_file(path: Path) -> None:
    corrupt_path = path.with_suffix(f"{path.suffix}.corrupt")
    try:
        if corrupt_path.exists():
            corrupt_path.unlink()
        path.replace(corrupt_path)
        print(f"Warning: moved corrupt peaks file to {corrupt_path}")
    except OSError as exc:
        print(f"Warning: failed to quarantine corrupt peaks file {path}: {exc}")

def normalize_peaks(payload: object) -> dict[str, float]:
    if not isinstance(payload, dict):
        raise ValueError("peaks payload must be a JSON object")

    normalized: dict[str, float] = {}
    for ticker, value in payload.items():
        if ticker is None:
            continue
        try:
            normalized[str(ticker).strip().upper()] = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid peak value for {ticker!r}: {value!r}") from exc
    return normalized

def load_peaks() -> dict[str, float]:
    if not PEAKS_PATH.exists():
        return {}

    try:
        payload = json.loads(PEAKS_PATH.read_text(encoding="utf-8"))
        return normalize_peaks(payload)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"Warning: failed to load peaks from {PEAKS_PATH}: {exc}")
        quarantine_corrupt_peaks_file(PEAKS_PATH)
        return {}

def save_peaks(peaks: dict[str, float]) -> None:
    PEAKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    normalized = normalize_peaks(peaks)
    temp_path = PEAKS_PATH.with_suffix(f"{PEAKS_PATH.suffix}.tmp")
    serialized = json.dumps(normalized, indent=2, sort_keys=True)
    temp_path.write_text(serialized, encoding="utf-8")
    with temp_path.open("r+", encoding="utf-8") as handle:
        handle.flush()
        os.fsync(handle.fileno())
    temp_path.replace(PEAKS_PATH)

from src.daily_bar_session import check_price_frame_freshness as _check_price_frame_freshness
from src.daily_bar_session import drop_incomplete_session_bar


def format_llm_verdict(is_ok: bool | None, reason: str = "") -> str:
    if is_ok is None:
        return ""
    verdict = "ACCEPT" if is_ok else "REJECT"
    return f"{verdict}: {reason}" if reason else verdict


def summarize_run_metrics(
    live_order_count: int,
    skipped_reasons: Counter,
    data_error_count: int,
    api_error_count: int,
) -> str:
    skip_summary = ", ".join(
        f"{reason}={count}" for reason, count in skipped_reasons.most_common()
    ) or "none"
    return (
        f"orders_submitted={live_order_count}, "
        f"skips={skip_summary}, "
        f"data_errors={data_error_count}, "
        f"api_errors={api_error_count}"
    )


def resolve_full_exit_reason(
    *,
    unrealized_plpc: float,
    stop_loss_pct: float,
    take_profit_pct: float,
    trailing_drawdown: float | None,
    trailing_stop_pct: float,
    signal: str,
    ai_exit_triggered: bool,
    holding_days: int = 0,
    max_holding_days: int = 30,
) -> str | None:
    if stop_loss_pct > 0 and unrealized_plpc <= -stop_loss_pct:
        return "stop loss triggered"
    if max_holding_days > 0 and holding_days >= max_holding_days:
        return f"max holding period reached ({holding_days} days)"
    if (
        trailing_drawdown is not None
        and trailing_stop_pct > 0
        and trailing_drawdown >= trailing_stop_pct
    ):
        return "trailing stop triggered"
    if ai_exit_triggered:
        return "ai exit triggered"
    if signal == "SELL":
        return "strategy sell signal"
    if take_profit_pct > 0 and unrealized_plpc >= take_profit_pct:
        return "take profit triggered"
    return None
from src.macro_loader import load_macro_data


def apply_volume_volatility_filters(signal: str, indicator_df, settings) -> str:
    if signal != "BUY":
        return signal

    latest = indicator_df.iloc[-1]

    if getattr(settings, "volume_filter_enabled", False):
        lookback = int(getattr(settings, "volume_lookback_days", 20))
        if lookback <= 0:
            raise ValueError("volume_lookback_days must be positive")
        volume_ma = indicator_df["volume"].rolling(lookback).mean().iloc[-1]
        if (
            pd.isna(volume_ma)
            or volume_ma <= 0
            or latest["volume"] / volume_ma < float(settings.min_volume_ratio)
        ):
            return "HOLD"

    if getattr(settings, "volatility_filter_enabled", False):
        lookback = int(getattr(settings, "volatility_lookback_days", 20))
        if lookback <= 0:
            raise ValueError("volatility_lookback_days must be positive")
        volatility = indicator_df["close"].pct_change().rolling(lookback).std().iloc[-1]
        if pd.isna(volatility) or volatility > float(settings.max_volatility):
            return "HOLD"

    return signal


def offline_account_summary() -> dict:
    return {
        "status": "UNKNOWN",
        "currency": "USD",
        "cash": 0.0,
        "portfolio_value": 0.0,
        "buying_power": 0.0,
        "positions_count": 0,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AI trading bot MVP. Default mode is dry-run."
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Submit real paper orders to Alpaca. Without this flag, dry-run only.",
    )
    parser.add_argument(
        "--sleeve-rebalance-only",
        action="store_true",
        help=(
            "Run portfolio sleeve allocation rebalance only (retag + trim sells). "
            "Implies --execute for order submission when the market allows."
        ),
    )
    args = parser.parse_args()
    if args.sleeve_rebalance_only:
        args.execute = True
    return args


def get_signal_for_ticker(
    ticker: str,
    raw_df,
    settings,
    ai_model_bundle=None,
    market_regime_bullish: bool = True,
    vix_df=None,
    spy_df=None,
    macro_df=None,
    market_clock=None,
) -> tuple[str, object, float | None]:
    if raw_df.empty:
        raise ValueError(f"No price data available for {ticker}")

    signal_df = (
        drop_incomplete_session_bar(raw_df, market_clock)
        if market_clock is not None
        else raw_df
    )
    if signal_df.empty:
        raise ValueError(f"No completed daily bars available for {ticker}")

    df = add_indicators(
        signal_df,
        ma_fast=settings.ma_fast,
        ma_slow=settings.ma_slow,
    )
    if df.empty:
        raise ValueError(
            f"Not enough price history to generate signal for {ticker} "
            f"(rows={len(raw_df)}, ma_slow={settings.ma_slow})"
        )
    signal = generate_signal(df, rsi_buy_limit=settings.rsi_buy_limit)
    if (
        signal == "BUY"
        and getattr(settings, "market_regime_filter_enabled", False)
        and not market_regime_bullish
    ):
        signal = "HOLD"
    signal = apply_volume_volatility_filters(signal, df, settings)
    latest = df.iloc[-1]

    ai_score = None
    if getattr(settings, "use_ai_score", False):
        try:
            if ai_model_bundle is None:
                raise ValueError("AI score model was not loaded")
            ai_score = predict_ai_score_from_bundle(
                signal_df,
                ai_model_bundle,
                vix_df=vix_df,
                spy_df=spy_df,
                macro_df=macro_df,
            )
        except Exception:
            ai_score = None

    return signal, latest, ai_score


def execution_reference_price(
    indicators: dict | None,
    *,
    fallback: float | None = None,
) -> float:
    if indicators:
        for key in ("close", "adj_close"):
            value = indicators.get(key)
            if value is not None and float(value) > 0:
                return float(value)
    if fallback is not None and float(fallback) > 0:
        return float(fallback)
    raise ValueError("missing reference price for extended-hours limit order")


def execution_block_label(execute_orders: bool, market_clock) -> str:
    if not execute_orders:
        return "DRY_RUN_ONLY"
    if market_clock.session.value == "closed":
        return "TRADING_SESSION_CLOSED"
    if not market_clock.orders_allowed:
        return "TRADING_SESSION_DISABLED"
    return "EXECUTION_BLOCKED"


def order_is_filled(status: str) -> bool:
    normalized = str(status).upper()
    return "FILLED" in normalized and "PARTIALLY" not in normalized


def audit_log(audit_ctx: AuditContext, **kwargs) -> None:
    log_execution_audit(**kwargs, **audit_ctx.as_audit_fields())


def filled_notional(checked_order: dict, fallback: float) -> float:
    filled_qty = checked_order.get("filled_qty")
    filled_avg_price = checked_order.get("filled_avg_price")
    if (
        filled_qty in (None, "", "0", "0.0", "None")
        or filled_avg_price in (None, "", "None")
        or str(filled_qty).lower() == "none"
        or str(filled_avg_price).lower() == "none"
    ):
        return 0.0
    try:
        return float(filled_qty) * float(filled_avg_price)
    except (TypeError, ValueError):
        return 0.0
