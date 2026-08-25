from __future__ import annotations

"""실시간 인기 종목 수집 및 후보 종목 캐시 관리."""

import src.config  # noqa: F401  # load .env before LLM

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import pandas as pd
import requests

from src.broker_adapter import get_broker_adapter
from src.daily_bar_session import drop_incomplete_session_bar
from src.data_loader import load_price_data_batch
from src.conditional_margin_leverage import resolve_conditional_margin_leverage
from src.features import MAX_FEATURE_LOOKBACK
from src.macro_loader import load_macro_data
from src.market_clock import get_market_clock
from src.ml_model import load_ai_score_model, predict_ai_score_from_bundle
from src.buy_guards import (
    apply_sector_score_bonus,
    apply_shared_buy_guards,
)
from src.llm_analyst import llm_cache_only_for_run
from src.macro_events import get_macro_event_risk
from src.margin_leverage_paper_gate import (
    apply_margin_leverage_paper_overrides,
    evaluate_margin_leverage_buy_block,
)
from src.risk_manager import (
    apply_buy_safety_limits,
    apply_effective_leverage_exposure_limits,
    apply_portfolio_exposure_limits,
    check_additional_buy_allowed,
    check_buy_allowed,
    check_exit_allowed,
    get_recent_buy_symbols,
    get_today_buy_notional,
)
from src.position_dust import (
    count_meaningful_positions,
    dust_position_min_usd,
    effective_position,
    meaningful_gross_exposure,
    meaningful_open_symbols,
)
from src.position_sizing import cap_single_order_amount, conviction_adjustments
from src.rank_ai_gate import apply_rank_ai_buy_gate, build_rank_ai_gate_scores
from src.rank_buy_allocator import finalize_rank_buy_cache_execution_labels
from src.rank_leaderboard import LATEST_RANK_PATH, build_rank_leaderboard_frame
from src.sector_rotation import get_sector_leadership
from src.settings import load_settings
from src.strategy import add_indicators, generate_signal

# ── 경로 및 설정 ──────────────────────────────────────────────────────────────
CACHE_DIR = Path("logs/candidate_cache")
LATEST_META_PATH = CACHE_DIR / "latest_meta.json"
UNIVERSE_META_PATH = CACHE_DIR / "universe_meta.json"
UNIVERSE_HISTORY_PATH = CACHE_DIR / "universe_history.jsonl"
LATEST_BUY_PATH = CACHE_DIR / "latest_buy.csv"
LATEST_EXIT_PATH = CACHE_DIR / "latest_exit.csv"
LATEST_QUALITY_PATH = CACHE_DIR / "latest_quality.csv"
LATEST_ERRORS_PATH = CACHE_DIR / "latest_errors.csv"
TRENDING_SOURCE_URL = "https://finance.yahoo.com/markets/stocks/most-active/"
FALLBACK_TRENDING_TICKERS = [
    "TSLA", "NVDA", "AMD", "PLTR", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "AVGO"
]
EXTENDED_FALLBACK_TRENDING_TICKERS = [
    "TSLA", "NVDA", "AMD", "PLTR", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "AVGO",
    "SMH", "ARM", "SNOW", "U", "COIN",
]
AI_PRICE_HISTORY_PERIOD = "2y"
AI_MIN_PRICE_ROWS = MAX_FEATURE_LOOKBACK + 5


# ── 다이내믹 유니버스 (Phase 13) ──────────────────────────────────────────────

def _write_universe_meta(meta: dict) -> None:
    """Persist dynamic-universe snapshot without clobbering full candidate-cache meta."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    UNIVERSE_META_PATH.write_text(json.dumps(meta, indent=2, sort_keys=True), encoding="utf-8")
    history_path = UNIVERSE_META_PATH.with_name(UNIVERSE_HISTORY_PATH.name)
    try:
        with history_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(meta, sort_keys=True) + "\n")
    except OSError as exc:
        print(f"Warning: failed to append dynamic-universe history: {exc}")


def load_dynamic_universe_history(
    path: Path = UNIVERSE_HISTORY_PATH,
) -> dict[pd.Timestamp, list[str]]:
    """Load point-in-time universe snapshots for operational backtests."""
    if not path.is_file():
        return {}
    snapshots: dict[pd.Timestamp, list[str]] = {}
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            payload = json.loads(raw)
            generated_at = pd.Timestamp(payload["generated_at"]).tz_localize(None)
            tickers = payload["tickers"]
            if not isinstance(tickers, list):
                raise ValueError("tickers must be a list")
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError(
                f"Invalid universe history row {line_number} in {path}: {exc}"
            ) from exc
        snapshots[generated_at.normalize()] = [
            str(ticker).strip().upper()
            for ticker in tickers
            if str(ticker).strip()
        ]
    return snapshots


def _build_dynamic_universe_meta(
    static_tickers: List[str],
    trending: List[str],
    final_universe: List[str],
    *,
    requested_limit: int,
    source: str,
    source_url: str = TRENDING_SOURCE_URL,
) -> dict:
    combined_count = len(static_tickers) + len(trending)
    unique_candidates = len(set([*static_tickers, *trending]))
    missing_ticker_count = max(0, combined_count - len(final_universe))
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": source,
        "source_url": source_url,
        "requested_limit": requested_limit,
        "static_count": len(static_tickers),
        "trending_count": len(trending),
        "combined_count": combined_count,
        "unique_candidate_count": unique_candidates,
        "final_count": len(final_universe),
        "missing_ticker_count": missing_ticker_count,
        "tickers": final_universe,
    }


def _fetch_trending_tickers_with_meta(limit: int = 50) -> tuple[List[str], str]:
    """Yahoo Finance의 Most Active 섹션을 스크레이핑하여 인기 종목과 소스 정보를 가져온다."""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(TRENDING_SOURCE_URL, headers=headers, timeout=15)
        tables = pd.read_html(response.text)

        if tables:
            df = tables[0]
            if "Symbol" in df.columns:
                return df["Symbol"].head(limit).tolist(), "yahoo_most_active"

        return EXTENDED_FALLBACK_TRENDING_TICKERS[:limit], "fallback_no_symbol_table"
    except Exception as e:
        print(f"Error fetching trending tickers: {e}")
        return FALLBACK_TRENDING_TICKERS[:limit], "fallback_request_error"


def fetch_trending_tickers(limit: int = 50) -> List[str]:
    """Yahoo Finance의 Most Active 섹션을 스크레이핑하여 인기 종목을 가져온다."""
    tickers, _ = _fetch_trending_tickers_with_meta(limit)
    return tickers


def get_dynamic_universe(static_tickers: List[str], limit: int = 50) -> List[str]:
    """정적 목록과 실시간 인기 종목을 합쳐 최종 유니버스를 생성한다."""
    trending, source = _fetch_trending_tickers_with_meta(limit)

    all_candidates = [
        str(t).strip().upper()
        for t in (list(static_tickers) + list(trending))
        if pd.notna(t)
    ]
    combined = list(set(all_candidates))
    final_universe = [
        t for t in combined
        if t and not t.startswith("^") and "." not in t and len(t) <= 5
    ]

    meta = _build_dynamic_universe_meta(
        static_tickers=[str(t).strip().upper() for t in static_tickers if pd.notna(t)],
        trending=[str(t).strip().upper() for t in trending if pd.notna(t)],
        final_universe=sorted(final_universe),
        requested_limit=limit,
        source=source,
    )
    _write_universe_meta(meta)

    print(
        f"Dynamic Universe: Static({len(static_tickers)}) + Trending({len(trending)}) "
        f"-> Total {len(final_universe)}"
    )
    return final_universe


def _resolve_watchlist_tickers(settings) -> tuple[list[str], dict | None]:
    static_tickers = [str(t).strip().upper() for t in settings.tickers if pd.notna(t)]
    if getattr(settings, "dynamic_universe_enabled", False):
        watchlist = get_dynamic_universe(
            static_tickers,
            limit=int(getattr(settings, "dynamic_count", 50)),
        )
        if UNIVERSE_META_PATH.is_file():
            universe_meta = json.loads(UNIVERSE_META_PATH.read_text(encoding="utf-8"))
        else:
            universe_meta = None
        return watchlist, universe_meta

    return static_tickers, None


# ── 캐시 빌드 ─────────────────────────────────────────────────────────────────

def _offline_account_summary() -> dict:
    return {
        "status": "UNKNOWN",
        "currency": "USD",
        "cash": 0.0,
        "portfolio_value": 0.0,
        "buying_power": 0.0,
        "positions_count": 0,
    }


def _append_context_tickers(tickers: list[str], settings) -> list[str]:
    merged = [str(t).strip().upper() for t in tickers if pd.notna(t)]
    for symbol in ("SPY", "^VIX"):
        if symbol not in merged:
            merged.append(symbol)
    if getattr(settings, "market_regime_filter_enabled", False):
        regime_ticker = str(getattr(settings, "market_regime_ticker", "SPY")).strip().upper()
        if regime_ticker not in merged:
            merged.append(regime_ticker)
    return list(dict.fromkeys(merged))


def _load_cache_ticker_data(tickers: list[str], settings) -> dict[str, pd.DataFrame]:
    tickers_to_load = _append_context_tickers(tickers, settings)
    try:
        ticker_data = load_price_data_batch(tickers_to_load, period=AI_PRICE_HISTORY_PERIOD)
    except Exception as exc:
        print(f"Warning: batch price load failed ({exc}); retrying tickers individually")
        ticker_data = {}
        for ticker in tickers_to_load:
            try:
                ticker_data.update(load_price_data_batch([ticker], period=AI_PRICE_HISTORY_PERIOD))
            except Exception as single_exc:
                print(f"Warning: failed to load {ticker}: {single_exc}")

    spy_df = ticker_data.get("SPY")
    vix_df = ticker_data.get("^VIX")
    if spy_df is None or spy_df.empty or vix_df is None or vix_df.empty:
        missing = []
        if spy_df is None or spy_df.empty:
            missing.append("SPY")
        if vix_df is None or vix_df.empty:
            missing.append("^VIX")
        try:
            context_data = load_price_data_batch(missing, period=AI_PRICE_HISTORY_PERIOD)
            ticker_data.update({k: v for k, v in context_data.items() if v is not None and not v.empty})
        except Exception as exc:
            print(f"Warning: failed to load market context data ({missing}): {exc}")
    return ticker_data


def get_signal_for_cache(
    ticker: str,
    raw_df: pd.DataFrame,
    settings,
    ai_model_bundle=None,
    vix_df=None,
    spy_df=None,
    macro_df=None,
    market_clock=None,
):
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
            f"Price OHLC empty after cleaning for {ticker} "
            f"(rows={len(raw_df)}, usable={len(signal_df)}, ma_slow={settings.ma_slow})"
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
            if len(signal_df) < AI_MIN_PRICE_ROWS:
                raise ValueError(
                    f"Not enough rows to build features: need at least {AI_MIN_PRICE_ROWS}, "
                    f"got {len(signal_df)}"
                )
            ai_score = predict_ai_score_from_bundle(
                signal_df,
                ai_model_bundle,
                vix_df=vix_df,
                spy_df=spy_df,
                macro_df=macro_df,
            )
            ai_score_status = "OK"
        except Exception as exc:
            ai_score_status = "ERROR"
            ai_score_error = str(exc)
            ai_score = None

    return signal, latest, ai_score, ai_score_status, ai_score_error


def build_data_quality_rows(
    requested_tickers: List[str],
    ticker_data: dict[str, pd.DataFrame],
    *,
    min_history_rows: int = 50,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    quality_rows = []
    error_rows = []

    for raw_ticker in requested_tickers:
        ticker = str(raw_ticker).strip().upper()
        frame = ticker_data.get(ticker)

        if frame is None or frame.empty:
            quality_rows.append(
                {"ticker": ticker, "rows": 0, "data_status": "ERROR", "reason": "missing price data"}
            )
            error_rows.append(
                {"ticker": ticker, "data_status": "ERROR", "reason": "missing price data"}
            )
            continue

        row_count = len(frame)
        if row_count < min_history_rows:
            quality_rows.append(
                {
                    "ticker": ticker,
                    "rows": row_count,
                    "data_status": "WARN",
                    "reason": f"short history ({row_count} < {min_history_rows})",
                }
            )
            error_rows.append(
                {
                    "ticker": ticker,
                    "data_status": "WARN",
                    "reason": f"short history ({row_count} < {min_history_rows})",
                }
            )
            continue

        quality_rows.append(
            {"ticker": ticker, "rows": row_count, "data_status": "OK", "reason": "ready"}
        )

    return pd.DataFrame(quality_rows), pd.DataFrame(error_rows)


def build_candidate_cache() -> tuple[dict, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    started_at = time.monotonic()
    settings = load_settings()
    clock = get_market_clock(settings)
    watchlist, universe_meta = _resolve_watchlist_tickers(settings)

    broker = get_broker_adapter(settings.broker_provider)
    try:
        account = broker.get_account()
        positions = broker.get_positions()
    except (ConnectionError, NotImplementedError) as exc:
        print(f"Broker unavailable, building candidate cache with offline defaults: {exc}")
        account = _offline_account_summary()
        positions = []

    dust_min_usd = dust_position_min_usd(settings)
    meaningful_positions_count = count_meaningful_positions(
        positions, min_usd=dust_min_usd
    )

    open_symbols = meaningful_open_symbols(positions, min_usd=dust_min_usd)
    positions_by_symbol = {
        str(position["symbol"]).upper(): position for position in positions
    }
    tickers_to_load = list(dict.fromkeys([*watchlist, *open_symbols]))
    ticker_data = _load_cache_ticker_data(tickers_to_load, settings)
    quality_df, errors_df = build_data_quality_rows(tickers_to_load, ticker_data)

    vix_df = ticker_data.get("^VIX")
    if vix_df is None or (hasattr(vix_df, "empty") and vix_df.empty):
        vix_df = ticker_data.get("VIX")
    spy_df = ticker_data.get("SPY")
    if getattr(settings, "margin_leverage_paper_enabled", False):
        leverage_decision = resolve_conditional_margin_leverage(
            settings,
            spy_df=spy_df,
            vix_df=vix_df,
        )
        settings = apply_margin_leverage_paper_overrides(
            settings,
            effective_leverage_factor=leverage_decision.leverage_factor,
        )
    macro_df = (
        load_macro_data(period=AI_PRICE_HISTORY_PERIOD)
        if getattr(settings, "use_ai_score", False)
        else None
    )
    try:
        rank_ai_gate_scores = build_rank_ai_gate_scores(
            ticker_data,
            settings,
            vix_df=vix_df,
            spy_df=spy_df,
            macro_df=macro_df,
        )
    except Exception as exc:
        if bool(getattr(settings, "rank_ai_buy_gate_fail_closed", True)):
            raise
        print(f"Warning: rank AI buy/add gate disabled for candidate cache: {exc}")
        rank_ai_gate_scores = {}

    ai_model_bundle = None
    if getattr(settings, "use_ai_score", False):
        try:
            ai_model_bundle = load_ai_score_model()
        except Exception:
            ai_model_bundle = None

    exit_rows = []
    buy_rows = []

    for position in positions:
        ticker = str(position["symbol"]).upper()
        frame = ticker_data.get(ticker)
        if frame is None or frame.empty:
            exit_rows.append({"ticker": ticker, "error": "missing price data"})
            continue

        try:
            signal, latest, ai_score, ai_score_status, ai_score_error = get_signal_for_cache(
                ticker,
                frame,
                settings,
                ai_model_bundle=ai_model_bundle,
                vix_df=vix_df,
                spy_df=spy_df,
                macro_df=macro_df,
                market_clock=clock,
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
            exit_rows.append({"ticker": ticker, "error": str(exc)})

    cash = float(account["cash"])
    positions_count = meaningful_positions_count
    current_gross_exposure = meaningful_gross_exposure(
        positions, min_usd=dust_min_usd
    )
    simulated_daily_notional = get_today_buy_notional()
    recent_buy_symbols = get_recent_buy_symbols(
        int(getattr(settings, "buy_cooldown_days", 0))
    )

    top_sectors: list[str] = []
    if getattr(settings, "sector_rotation_enabled", False):
        try:
            top_sectors = get_sector_leadership()
        except Exception as exc:
            print(f"Warning: sector leadership lookup failed: {exc}")

    macro_risk_active = False
    macro_risk_reason = ""
    if getattr(settings, "macro_event_risk_enabled", False):
        macro_risk_active, macro_risk_reason = get_macro_event_risk(
            lookforward_days=int(getattr(settings, "macro_event_lookahead_days", 2)),
            lookback_days=int(getattr(settings, "macro_event_lookback_days", 1)),
        )

    margin_leverage_block_active, margin_leverage_block_reason = evaluate_margin_leverage_buy_block(
        float(getattr(settings, "leverage_factor", 1.0)),
        margin_leverage_paper_enabled=bool(
            getattr(settings, "margin_leverage_paper_enabled", False)
        ),
        margin_leverage_stress_gate_required=bool(
            getattr(settings, "margin_leverage_stress_gate_required", True)
        ),
        conditional_margin_leverage_enabled=bool(
            getattr(settings, "conditional_margin_leverage_enabled", False)
        ),
    )
    for ticker in watchlist:
        frame = ticker_data.get(ticker)
        if frame is None or frame.empty:
            buy_rows.append({"ticker": ticker, "error": "missing price data"})
            continue

        try:
            signal, latest, ai_score, ai_score_status, ai_score_error = get_signal_for_cache(
                ticker,
                frame,
                settings,
                ai_model_bundle=ai_model_bundle,
                vix_df=vix_df,
                spy_df=spy_df,
                macro_df=macro_df,
                market_clock=clock,
            )

            ai_score = apply_sector_score_bonus(ticker, ai_score, top_sectors)
            conviction = conviction_adjustments(settings, ai_score)

            position = effective_position(
                positions_by_symbol.get(ticker),
                min_usd=dust_min_usd,
            )
            if position is not None:
                risk = check_additional_buy_allowed(
                    signal=signal,
                    cash=cash,
                    portfolio_value=float(account["portfolio_value"]),
                    current_position_value=float(position["market_value"]),
                    ticker=ticker,
                    position_mult=conviction.position_mult,
                    cash_buffer_mult=conviction.cash_buffer_mult,
                    settings=settings,
                )
                risk_allowed = risk.allowed
                reason = risk.reason
                target_amount = risk.target_amount
            else:
                risk = check_buy_allowed(
                    signal=signal,
                    cash=cash,
                    current_positions_count=meaningful_positions_count,
                    portfolio_value=float(account["portfolio_value"]),
                    ticker=ticker,
                    position_mult=conviction.position_mult,
                    cash_buffer_mult=conviction.cash_buffer_mult,
                    settings=settings,
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

            guard = apply_shared_buy_guards(
                ticker=ticker,
                position=position,
                settings=settings,
                risk_allowed=risk_allowed,
                risk_reason=reason,
                target_amount=target_amount,
                ai_score=ai_score,
                open_symbols=open_symbols,
                ticker_data=ticker_data,
                vix_df=vix_df,
                macro_risk_active=macro_risk_active,
                macro_risk_reason=macro_risk_reason,
                margin_leverage_block_active=margin_leverage_block_active,
                margin_leverage_block_reason=margin_leverage_block_reason,
                llm_cache_only=llm_cache_only_for_run(execute_orders=False),
            )
            risk_allowed = guard.risk_allowed
            reason = guard.risk_reason
            target_amount = guard.target_amount

            rank_gate = apply_rank_ai_buy_gate(
                ticker=ticker,
                settings=settings,
                risk_allowed=risk_allowed,
                risk_reason=reason,
                target_amount=target_amount,
                scores=rank_ai_gate_scores,
            )
            risk_allowed = rank_gate.risk_allowed
            reason = rank_gate.risk_reason
            target_amount = rank_gate.target_amount

            order_amount = cap_single_order_amount(
                target_amount,
                float(account["portfolio_value"]),
                settings,
            )

            if risk_allowed:
                safety = apply_buy_safety_limits(
                    ticker=ticker,
                    order_amount=order_amount,
                    submitted_notional_today=simulated_daily_notional,
                    recent_buy_symbols=recent_buy_symbols,
                    portfolio_value=float(account["portfolio_value"]),
                    settings=settings,
                )
                risk_allowed = safety.allowed
                reason = safety.reason if not safety.allowed else reason
                order_amount = safety.target_amount

            if risk_allowed:
                exposure = apply_portfolio_exposure_limits(
                    ticker=ticker,
                    order_amount=order_amount,
                    cash=cash,
                    portfolio_value=float(account["portfolio_value"]),
                    buying_power=float(account.get("buying_power", 0.0)),
                    current_gross_exposure=current_gross_exposure,
                    current_position_value=(
                        float(position["market_value"]) if position is not None else 0.0
                    ),
                    cash_buffer_mult=conviction.cash_buffer_mult,
                    settings=settings,
                )
                risk_allowed = exposure.allowed
                reason = exposure.reason if not exposure.allowed else reason
                order_amount = exposure.target_amount

            if risk_allowed:
                leverage_cap = apply_effective_leverage_exposure_limits(
                    ticker=ticker,
                    order_amount=order_amount,
                    portfolio_value=float(account["portfolio_value"]),
                    positions_by_symbol=positions_by_symbol,
                    settings=settings,
                )
                risk_allowed = leverage_cap.allowed
                reason = leverage_cap.reason if not leverage_cap.allowed else reason
                order_amount = leverage_cap.target_amount

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
                    "rank_ai_score": rank_gate.score,
                    "rank_ai_percentile": rank_gate.percentile,
                    "rank_ai_gate_enabled": getattr(settings, "rank_ai_buy_gate_enabled", False),
                    "target_amount": target_amount,
                    "order_amount": order_amount,
                    "daily_order_used": simulated_daily_notional,
                    "daily_order_limit": getattr(settings, "max_daily_order_amount", None),
                    "buy_cooldown_days": getattr(settings, "buy_cooldown_days", None),
                    "is_new_position": position is None,
                    "close": float(latest["close"]),
                    "rsi": float(latest["rsi"]),
                    "ma_fast": float(latest["ma_fast"]),
                    "ma_slow": float(latest["ma_slow"]),
                }
            )
        except Exception as exc:
            buy_rows.append({"ticker": ticker, "error": str(exc)})

    finalize_rank_buy_cache_execution_labels(
        buy_rows,
        settings=settings,
        meaningful_positions_count=meaningful_positions_count,
        orders_allowed=bool(clock.orders_allowed),
    )

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    meta = {
        "generated_at": generated_at,
        "market_is_open": clock.orders_allowed,
        "orders_allowed": clock.orders_allowed,
        "trading_session": clock.session.value,
        "broker_provider": clock.broker_provider,
        "extended_hours_enabled": clock.extended_hours_enabled,
        "regular_session_open": clock.is_open,
        "market_timestamp": clock.timestamp,
        "next_open": clock.next_open,
        "next_close": clock.next_close,
        "cash": account["cash"],
        "portfolio_value": account["portfolio_value"],
        "positions_count": meaningful_positions_count,
        "watchlist_size": len(watchlist),
        "tickers": watchlist,
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
    if universe_meta is not None:
        meta.update(
            {
                "universe_source": universe_meta.get("source"),
                "universe_source_url": universe_meta.get("source_url"),
                "static_count": universe_meta.get("static_count"),
                "trending_count": universe_meta.get("trending_count"),
                "final_count": universe_meta.get("final_count"),
                "missing_ticker_count": universe_meta.get("missing_ticker_count"),
            }
        )
    else:
        meta.setdefault("source", "static_config")
        meta.setdefault("missing_ticker_count", 0)

    buy_df = pd.DataFrame(buy_rows)
    rank_df = build_rank_leaderboard_frame(
        rank_ai_gate_scores,
        open_symbols=open_symbols,
        buy_df=buy_df,
        settings=settings,
    )

    return (
        meta,
        pd.DataFrame(exit_rows),
        buy_df,
        quality_df,
        errors_df,
        rank_df,
    )


def _read_csv_or_empty(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def save_candidate_cache() -> dict:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    meta, exit_df, buy_df, quality_df, errors_df, rank_df = build_candidate_cache()

    if errors_df.empty:
        errors_df = pd.DataFrame(columns=["ticker", "data_status", "reason"])

    LATEST_META_PATH.write_text(
        json.dumps(meta, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    exit_df.to_csv(LATEST_EXIT_PATH, index=False)
    buy_df.to_csv(LATEST_BUY_PATH, index=False)
    rank_df.to_csv(LATEST_RANK_PATH, index=False)
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
    rank_df.to_csv(run_dir / "rank_leaderboard.csv", index=False)
    quality_df.to_csv(run_dir / "data_quality.csv", index=False)
    errors_df.to_csv(run_dir / "errors.csv", index=False)
    return meta


def load_latest_candidate_cache() -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    if not LATEST_META_PATH.exists():
        raise FileNotFoundError(
            "No candidate cache found. Run python -m src.generate_candidate_cache"
        )
    meta = json.loads(LATEST_META_PATH.read_text(encoding="utf-8"))
    meta.setdefault("generated_at", None)
    meta.setdefault("source", "unknown")
    meta.setdefault("missing_ticker_count", 0)
    meta.setdefault("tickers", [])
    meta.setdefault("orders_allowed", meta.get("market_is_open", False))
    exit_df = _read_csv_or_empty(LATEST_EXIT_PATH) if LATEST_EXIT_PATH.exists() else pd.DataFrame()
    buy_df = _read_csv_or_empty(LATEST_BUY_PATH) if LATEST_BUY_PATH.exists() else pd.DataFrame()
    return meta, exit_df, buy_df


def load_latest_candidate_cache_full() -> tuple[dict, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    meta, exit_df, buy_df = load_latest_candidate_cache()
    quality_df = _read_csv_or_empty(LATEST_QUALITY_PATH) if LATEST_QUALITY_PATH.exists() else pd.DataFrame()
    errors_df = _read_csv_or_empty(LATEST_ERRORS_PATH) if LATEST_ERRORS_PATH.exists() else pd.DataFrame()
    return meta, exit_df, buy_df, quality_df, errors_df
