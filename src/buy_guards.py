"""Shared pre-order buy guards for main.py and candidate_cache dry-run parity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from src.correlation_guard import is_correlation_allowed
from src.earnings import is_earnings_window
from src.instrument_meta import check_instrument_buy_allowed
from src.llm_analyst import evaluate_ticker_consensus, llm_skipped_for_run
from src.news_sentiment import get_ticker_sentiment
from src.risk_manager import apply_factor_crowding_limits
from src.sector import is_sector_allowed
from src.sector_rotation import get_ticker_sector_bonus


@dataclass
class BuyGuardResult:
    risk_allowed: bool
    risk_reason: str
    target_amount: float
    llm_is_ok: bool | None = None
    llm_reason: str = ""


def apply_sector_score_bonus(
    ticker: str,
    ai_score: float | None,
    top_sectors: list[str] | None,
) -> float | None:
    if ai_score is None or not top_sectors:
        return ai_score
    bonus = get_ticker_sector_bonus(ticker, top_sectors)
    if bonus > 0:
        return ai_score + bonus
    return ai_score


def apply_shared_buy_guards(
    *,
    ticker: str,
    position: dict | None,
    settings: Any,
    risk_allowed: bool,
    risk_reason: str,
    target_amount: float,
    ai_score: float | None,
    open_symbols: set[str],
    ticker_data: dict[str, pd.DataFrame],
    vix_df: pd.DataFrame | None,
    instrument_ticker: str | None = None,
    macro_risk_active: bool = False,
    macro_risk_reason: str = "",
    margin_leverage_block_active: bool = False,
    margin_leverage_block_reason: str = "",
    llm_cache_only: bool = True,
) -> BuyGuardResult:
    """Mirror main.py new-position buy guards (news → LLM). Skips when position is held."""
    llm_is_ok: bool | None = None
    llm_reason = ""

    if not risk_allowed or position is not None:
        return BuyGuardResult(risk_allowed, risk_reason, target_amount, llm_is_ok, llm_reason)

    if getattr(settings, "news_sentiment_enabled", False):
        try:
            sentiment = get_ticker_sentiment(ticker)
            threshold = float(getattr(settings, "news_sentiment_threshold", -0.30))
            if sentiment is not None and sentiment < threshold:
                return BuyGuardResult(
                    False,
                    f"negative news sentiment (score={sentiment:.2f}, threshold={threshold})",
                    0.0,
                    llm_is_ok,
                    llm_reason,
                )
        except Exception:
            pass

    sector_ok, sector_reason = is_sector_allowed(
        ticker,
        open_symbols,
        max_sector_positions=int(getattr(settings, "max_sector_positions", 2)),
    )
    if not sector_ok:
        return BuyGuardResult(False, sector_reason, 0.0, llm_is_ok, llm_reason)

    inst_ok, inst_reason = check_instrument_buy_allowed(
        instrument_ticker or ticker,
        open_symbols,
        allow_leveraged_etfs=bool(getattr(settings, "allow_leveraged_etfs", False)),
        allow_single_name_leveraged_products=bool(
            getattr(settings, "allow_single_name_leveraged_products", False)
        ),
        leveraged_etf_allowlist=list(
            getattr(settings, "leveraged_etf_allowlist", [])
        ),
        max_leveraged_etf_positions=int(getattr(settings, "max_leveraged_etf_positions", 1)),
        block_leveraged_etfs_vix_above=float(
            getattr(settings, "block_leveraged_etfs_vix_above", 0.0)
        ),
        vix_df=vix_df,
    )
    if not inst_ok:
        return BuyGuardResult(False, inst_reason, 0.0, llm_is_ok, llm_reason)

    if getattr(settings, "correlation_guard_enabled", False):
        corr_ok, corr_reason = is_correlation_allowed(
            ticker,
            open_symbols,
            ticker_data,
            max_corr=float(getattr(settings, "max_correlation_threshold", 0.85)),
            max_portfolio_avg_corr=float(
                getattr(settings, "max_portfolio_avg_correlation_threshold", 0.70)
            ),
            lookback_days=int(getattr(settings, "correlation_lookback_days", 60)),
        )
        if not corr_ok:
            return BuyGuardResult(False, corr_reason, 0.0, llm_is_ok, llm_reason)

    if getattr(settings, "crowding_guard_enabled", False):
        crowding = apply_factor_crowding_limits(
            ticker=ticker,
            open_symbols=open_symbols,
            ticker_data=ticker_data,
        )
        if not crowding.allowed:
            return BuyGuardResult(False, crowding.reason, 0.0, llm_is_ok, llm_reason)

    if getattr(settings, "earnings_filter_enabled", False):
        in_window, earnings_reason = is_earnings_window(
            ticker,
            pd.Timestamp.now(),
            lookback_days=int(getattr(settings, "earnings_lookback_days", 3)),
            lookforward_days=int(getattr(settings, "earnings_lookforward_days", 1)),
        )
        if in_window:
            return BuyGuardResult(
                False,
                f"earnings filter: {earnings_reason}",
                0.0,
                llm_is_ok,
                llm_reason,
            )

    if macro_risk_active:
        return BuyGuardResult(
            False,
            f"macro event risk: {macro_risk_reason}",
            0.0,
            llm_is_ok,
            llm_reason,
        )

    if margin_leverage_block_active:
        return BuyGuardResult(
            False,
            margin_leverage_block_reason,
            0.0,
            llm_is_ok,
            llm_reason,
        )

    if llm_skipped_for_run():
        return BuyGuardResult(risk_allowed, risk_reason, target_amount, None, "")

    llm_is_ok, llm_reason = evaluate_ticker_consensus(
        ticker,
        settings=settings,
        cache_only=llm_cache_only,
    )
    llm_advisory_only = bool(getattr(settings, "llm_advisory_only", True))
    if not llm_is_ok and not llm_advisory_only:
        return BuyGuardResult(
            False,
            f"LLM Reject: {llm_reason}",
            0.0,
            llm_is_ok,
            llm_reason,
        )

    return BuyGuardResult(risk_allowed, risk_reason, target_amount, llm_is_ok, llm_reason)


def execution_label_for_cache(
    *,
    risk_allowed: bool,
    reason: str,
    dry_run_orders_count: int,
    max_orders_per_run: int,
    orders_allowed: bool,
) -> tuple[str, bool]:
    """Return (execution_label, would_submit)."""
    if risk_allowed:
        if dry_run_orders_count >= max_orders_per_run:
            return "SKIP_MAX_ORDERS", False
        if not orders_allowed:
            return "SESSION_CLOSED", False
        return "WOULD_SUBMIT_IF_EXECUTED", True

    lowered = str(reason).lower()
    if "daily order amount limit" in lowered:
        return "SKIP_DAILY_LIMIT", False
    if "buy cooldown" in lowered:
        return "SKIP_COOLDOWN", False
    return "NOT_ALLOWED", False
