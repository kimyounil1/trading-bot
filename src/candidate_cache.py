import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.settings import load_settings
from src.market_clock import get_market_clock
from src.alpaca_client import get_account_summary, get_positions_summary
from src.data_loader import load_price_data
from src.strategy import add_indicators, generate_signal
from src.risk_manager import check_buy_allowed, check_exit_allowed
from src.ml_model import predict_ai_score


CACHE_DIR = Path("logs/candidate_cache")
LATEST_META_PATH = CACHE_DIR / "latest_meta.json"
LATEST_BUY_PATH = CACHE_DIR / "latest_buy.csv"
LATEST_EXIT_PATH = CACHE_DIR / "latest_exit.csv"


def get_signal_for_cache(ticker: str, settings):
    raw_df = load_price_data(ticker)

    df = add_indicators(
        raw_df,
        ma_fast=settings.ma_fast,
        ma_slow=settings.ma_slow,
    )
    signal = generate_signal(df, rsi_buy_limit=settings.rsi_buy_limit)
    latest = df.iloc[-1]

    ai_score = None
    if getattr(settings, "use_ai_score", False):
        try:
            ai_score = predict_ai_score(raw_df)
        except Exception:
            ai_score = None

    return signal, latest, ai_score


def build_candidate_cache() -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    settings = load_settings()
    clock = get_market_clock()
    account = get_account_summary()
    positions = get_positions_summary()

    open_symbols = {position["symbol"] for position in positions}

    exit_rows = []
    buy_rows = []

    for position in positions:
        ticker = position["symbol"]

        try:
            signal, latest, ai_score = get_signal_for_cache(ticker, settings)
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

    for ticker in settings.tickers:
        try:
            signal, latest, ai_score = get_signal_for_cache(ticker, settings)

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

            buy_rows.append(
                {
                    "ticker": ticker,
                    "signal": signal,
                    "ai_score": ai_score,
                    "ai_threshold": getattr(settings, "ai_score_buy_threshold", None),
                    "use_ai_score": getattr(settings, "use_ai_score", False),
                    "risk_allowed": risk_allowed,
                    "reason": reason,
                    "target_amount": target_amount,
                    "order_amount": order_amount,
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
    }

    return meta, pd.DataFrame(exit_rows), pd.DataFrame(buy_rows)


def save_candidate_cache() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    meta, exit_df, buy_df = build_candidate_cache()

    LATEST_META_PATH.write_text(
        json.dumps(meta, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    exit_df.to_csv(LATEST_EXIT_PATH, index=False)
    buy_df.to_csv(LATEST_BUY_PATH, index=False)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = CACHE_DIR / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)

    (run_dir / "meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    exit_df.to_csv(run_dir / "exit_candidates.csv", index=False)
    buy_df.to_csv(run_dir / "buy_candidates.csv", index=False)


def load_latest_candidate_cache() -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    if not LATEST_META_PATH.exists():
        raise FileNotFoundError("No candidate cache found. Run python -m src.generate_candidate_cache")

    meta = json.loads(LATEST_META_PATH.read_text(encoding="utf-8"))

    exit_df = pd.read_csv(LATEST_EXIT_PATH) if LATEST_EXIT_PATH.exists() else pd.DataFrame()
    buy_df = pd.read_csv(LATEST_BUY_PATH) if LATEST_BUY_PATH.exists() else pd.DataFrame()

    return meta, exit_df, buy_df
