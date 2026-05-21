import json
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.settings import load_settings
from src.market_clock import get_market_clock
from src.alpaca_client import get_account_summary, get_positions_summary
from src.data_loader import load_price_data_batch
from src.strategy import add_indicators, generate_signal
from src.risk_manager import (
    apply_buy_safety_limits,
    check_buy_allowed,
    check_exit_allowed,
    get_recent_buy_symbols,
    get_today_buy_notional,
)
from src.ml_model import load_ai_score_model, predict_ai_score_from_bundle


CACHE_DIR = Path("logs/candidate_cache")
LATEST_META_PATH = CACHE_DIR / "latest_meta.json"
LATEST_BUY_PATH = CACHE_DIR / "latest_buy.csv"
LATEST_EXIT_PATH = CACHE_DIR / "latest_exit.csv"
LATEST_QUALITY_PATH = CACHE_DIR / "latest_quality.csv"
LATEST_ERRORS_PATH = CACHE_DIR / "latest_errors.csv"


def get_signal_for_cache(ticker: str, raw_df: pd.DataFrame, settings, ai_model_bundle=None):
    df = add_indicators(
        raw_df,
        ma_fast=settings.ma_fast,
        ma_slow=settings.ma_slow,
    )
    signal = generate_signal(df, rsi_buy_limit=settings.rsi_buy_limit)
    latest = df.iloc[-1]

    ai_score = None
    ai_score_status = "DISABLED"
    ai_score_error = ""
    if getattr(settings, "use_ai_score", False):
        try:
            if ai_model_bundle is None:
                raise ValueError("AI score model was not loaded")
            ai_score = predict_ai_score_from_bundle(raw_df, ai_model_bundle)
            ai_score_status = "OK"
        except Exception as exc:
            ai_score_status = "ERROR"
            ai_score_error = str(exc)
            ai_score = None

    return signal, latest, ai_score, ai_score_status, ai_score_error


def build_data_quality_rows(
    tickers: list[str],
    ticker_data: dict[str, pd.DataFrame],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    now = pd.Timestamp.now()
    rows = []

    for ticker in tickers:
        df = ticker_data.get(ticker)

        if df is None or df.empty:
            rows.append(
                {
                    "ticker": ticker,
                    "data_status": "ERROR",
                    "error_type": "missing_price_data",
                    "error": "No price data loaded for ticker",
                    "row_count": 0,
                    "last_price_date": None,
                    "data_age_days": None,
                }
            )
            continue

        row_count = len(df)
        required_columns = {"date", "open", "high", "low", "close", "volume"}
        missing_columns = sorted(required_columns - set(df.columns))

        last_price_date = None
        data_age_days = None
        error_type = ""
        error = ""
        status = "OK"

        if missing_columns:
            status = "ERROR"
            error_type = "missing_columns"
            error = ",".join(missing_columns)
        else:
            dates = pd.to_datetime(df["date"], errors="coerce").dropna()
            if dates.empty:
                status = "ERROR"
                error_type = "invalid_dates"
                error = "No valid date values"
            else:
                last_price_date = dates.max()
                data_age_days = int((now.normalize() - last_price_date.normalize()).days)

                if row_count < 60:
                    status = "WARN"
                    error_type = "short_history"
                    error = f"Only {row_count} rows"
                elif data_age_days > 7:
                    status = "WARN"
                    error_type = "stale_data"
                    error = f"Last price date is {data_age_days} days old"

        rows.append(
            {
                "ticker": ticker,
                "data_status": status,
                "error_type": error_type,
                "error": error,
                "row_count": row_count,
                "last_price_date": (
                    last_price_date.date().isoformat()
                    if last_price_date is not None
                    else None
                ),
                "data_age_days": data_age_days,
            }
        )

    quality_df = pd.DataFrame(rows)
    errors_df = quality_df[quality_df["data_status"] != "OK"].copy()
    return quality_df, errors_df


def build_candidate_cache() -> tuple[dict, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    started_at = time.monotonic()
    settings = load_settings()
    clock = get_market_clock()
    account = get_account_summary()
    positions = get_positions_summary()

    open_symbols = {position["symbol"] for position in positions}
    tickers_to_load = list(dict.fromkeys([*settings.tickers, *open_symbols]))
    ticker_data = load_price_data_batch(tickers_to_load, period="1y")
    quality_df, errors_df = build_data_quality_rows(tickers_to_load, ticker_data)

    ai_model_bundle = None
    if getattr(settings, "use_ai_score", False):
        try:
            ai_model_bundle = load_ai_score_model()
        except Exception:
            ai_model_bundle = None

    exit_rows = []
    buy_rows = []

    for position in positions:
        ticker = position["symbol"]

        try:
            signal, latest, ai_score, ai_score_status, ai_score_error = get_signal_for_cache(
                ticker,
                ticker_data[ticker],
                settings,
                ai_model_bundle=ai_model_bundle,
            )
            unrealized_plpc = float(position["unrealized_plpc"])

            exit_decision = check_exit_allowed(
                signal=signal,
                unrealized_plpc=unrealized_plpc,
            )

            exit_rows.append(
                {
                    "ticker": ticker,
                    "qty": position["qty"],
                    "market_value": position["market_value"],
                    "unrealized_pl": position["unrealized_pl"],
                    "unrealized_plpc": unrealized_plpc,
                    "signal": signal,
                    "ai_score": ai_score,
                    "ai_score_status": ai_score_status,
                    "ai_score_error": ai_score_error,
                    "should_exit": exit_decision.should_exit,
                    "exit_reason": exit_decision.reason,
                    "close": float(latest["close"]),
                    "rsi": float(latest["rsi"]),
                    "ma_fast": float(latest["ma_fast"]),
                    "ma_slow": float(latest["ma_slow"]),
                }
            )

        except Exception as exc:
            exit_rows.append(
                {
                    "ticker": ticker,
                    "error": str(exc),
                }
            )

    cash = account["cash"]
    positions_count = account["positions_count"]
    dry_run_orders_count = 0
    simulated_daily_notional = get_today_buy_notional()
    recent_buy_symbols = get_recent_buy_symbols(
        int(getattr(settings, "buy_cooldown_days", 0))
    )

    for ticker in settings.tickers:
        try:
            signal, latest, ai_score, ai_score_status, ai_score_error = get_signal_for_cache(
                ticker,
                ticker_data[ticker],
                settings,
                ai_model_bundle=ai_model_bundle,
            )

            if ticker in open_symbols:
                risk_allowed = False
                reason = "already holding position"
                target_amount = 0.0
            else:
                risk = check_buy_allowed(
                    signal=signal,
                    cash=cash,
                    current_positions_count=positions_count,
                )
                risk_allowed = risk.allowed
                reason = risk.reason
                target_amount = risk.target_amount

            if (
                risk_allowed
                and getattr(settings, "use_ai_score", False)
                and (
                    ai_score is None
                    or ai_score < float(settings.ai_score_buy_threshold)
                )
            ):
                risk_allowed = False
                reason = (
                    f"ai score filter blocked "
                    f"(score={ai_score}, threshold={settings.ai_score_buy_threshold})"
                )
                target_amount = 0.0

            order_amount = min(target_amount, settings.max_test_order_amount)

            if risk_allowed:
                safety = apply_buy_safety_limits(
                    ticker=ticker,
                    order_amount=order_amount,
                    submitted_notional_today=simulated_daily_notional,
                    recent_buy_symbols=recent_buy_symbols,
                )
                risk_allowed = safety.allowed
                reason = safety.reason if not safety.allowed else reason
                order_amount = safety.target_amount

            would_submit = False
            execution_label = "NOT_ALLOWED"

            if risk_allowed:
                if dry_run_orders_count >= settings.max_orders_per_run:
                    execution_label = "SKIP_MAX_ORDERS"
                elif not clock.is_open:
                    execution_label = "MARKET_CLOSED"
                    dry_run_orders_count += 1
                else:
                    execution_label = "WOULD_SUBMIT_IF_EXECUTED"
                    would_submit = True
                    dry_run_orders_count += 1
                    simulated_daily_notional += order_amount

            buy_rows.append(
                {
                    "ticker": ticker,
                    "signal": signal,
                    "ai_score": ai_score,
                    "ai_score_status": ai_score_status,
                    "ai_score_error": ai_score_error,
                    "ai_threshold": getattr(settings, "ai_score_buy_threshold", None),
                    "use_ai_score": getattr(settings, "use_ai_score", False),
                    "risk_allowed": risk_allowed,
                    "reason": reason,
                    "target_amount": target_amount,
                    "order_amount": order_amount,
                    "daily_order_used": simulated_daily_notional,
                    "daily_order_limit": getattr(settings, "max_daily_order_amount", None),
                    "buy_cooldown_days": getattr(settings, "buy_cooldown_days", None),
                    "execution_label": execution_label,
                    "would_submit_if_execute": would_submit,
                    "close": float(latest["close"]),
                    "rsi": float(latest["rsi"]),
                    "ma_fast": float(latest["ma_fast"]),
                    "ma_slow": float(latest["ma_slow"]),
                }
            )

        except Exception as exc:
            buy_rows.append(
                {
                    "ticker": ticker,
                    "error": str(exc),
                }
            )

    generated_at = datetime.now().isoformat(timespec="seconds")

    meta = {
        "generated_at": generated_at,
        "market_is_open": clock.is_open,
        "market_timestamp": clock.timestamp,
        "next_open": clock.next_open,
        "next_close": clock.next_close,
        "cash": account["cash"],
        "portfolio_value": account["portfolio_value"],
        "positions_count": account["positions_count"],
        "watchlist_size": len(settings.tickers),
        "max_orders_per_run": settings.max_orders_per_run,
        "max_total_positions": settings.max_total_positions,
        "max_test_order_amount": settings.max_test_order_amount,
        "use_ai_score": getattr(settings, "use_ai_score", False),
        "ai_score_buy_threshold": getattr(settings, "ai_score_buy_threshold", None),
        "max_daily_order_amount": getattr(settings, "max_daily_order_amount", None),
        "buy_cooldown_days": getattr(settings, "buy_cooldown_days", None),
        "today_buy_notional": get_today_buy_notional(),
        "cache_duration_seconds": round(time.monotonic() - started_at, 2),
        "price_data_success_count": int((quality_df["data_status"] == "OK").sum()),
        "price_data_warning_count": int((quality_df["data_status"] == "WARN").sum()),
        "price_data_error_count": int((quality_df["data_status"] == "ERROR").sum()),
    }

    return (
        meta,
        pd.DataFrame(exit_rows),
        pd.DataFrame(buy_rows),
        quality_df,
        errors_df,
    )


def save_candidate_cache() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    meta, exit_df, buy_df, quality_df, errors_df = build_candidate_cache()

    LATEST_META_PATH.write_text(
        json.dumps(meta, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    exit_df.to_csv(LATEST_EXIT_PATH, index=False)
    buy_df.to_csv(LATEST_BUY_PATH, index=False)
    quality_df.to_csv(LATEST_QUALITY_PATH, index=False)
    errors_df.to_csv(LATEST_ERRORS_PATH, index=False)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = CACHE_DIR / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)

    (run_dir / "meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    exit_df.to_csv(run_dir / "exit_candidates.csv", index=False)
    buy_df.to_csv(run_dir / "buy_candidates.csv", index=False)
    quality_df.to_csv(run_dir / "data_quality.csv", index=False)
    errors_df.to_csv(run_dir / "errors.csv", index=False)


def load_latest_candidate_cache() -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    if not LATEST_META_PATH.exists():
        raise FileNotFoundError("No candidate cache found. Run python -m src.generate_candidate_cache")

    meta = json.loads(LATEST_META_PATH.read_text(encoding="utf-8"))

    exit_df = pd.read_csv(LATEST_EXIT_PATH) if LATEST_EXIT_PATH.exists() else pd.DataFrame()
    buy_df = pd.read_csv(LATEST_BUY_PATH) if LATEST_BUY_PATH.exists() else pd.DataFrame()

    return meta, exit_df, buy_df


def load_latest_candidate_cache_full() -> tuple[
    dict,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    meta, exit_df, buy_df = load_latest_candidate_cache()

    quality_df = (
        pd.read_csv(LATEST_QUALITY_PATH)
        if LATEST_QUALITY_PATH.exists()
        else pd.DataFrame()
    )
    errors_df = (
        pd.read_csv(LATEST_ERRORS_PATH)
        if LATEST_ERRORS_PATH.exists()
        else pd.DataFrame()
    )

    return meta, exit_df, buy_df, quality_df, errors_df
