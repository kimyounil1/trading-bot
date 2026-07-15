from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from types import SimpleNamespace
from typing import Any
import warnings

import pandas as pd

from src.strategy import add_indicators, build_market_regime_frame
from src.features import FEATURE_COLUMNS, build_inference_features
from src.ml_model import load_ai_score_model
from src.portfolio_optimizer import compute_candidate_weights
from src.llm_analyst import evaluate_ticker_consensus
from src.news_sentiment import get_ticker_sentiment
from src.risk_manager import apply_factor_crowding_limits
from src.correlation_guard import is_correlation_allowed
from src.partial_exit_policy import (
    compute_partial_exit_thresholds,
    evaluate_partial_exit,
)
from src.regime_stop_policy import RegimeStopProfile, resolve_regime_stop_params
from src.rank_ai_gate import (
    build_rank_ai_gate_score_history,
    rank_ai_gate_effective_cutoff,
)
from src.rank_buy_allocator import (
    attach_rank_gate_scores_to_day_df,
    max_rank_new_buys_per_run,
    rank_buy_top_k_enabled,
    truncate_ticker_frames_asof,
)
from src.sector import is_sector_allowed
from src.instrument_meta import (
    adjust_position_cap_for_instrument,
    count_leveraged_etf_positions,
    get_instrument,
    preferred_leveraged_long_product,
)


@dataclass
class PortfolioBacktestResult:
    initial_cash: float
    final_equity: float
    total_return: float
    max_drawdown: float
    trades: int
    win_rate: float
    benchmark_return: float
    sharpe_ratio: float = 0.0


PORTFOLIO_ENTRY_COLUMNS: tuple[str, ...] = (
    "market_date",
    "signal_ticker",
    "execution_ticker",
    "leveraged",
    "quality_notional_multiplier",
    "quality_allow_leveraged",
    "planned_notional",
    "planned_notional_pct",
    "rank_ai_score",
    "rank_ai_percentile",
    "sleeve_id",
)


def _prepare_ticker_frame(
    ticker: str,
    df: pd.DataFrame,
    ma_fast: int = 20,
    ma_slow: int = 50,
    rsi_buy_limit: float = 70,
    use_ai_score: bool = False,
    ai_score_buy_threshold: float = 0.55,
    ai_model_bundle=None,
    ai_score_frame: pd.DataFrame | None = None,
    relative_strength_lookback_days: int = 20,
    volume_filter_enabled: bool = False,
    volume_lookback_days: int = 20,
    min_volume_ratio: float = 1.0,
    volatility_filter_enabled: bool = False,
    volatility_lookback_days: int = 20,
    max_volatility: float = 0.04,
) -> pd.DataFrame:
    raw_df = df.copy()
    df = add_indicators(df, ma_fast=ma_fast, ma_slow=ma_slow).copy()
    df = df.sort_values("date").reset_index(drop=True)

    df["ticker"] = ticker
    df["ai_score"] = float("nan")
    df["relative_return"] = df["close"].pct_change(relative_strength_lookback_days)
    df["volume_ratio"] = df["volume"] / df["volume"].rolling(volume_lookback_days).mean()
    df["volatility"] = df["close"].pct_change().rolling(volatility_lookback_days).std()
    df["volatility_20d"] = df["volatility"]

    if use_ai_score and ai_score_frame is not None:
        score_df = ai_score_frame[["date", "ai_score"]].copy()
        score_df["date"] = pd.to_datetime(score_df["date"])
        df["date"] = pd.to_datetime(df["date"])
        df = df.merge(score_df, on="date", how="left", suffixes=("", "_model"))
        if "ai_score_model" in df.columns:
            df["ai_score"] = df["ai_score_model"]
            df = df.drop(columns=["ai_score_model"])
    elif use_ai_score:
        try:
            if ai_model_bundle is None:
                raise ValueError("AI score model was not loaded")
            score_df = build_ai_score_frame(raw_df, ai_model_bundle, vix_df=None, spy_df=None)
            score_df["date"] = pd.to_datetime(score_df["date"])
            df["date"] = pd.to_datetime(df["date"])
            df = df.merge(score_df, on="date", how="left", suffixes=("", "_model"))
            if "ai_score_model" in df.columns:
                df["ai_score"] = df["ai_score_model"]
                df = df.drop(columns=["ai_score_model"])

        except Exception:
            df["ai_score"] = float("nan")

    base_buy_signal = (df["ma_fast"] > df["ma_slow"]) & (df["rsi"] < rsi_buy_limit)

    if use_ai_score:
        df["buy_signal"] = base_buy_signal & (
            pd.to_numeric(df["ai_score"], errors="coerce") >= ai_score_buy_threshold
        )
    else:
        df["buy_signal"] = base_buy_signal

    if volume_filter_enabled:
        df["buy_signal"] = df["buy_signal"] & (
            pd.to_numeric(df["volume_ratio"], errors="coerce") >= min_volume_ratio
        )

    if volatility_filter_enabled:
        df["buy_signal"] = df["buy_signal"] & (
            pd.to_numeric(df["volatility"], errors="coerce") <= max_volatility
        )

    df["sell_signal"] = df["ma_fast"] < df["ma_slow"]

    return df[
        [
            "date",
            "ticker",
            "close",
            "ma20",
            "ma50",
            "ma_fast",
            "ma_slow",
            "rsi",
            "ai_score",
            "relative_return",
            "volume_ratio",
            "volatility",
            "volatility_20d",
            "buy_signal",
            "sell_signal",
        ]
    ]


def build_ai_score_frame(
    df: pd.DataFrame,
    ai_model_bundle,
    vix_df: pd.DataFrame | None = None,
    spy_df: pd.DataFrame | None = None,
    macro_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    feature_df = build_inference_features(
        df,
        prediction_horizon=ai_model_bundle.prediction_horizon,
        target_return_threshold=ai_model_bundle.target_return_threshold,
        vix_df=vix_df,
        spy_df=spy_df,
        macro_df=macro_df,
    )
    scores = ai_model_bundle.predict_proba(
        df, vix_df=vix_df, spy_df=spy_df, macro_df=macro_df
    )
    if len(scores) != len(feature_df):
        raise ValueError(
            "AI inference score/date length mismatch: "
            f"scores={len(scores)}, features={len(feature_df)}"
        )
    score_df = feature_df[["date"]].copy()
    score_df["ai_score"] = scores.to_numpy()
    return score_df[["date", "ai_score"]]


def build_ai_score_frames(
    ticker_data: dict[str, pd.DataFrame],
    ai_model_bundle=None,
    vix_df: pd.DataFrame | None = None,
    spy_df: pd.DataFrame | None = None,
    macro_df: pd.DataFrame | None = None,
) -> dict[str, pd.DataFrame]:
    if ai_model_bundle is None:
        ai_model_bundle = load_ai_score_model()

    score_frames = {}
    skipped: dict[str, str] = {}
    for ticker, df in ticker_data.items():
        try:
            score_frames[ticker] = build_ai_score_frame(
                df, ai_model_bundle, vix_df=vix_df, spy_df=spy_df, macro_df=macro_df
            )
        except ValueError as exc:
            skipped[str(ticker).upper()] = str(exc)
    if not score_frames:
        detail = "; ".join(f"{ticker}: {reason}" for ticker, reason in skipped.items())
        raise ValueError(f"No ticker produced AI score history. {detail}")
    if skipped:
        warnings.warn(
            "Skipped AI score history for insufficient/invalid ticker data: "
            + ", ".join(sorted(skipped)),
            RuntimeWarning,
            stacklevel=2,
        )
    return score_frames


def _apply_market_regime_filter(
    market_df: pd.DataFrame,
    benchmark_df: pd.DataFrame,
    market_regime_ma_fast: int,
    market_regime_ma_slow: int,
) -> pd.DataFrame:
    regime_df = build_market_regime_frame(
        benchmark_df,
        ma_fast=market_regime_ma_fast,
        ma_slow=market_regime_ma_slow,
    )
    filtered_df = market_df.merge(regime_df, on="date", how="left")
    filtered_df["market_regime_bullish"] = filtered_df["market_regime_bullish"] == True
    filtered_df["buy_signal"] = filtered_df["buy_signal"] & filtered_df["market_regime_bullish"]
    return filtered_df


def _price_series_from_ticker_df(df: pd.DataFrame) -> pd.Series:
    tmp = df.copy()
    tmp["date"] = pd.to_datetime(tmp["date"])
    price_col = "adj_close" if "adj_close" in tmp.columns else "close"
    if price_col not in tmp.columns:
        raise ValueError("Ticker data must contain close or adj_close")
    return pd.to_numeric(tmp.set_index("date")[price_col], errors="coerce")


def _build_equal_weight_benchmark_values(
    equity_dates: pd.Series,
    ticker_data: dict[str, pd.DataFrame],
    initial_cash: float,
) -> list[float]:
    """Equal-weight buy-and-hold using raw prices (not filtered market_df)."""
    if not ticker_data:
        raise ValueError("ticker_data is empty")

    price_by_ticker = {
        ticker: _price_series_from_ticker_df(df) for ticker, df in ticker_data.items()
    }
    dates = pd.to_datetime(equity_dates)
    start_date = None
    tickers = list(price_by_ticker.keys())
    for date in dates:
        prices = {
            ticker: price_by_ticker[ticker].get(date)
            for ticker in tickers
        }
        if all(price is not None and pd.notna(price) and float(price) > 0 for price in prices.values()):
            start_date = date
            break
    if start_date is None:
        raise ValueError("No date with valid closes for all tickers to seed equal-weight benchmark")

    per_ticker_cash = initial_cash / len(tickers)
    shares = {
        ticker: per_ticker_cash / float(price_by_ticker[ticker].loc[start_date])
        for ticker in tickers
    }
    aligned_prices = {
        ticker: series.reindex(dates).ffill()
        for ticker, series in price_by_ticker.items()
    }

    values: list[float] = []
    for date in dates:
        value = 0.0
        for ticker, qty in shares.items():
            price = aligned_prices[ticker].get(date)
            if price is not None and pd.notna(price):
                value += qty * float(price)
        values.append(value)
    return values


def _build_benchmark_relative_return_frame(
    benchmark_df: pd.DataFrame,
    lookback_days: int,
) -> pd.DataFrame:
    if benchmark_df.empty:
        raise ValueError("No benchmark price data available for relative strength filter")
    if "date" not in benchmark_df.columns or "close" not in benchmark_df.columns:
        raise ValueError("Benchmark data must contain date and close columns")

    frame = benchmark_df[["date", "close"]].copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame = frame.sort_values("date").reset_index(drop=True)
    frame["benchmark_relative_return"] = frame["close"].pct_change(
        lookback_days,
        fill_method=None,
    )
    return frame[["date", "benchmark_relative_return"]]


def _build_price_lookup(
    ticker_frames: dict[str, pd.DataFrame] | None,
) -> dict[str, dict[pd.Timestamp, float]]:
    lookup: dict[str, dict[pd.Timestamp, float]] = {}
    for ticker, frame in (ticker_frames or {}).items():
        if frame is None or frame.empty or "date" not in frame.columns:
            continue
        close_col = "adj_close" if "adj_close" in frame.columns else "close"
        if close_col not in frame.columns:
            continue
        work = frame[["date", close_col]].copy()
        work["date"] = pd.to_datetime(work["date"], errors="coerce")
        work[close_col] = pd.to_numeric(work[close_col], errors="coerce")
        work = work.dropna(subset=["date", close_col])
        lookup[str(ticker).upper()] = {
            pd.Timestamp(date): float(close)
            for date, close in zip(work["date"], work[close_col])
            if float(close) > 0
        }
    return lookup


def _active_universe_for_date(
    historical_universe_by_date: dict[Any, list[str]] | None,
    current_date: pd.Timestamp,
    fallback_universe: set[str] | None = None,
) -> set[str] | None:
    if not historical_universe_by_date:
        return None
    normalized = {
        pd.Timestamp(date).normalize(): {
            str(ticker).strip().upper()
            for ticker in tickers
            if str(ticker).strip()
        }
        for date, tickers in historical_universe_by_date.items()
    }
    eligible_dates = [date for date in normalized if date <= current_date.normalize()]
    if not eligible_dates:
        return fallback_universe
    return normalized[max(eligible_dates)]


def _apply_relative_strength_filter(
    market_df: pd.DataFrame,
    benchmark_df: pd.DataFrame,
    lookback_days: int,
    min_excess_return: float,
    threshold_by_date: dict[pd.Timestamp, float] | None = None,
) -> pd.DataFrame:
    benchmark_returns = _build_benchmark_relative_return_frame(
        benchmark_df,
        lookback_days=lookback_days,
    )
    filtered_df = market_df.merge(benchmark_returns, on="date", how="left")
    filtered_df["relative_strength_excess_return"] = (
        pd.to_numeric(filtered_df["relative_return"], errors="coerce")
        - pd.to_numeric(filtered_df["benchmark_relative_return"], errors="coerce")
    )
    threshold = pd.Series(min_excess_return, index=filtered_df.index, dtype=float)
    if threshold_by_date:
        normalized_dates = filtered_df["date"].dt.normalize()
        mapped = normalized_dates.map(threshold_by_date)
        threshold = pd.to_numeric(mapped, errors="coerce").fillna(min_excess_return)
    filtered_df["relative_strength_pass"] = (
        filtered_df["relative_strength_excess_return"] >= threshold
    )
    filtered_df["buy_signal"] = filtered_df["buy_signal"] & filtered_df["relative_strength_pass"]
    return filtered_df


def _sort_tournament_alpha_candidates(
    buy_candidates: pd.DataFrame,
    *,
    rank_weight: float = 0.65,
) -> pd.DataFrame:
    """Match the live tournament selector's Rank/AI alpha ordering."""
    if buy_candidates.empty:
        return buy_candidates
    ranked = buy_candidates.copy()
    ai_weight = 1.0 - rank_weight
    ranked["tournament_alpha_score"] = (
        rank_weight
        * pd.to_numeric(
            ranked["rank_ai_percentile"],
            errors="coerce",
        ).fillna(0.0)
        + ai_weight
        * pd.to_numeric(
            ranked["ai_score"],
            errors="coerce",
        ).fillna(0.5)
    )
    return ranked.sort_values(
        ["tournament_alpha_score", "ticker"],
        ascending=[False, True],
    )


def run_portfolio_backtest(
    ticker_data: dict[str, pd.DataFrame],
    benchmark_df: pd.DataFrame | None = None,
    relative_strength_benchmark_df: pd.DataFrame | None = None,
    initial_cash: float = 10000.0,
    max_positions: int = 3,
    target_position_pct: float = 0.30,
    transaction_cost_pct: float = 0.001,
    ma_fast: int = 20,
    ma_slow: int = 50,
    rsi_buy_limit: float = 70,
    use_ai_score: bool = False,
    ai_score_buy_threshold: float = 0.55,
    market_regime_filter_enabled: bool = False,
    market_regime_ma_fast: int = 50,
    market_regime_ma_slow: int = 200,
    stop_loss_pct: float = 0.0,
    take_profit_pct: float = 0.0,
    trailing_stop_pct: float = 0.0,
    max_holding_days: int = 0,
    rank_trend_weight: float = 1.0,
    rank_ai_weight: float = 0.0,
    rank_momentum_weight: float = 0.0,
    rank_volatility_weight: float = 0.0,
    relative_strength_filter_enabled: bool = False,
    relative_strength_lookback_days: int = 20,
    relative_strength_min_excess_return: float = 0.0,
    volume_filter_enabled: bool = False,
    volume_lookback_days: int = 20,
    min_volume_ratio: float = 1.0,
    volatility_filter_enabled: bool = False,
    volatility_lookback_days: int = 20,
    max_volatility: float = 0.04,
    ai_score_frames: dict[str, pd.DataFrame] | None = None,
    allocation_method: str = "equal_weight",
    mvo_lookback_days: int = 60,
    mvo_min_weight: float = 0.05,
    mvo_max_weight: float = 0.40,
    ai_exit_enabled: bool = False,
    ai_exit_threshold: float = 0.30,
    ai_exit_dynamic_enabled: bool = False,
    ai_exit_vix_low: float = 15.0,
    ai_exit_vix_high: float = 25.0,
    ai_exit_threshold_bull: float = 0.55,
    ai_exit_threshold_bear: float = 0.28,
    vix_df: pd.DataFrame | None = None,
    macro_df: pd.DataFrame | None = None,
    evaluation_start_date: str | pd.Timestamp | None = None,
    evaluation_end_date: str | pd.Timestamp | None = None,
    crowding_guard_enabled: bool = False,
    max_sector_positions: int | None = None,
    regime_adaptive_stop_enabled: bool = False,
    regime_stop_spy_df: pd.DataFrame | None = None,
    regime_stop_profile: RegimeStopProfile | None = None,
    llm_filter_enabled: bool = False,
    llm_cache_only: bool = True,
    news_sentiment_filter_enabled: bool = False,
    news_sentiment_threshold: float = -0.30,
    correlation_guard_enabled: bool = False,
    max_correlation_threshold: float = 0.85,
    max_portfolio_avg_correlation_threshold: float = 0.70,
    correlation_lookback_days: int = 60,
    operational_settings: Any | None = None,
    rank_ai_buy_gate_enabled: bool = False,
    rank_ai_buy_top_k_enabled: bool = True,
    rank_ai_primary_selector_enabled: bool = False,
    tournament_alpha_enabled: bool = False,
    tournament_alpha_rank_weight: float = 0.65,
    max_orders_per_run: int = 6,
    rank_position_sizing_enabled: bool = False,
    rank_position_sizing_min_mult: float = 0.6,
    rank_position_sizing_max_mult: float = 1.25,
    allow_leveraged_etfs: bool = False,
    leveraged_etf_allowlist: list[str] | None = None,
    max_leveraged_etf_positions: int = 1,
    max_effective_leverage_exposure_pct: float = 1.25,
    block_leveraged_etfs_vix_above: float = 0.0,
    prefer_leveraged_products: bool = False,
    leveraged_product_data: dict[str, pd.DataFrame] | None = None,
    leveraged_product_routes: dict[str, str] | None = None,
    historical_universe_by_date: dict[Any, list[str]] | None = None,
    base_universe: set[str] | list[str] | None = None,
    benchmark_universe: set[str] | list[str] | None = None,
    rank_ai_score_history: dict[Any, dict[str, Any]] | None = None,
    entry_parameter_overrides_by_date: dict[Any, dict[str, Any]] | None = None,
    entry_risk_overrides_by_date: dict[
        Any, dict[str, dict[str, Any]]
    ] | None = None,
    exit_parameter_overrides_by_date: dict[Any, dict[str, Any]] | None = None,
    take_profit_partial_pct: float = 0.0,
    partial_exit_ratio: float = 0.5,
    minimum_order_notional: float = 0.0,
    fractionable_symbols: set[str] | None = None,
    cash_reserve_pct: float = 0.0,
    leverage_factor: float = 1.0,
    annual_margin_interest_rate: float = 0.0,
) -> tuple[PortfolioBacktestResult, pd.DataFrame, pd.DataFrame]:
    if relative_strength_lookback_days <= 0:
        raise ValueError("relative_strength_lookback_days must be positive")
    if volume_lookback_days <= 0:
        raise ValueError("volume_lookback_days must be positive")
    if min_volume_ratio < 0:
        raise ValueError("min_volume_ratio must be non-negative")
    if volatility_lookback_days <= 0:
        raise ValueError("volatility_lookback_days must be positive")
    if max_volatility < 0:
        raise ValueError("max_volatility must be non-negative")
    if not 0 <= stop_loss_pct < 1:
        raise ValueError("stop_loss_pct must be between 0 and 1")
    if take_profit_pct < 0:
        raise ValueError("take_profit_pct must be non-negative")
    if not 0 <= trailing_stop_pct < 1:
        raise ValueError("trailing_stop_pct must be between 0 and 1")
    if max_holding_days < 0:
        raise ValueError("max_holding_days must be non-negative")
    if max_leveraged_etf_positions <= 0:
        raise ValueError("max_leveraged_etf_positions must be positive")
    if max_effective_leverage_exposure_pct <= 0:
        raise ValueError("max_effective_leverage_exposure_pct must be positive")
    if block_leveraged_etfs_vix_above < 0:
        raise ValueError("block_leveraged_etfs_vix_above must be non-negative")
    if not 0 <= tournament_alpha_rank_weight <= 1:
        raise ValueError("tournament_alpha_rank_weight must be between 0 and 1")
    if correlation_lookback_days <= 0:
        raise ValueError("correlation_lookback_days must be positive")
    if take_profit_partial_pct < 0:
        raise ValueError("take_profit_partial_pct must be non-negative")
    if not 0 < partial_exit_ratio <= 1:
        raise ValueError("partial_exit_ratio must be between 0 and 1")
    if minimum_order_notional < 0:
        raise ValueError("minimum_order_notional must be non-negative")
    if not 0 <= cash_reserve_pct < 1:
        raise ValueError("cash_reserve_pct must be between 0 and 1")
    if leverage_factor < 1.0:
        raise ValueError("leverage_factor must be at least 1.0")
    if annual_margin_interest_rate < 0:
        raise ValueError("annual_margin_interest_rate must be non-negative")

    ai_model_bundle = None
    if use_ai_score:
        try:
            ai_model_bundle = load_ai_score_model()
        except Exception:
            ai_model_bundle = None

    # SPY data for relative return feature
    spy_df = ticker_data.get("SPY")

    # Pre-compute AI score frames with full context (VIX + macro)
    _ai_score_frames = ai_score_frames
    if use_ai_score and ai_model_bundle is not None and _ai_score_frames is None:
        _ai_score_frames = build_ai_score_frames(
            ticker_data,
            ai_model_bundle=ai_model_bundle,
            vix_df=vix_df,
            spy_df=spy_df,
            macro_df=macro_df,
        )

    normalized_entry_overrides = {
        pd.Timestamp(date).normalize(): dict(values)
        for date, values in (entry_parameter_overrides_by_date or {}).items()
    }
    normalized_exit_overrides = {
        pd.Timestamp(date).normalize(): dict(values)
        for date, values in (exit_parameter_overrides_by_date or {}).items()
    }
    normalized_entry_risk_overrides: dict[
        pd.Timestamp, dict[str, dict[str, Any]]
    ] = {}
    for date, ticker_overrides in (entry_risk_overrides_by_date or {}).items():
        normalized_tickers: dict[str, dict[str, Any]] = {}
        for ticker, values in ticker_overrides.items():
            override = dict(values)
            multiplier = float(override.get("notional_multiplier", 1.0))
            if not 0.0 <= multiplier <= 1.0:
                raise ValueError(
                    "entry risk notional_multiplier must be between 0 and 1"
                )
            normalized_tickers[str(ticker).strip().upper()] = {
                "notional_multiplier": multiplier,
                "allow_leveraged": bool(override.get("allow_leveraged", True)),
            }
        normalized_entry_risk_overrides[
            pd.Timestamp(date).normalize()
        ] = normalized_tickers
    entry_defaults = {
        "ma_fast": ma_fast,
        "ma_slow": ma_slow,
        "rsi_buy_limit": rsi_buy_limit,
        "ai_score_buy_threshold": ai_score_buy_threshold,
    }
    entry_variants: dict[tuple[Any, ...], int] = {}

    def entry_variant(values: dict[str, Any]) -> tuple[Any, ...]:
        merged = {**entry_defaults, **values}
        return tuple(merged[name] for name in entry_defaults)

    base_variant = entry_variant({})
    entry_variants[base_variant] = 0
    date_variant: dict[pd.Timestamp, int] = {}
    for date, values in normalized_entry_overrides.items():
        variant = entry_variant(values)
        variant_id = entry_variants.setdefault(variant, len(entry_variants))
        date_variant[date] = variant_id

    prepared_frames: list[pd.DataFrame] = []
    for variant, variant_id in entry_variants.items():
        variant_params = dict(zip(entry_defaults, variant))
        for ticker, df in ticker_data.items():
            prepared = _prepare_ticker_frame(
                ticker,
                df,
                ma_fast=int(variant_params["ma_fast"]),
                ma_slow=int(variant_params["ma_slow"]),
                rsi_buy_limit=float(variant_params["rsi_buy_limit"]),
                use_ai_score=use_ai_score,
                ai_score_buy_threshold=float(
                    variant_params["ai_score_buy_threshold"]
                ),
                ai_model_bundle=ai_model_bundle,
                ai_score_frame=(
                    _ai_score_frames.get(ticker) if _ai_score_frames else None
                ),
                relative_strength_lookback_days=relative_strength_lookback_days,
                volume_filter_enabled=volume_filter_enabled,
                volume_lookback_days=volume_lookback_days,
                min_volume_ratio=min_volume_ratio,
                volatility_filter_enabled=volatility_filter_enabled,
                volatility_lookback_days=volatility_lookback_days,
                max_volatility=max_volatility,
            )
            prepared["_entry_variant"] = variant_id
            prepared_frames.append(prepared)

    market_df = pd.concat(prepared_frames, ignore_index=True)
    market_df["date"] = pd.to_datetime(market_df["date"])
    desired_variant = market_df["date"].dt.normalize().map(date_variant).fillna(0)
    market_df = market_df[market_df["_entry_variant"] == desired_variant].drop(
        columns=["_entry_variant"]
    )
    market_df = market_df.sort_values(["date", "ticker"]).reset_index(drop=True)
    if market_regime_filter_enabled:
        if benchmark_df is None:
            raise ValueError("benchmark_df is required when market_regime_filter_enabled=True")
        market_df = _apply_market_regime_filter(
            market_df,
            benchmark_df,
            market_regime_ma_fast=market_regime_ma_fast,
            market_regime_ma_slow=market_regime_ma_slow,
        )
    if relative_strength_filter_enabled:
        benchmark_for_relative_strength = relative_strength_benchmark_df
        if benchmark_for_relative_strength is None:
            benchmark_for_relative_strength = benchmark_df
        if benchmark_for_relative_strength is None:
            raise ValueError(
                "relative_strength_benchmark_df is required when "
                "relative_strength_filter_enabled=True"
            )
        market_df = _apply_relative_strength_filter(
            market_df,
            benchmark_for_relative_strength,
            lookback_days=relative_strength_lookback_days,
            min_excess_return=relative_strength_min_excess_return,
            threshold_by_date={
                date: float(
                    values.get(
                        "relative_strength_min_excess_return",
                        relative_strength_min_excess_return,
                    )
                )
                for date, values in normalized_entry_overrides.items()
            },
        )

    all_dates = sorted(market_df["date"].unique())
    trading_dates = all_dates
    if evaluation_start_date is not None:
        start_ts = pd.Timestamp(evaluation_start_date)
        trading_dates = [date for date in trading_dates if pd.Timestamp(date) >= start_ts]
    if evaluation_end_date is not None:
        end_ts = pd.Timestamp(evaluation_end_date)
        trading_dates = [date for date in trading_dates if pd.Timestamp(date) <= end_ts]
    if not trading_dates:
        raise ValueError("No dates available inside the requested evaluation window")

    # VIX lookup index for dynamic AI exit threshold
    _vix_by_date: dict = {}
    if (
        ai_exit_dynamic_enabled
        or (allow_leveraged_etfs and block_leveraged_etfs_vix_above > 0)
    ) and vix_df is not None and not vix_df.empty:
        _vix_tmp = vix_df.copy()
        _vix_tmp["date"] = pd.to_datetime(_vix_tmp["date"])
        _vix_tmp = _vix_tmp.sort_values("date")
        close_col = "adj_close" if "adj_close" in _vix_tmp.columns else "close"
        _vix_by_date = dict(zip(_vix_tmp["date"], _vix_tmp[close_col]))

    product_price_lookup = _build_price_lookup(leveraged_product_data)
    route_map = {
        str(source).strip().upper(): str(product).strip().upper()
        for source, product in (leveraged_product_routes or {}).items()
        if str(source).strip() and str(product).strip()
    }
    if prefer_leveraged_products and not route_map:
        route_map = {
            str(source).upper(): product
            for source in ticker_data
            if (
                product := preferred_leveraged_long_product(
                    source,
                    allowlist=leveraged_etf_allowlist,
                )
            )
        }
    fractionable = (
        {str(symbol).strip().upper() for symbol in fractionable_symbols}
        if fractionable_symbols is not None
        else None
    )
    _rank_score_history = rank_ai_score_history
    if (
        rank_ai_buy_gate_enabled
        and operational_settings is not None
        and _rank_score_history is None
    ):
        try:
            _rank_score_history = build_rank_ai_gate_score_history(
                ticker_data,
                operational_settings,
                vix_df=vix_df,
                spy_df=spy_df,
                macro_df=macro_df,
                historical_universe_by_date=historical_universe_by_date,
                base_universe=base_universe,
            )
        except Exception:
            _rank_score_history = {}
    normalized_rank_history = {
        pd.Timestamp(date): scores
        for date, scores in (_rank_score_history or {}).items()
    }
    normalized_base_universe = (
        {str(ticker).strip().upper() for ticker in base_universe}
        if base_universe is not None
        else None
    )

    cash = initial_cash
    positions: dict[str, dict] = {}
    cumulative_margin_interest = 0.0
    previous_trading_date: pd.Timestamp | None = None

    trades: list[dict] = []
    entry_events: list[dict] = []
    equity_rows: list[dict] = []

    for current_date in trading_dates:
        current_ts = pd.Timestamp(current_date)
        day_entry_params = normalized_entry_overrides.get(current_ts.normalize(), {})
        day_entry_risk = normalized_entry_risk_overrides.get(
            current_ts.normalize(), {}
        )
        day_exit_params = normalized_exit_overrides.get(current_ts.normalize(), {})
        day_max_positions = int(day_entry_params.get("max_positions", max_positions))
        day_target_position_pct = float(
            day_entry_params.get("target_position_pct", target_position_pct)
        )
        day_allocation_method = str(
            day_entry_params.get("allocation_method", allocation_method)
        )
        day_tournament_alpha_rank_weight = float(
            day_entry_params.get(
                "tournament_alpha_rank_weight",
                tournament_alpha_rank_weight,
            )
        )
        day_stop_loss_pct = float(
            day_exit_params.get("stop_loss_pct", stop_loss_pct)
        )
        day_take_profit_pct = float(
            day_exit_params.get("take_profit_pct", take_profit_pct)
        )
        day_trailing_stop_pct = float(
            day_exit_params.get("trailing_stop_pct", trailing_stop_pct)
        )
        day_max_holding_days = int(
            day_exit_params.get("max_holding_days", max_holding_days)
        )
        day_ops_settings = operational_settings
        if operational_settings is not None and (
            day_max_positions != max_positions
            or day_target_position_pct != target_position_pct
        ):
            day_ops_settings = SimpleNamespace(
                **{
                    **vars(operational_settings),
                    "max_total_positions": day_max_positions,
                    "max_position_pct": day_target_position_pct,
                }
            )
        if previous_trading_date is not None and cash < 0:
            calendar_days = max((current_ts - previous_trading_date).days, 1)
            margin_interest = (
                -cash
                * annual_margin_interest_rate
                * calendar_days
                / 360.0
            )
            cash -= margin_interest
            cumulative_margin_interest += margin_interest
        previous_trading_date = current_ts

        day_df = market_df[market_df["date"] == current_date].copy()
        day_prices = {
            row["ticker"]: float(row["close"])
            for _, row in day_df.iterrows()
        }
        for product, prices in product_price_lookup.items():
            product_close = prices.get(pd.Timestamp(current_date))
            if product_close is not None:
                day_prices[product] = float(product_close)

        pre_exit_equity = cash + sum(
            pos["qty"] * day_prices.get(ticker, pos["last_price"])
            for ticker, pos in positions.items()
        )

        for ticker in list(positions.keys()):
            position = positions[ticker]
            signal_ticker = str(position.get("signal_ticker") or ticker).upper()
            ticker_row = day_df[day_df["ticker"] == signal_ticker]

            if ticker_row.empty or ticker not in day_prices:
                continue

            row = ticker_row.iloc[0]
            close = float(day_prices[ticker])
            position["highest_price"] = max(
                float(position.get("highest_price", position["entry_price"])),
                close,
            )

            exit_reason = None
            gross_return_pct = (close / float(position["entry_price"])) - 1.0
            drawdown_from_high = (close / float(position["highest_price"])) - 1.0

            ai_exit_triggered = False
            if ai_exit_enabled:
                ai_score_val = pd.to_numeric(row.get("ai_score"), errors="coerce")
                if not pd.isna(ai_score_val):
                    effective_threshold = ai_exit_threshold
                    if ai_exit_dynamic_enabled and _vix_by_date:
                        ts = pd.Timestamp(current_date)
                        vix_val = _vix_by_date.get(ts)
                        if vix_val is None:
                            past = {k: v for k, v in _vix_by_date.items() if k <= ts}
                            vix_val = past[max(past)] if past else None
                        if vix_val is not None:
                            if float(vix_val) < ai_exit_vix_low:
                                effective_threshold = ai_exit_threshold_bull
                            elif float(vix_val) > ai_exit_vix_high:
                                effective_threshold = ai_exit_threshold_bear
                    ai_exit_triggered = float(ai_score_val) < effective_threshold

            day_stop_loss_pct, day_trailing_stop_pct, _ = resolve_regime_stop_params(
                regime_stop_spy_df,
                pd.Timestamp(current_date),
                fallback_stop_loss_pct=day_stop_loss_pct,
                fallback_trailing_stop_pct=day_trailing_stop_pct,
                enabled=regime_adaptive_stop_enabled,
                profile=regime_stop_profile,
            )

            if day_stop_loss_pct > 0 and gross_return_pct <= -day_stop_loss_pct:
                exit_reason = "STOP_LOSS"
            elif day_trailing_stop_pct > 0 and drawdown_from_high <= -day_trailing_stop_pct:
                exit_reason = "TRAILING_STOP"
            elif (
                day_max_holding_days > 0
                and (
                    pd.Timestamp(current_date) - pd.Timestamp(position["entry_date"])
                ).days
                >= day_max_holding_days
            ):
                exit_reason = "MAX_HOLDING"
            elif ai_exit_triggered:
                exit_reason = "AI_EXIT"
            elif bool(row["sell_signal"]):
                exit_reason = "SELL_SIGNAL"
            elif (
                day_take_profit_pct > 0
                and gross_return_pct >= day_take_profit_pct
            ):
                exit_reason = "TAKE_PROFIT"

            if (
                exit_reason is None
                and take_profit_partial_pct > 0
                and gross_return_pct >= take_profit_partial_pct
                and not bool(position.get("partial_exit_taken"))
            ):
                position_value = float(position["qty"]) * close
                partial_qty = float(position["qty"]) * partial_exit_ratio
                partial_notional = partial_qty * close
                partial_settings = day_ops_settings or SimpleNamespace(
                    max_position_pct=day_target_position_pct,
                    partial_exit_ratio=partial_exit_ratio,
                )
                thresholds = compute_partial_exit_thresholds(
                    portfolio_value=pre_exit_equity,
                    settings=partial_settings,
                    dust_min_usd=max(minimum_order_notional, 0.0),
                )
                partial_allowed, _ = evaluate_partial_exit(
                    position_market_value=position_value,
                    sell_notional=partial_notional,
                    thresholds=thresholds,
                    already_taken=False,
                )
                if partial_allowed and partial_qty > 0:
                    gross_value = partial_qty * close
                    net_value = gross_value * (1.0 - transaction_cost_pct)
                    cost_basis = float(position["cost_basis"]) * partial_exit_ratio
                    cash += net_value
                    position["qty"] -= partial_qty
                    position["cost_basis"] -= cost_basis
                    position["partial_exit_taken"] = True
                    trades.append(
                        {
                            "ticker": ticker,
                            "signal_ticker": signal_ticker,
                            "leveraged": bool(position.get("leveraged")),
                            "entry_notional_multiplier": float(
                                position.get("entry_notional_multiplier", 1.0)
                            ),
                            "entry_leverage_allowed": bool(
                                position.get("entry_leverage_allowed", True)
                            ),
                            "entry_date": position["entry_date"],
                            "exit_date": current_date,
                            "entry_price": position["entry_price"],
                            "exit_price": close,
                            "qty": partial_qty,
                            "cost_basis": cost_basis,
                            "exit_value": net_value,
                            "return_pct": (net_value / cost_basis) - 1.0,
                            "exit_reason": "PARTIAL_TAKE_PROFIT",
                        }
                    )

            if exit_reason is not None:
                position = positions.pop(ticker)
                qty = position["qty"]
                entry_price = position["entry_price"]
                entry_date = position["entry_date"]

                gross_value = qty * close
                cost = gross_value * transaction_cost_pct
                net_value = gross_value - cost
                cash += net_value

                return_pct = (net_value / position["cost_basis"]) - 1.0

                trades.append(
                    {
                        "ticker": ticker,
                        "signal_ticker": signal_ticker,
                        "leveraged": bool(position.get("leveraged")),
                        "entry_notional_multiplier": float(
                            position.get("entry_notional_multiplier", 1.0)
                        ),
                        "entry_leverage_allowed": bool(
                            position.get("entry_leverage_allowed", True)
                        ),
                        "entry_date": entry_date,
                        "exit_date": current_date,
                        "entry_price": entry_price,
                        "exit_price": close,
                        "qty": qty,
                        "cost_basis": position["cost_basis"],
                        "exit_value": net_value,
                        "return_pct": return_pct,
                        "exit_reason": exit_reason,
                    }
                )

        positions_value = sum(
            pos["qty"] * day_prices.get(ticker, pos["last_price"])
            for ticker, pos in positions.items()
        )
        equity = cash + positions_value

        slots_left = day_max_positions - len(positions)

        if slots_left > 0:
            held_signal_tickers = {
                str(pos.get("signal_ticker") or symbol).upper()
                for symbol, pos in positions.items()
            }
            active_universe = _active_universe_for_date(
                historical_universe_by_date,
                pd.Timestamp(current_date),
                normalized_base_universe,
            )
            asof_ticker_data = truncate_ticker_frames_asof(
                ticker_data,
                current_date,
                min_rows=1,
            )
            entry_mask = day_df["buy_signal"]
            if rank_ai_primary_selector_enabled and rank_ai_buy_gate_enabled:
                entry_mask = pd.Series(True, index=day_df.index)
            buy_candidates = day_df[
                entry_mask & (~day_df["ticker"].isin(held_signal_tickers))
            ].copy()
            if active_universe is not None:
                buy_candidates = buy_candidates[
                    buy_candidates["ticker"].isin(active_universe)
                ].copy()

            if not buy_candidates.empty:
                leveraged_mask = buy_candidates["ticker"].map(
                    lambda symbol: get_instrument(str(symbol)).is_leveraged_etf
                )
                allowed_leveraged = {
                    str(symbol).strip().upper()
                    for symbol in (leveraged_etf_allowlist or [])
                    if str(symbol).strip()
                }
                if allowed_leveraged:
                    disallowed_mask = leveraged_mask & ~buy_candidates["ticker"].isin(
                        allowed_leveraged
                    )
                    buy_candidates = buy_candidates[~disallowed_mask].copy()
                    leveraged_mask = buy_candidates["ticker"].map(
                        lambda symbol: get_instrument(str(symbol)).is_leveraged_etf
                    )
                leveraged_count = count_leveraged_etf_positions(set(positions))
                block_leveraged = (
                    not allow_leveraged_etfs
                    or leveraged_count >= max_leveraged_etf_positions
                )
                if not block_leveraged and _vix_by_date:
                    ts = pd.Timestamp(current_date)
                    past_vix = {k: v for k, v in _vix_by_date.items() if k <= ts}
                    vix_value = past_vix[max(past_vix)] if past_vix else None
                    block_leveraged = (
                        vix_value is not None
                        and float(vix_value) >= block_leveraged_etfs_vix_above
                    )
                if block_leveraged and not buy_candidates.empty:
                    buy_candidates = buy_candidates.loc[
                        ~leveraged_mask.astype(bool)
                    ].copy()

            ops_settings = day_ops_settings
            use_rank_gate = bool(rank_ai_buy_gate_enabled and ops_settings is not None)

            if buy_candidates.empty:
                selected = buy_candidates
            elif use_rank_gate:
                rank_scores = normalized_rank_history.get(
                    pd.Timestamp(current_date),
                    {},
                )
                cutoff = rank_ai_gate_effective_cutoff(ops_settings)
                buy_candidates = attach_rank_gate_scores_to_day_df(
                    buy_candidates,
                    scores=rank_scores,
                    cutoff=cutoff,
                )
                if tournament_alpha_enabled:
                    buy_candidates = _sort_tournament_alpha_candidates(
                        buy_candidates,
                        rank_weight=day_tournament_alpha_rank_weight,
                    )
                if rank_buy_top_k_enabled(ops_settings):
                    max_select = max_rank_new_buys_per_run(
                        ops_settings,
                        meaningful_positions_count=len(positions),
                    )
                    max_select = min(max_select, slots_left)
                else:
                    max_select = slots_left
                selected = buy_candidates.head(max_select)
            else:
                buy_candidates["trend_strength"] = (
                    buy_candidates["ma_fast"] / buy_candidates["ma_slow"]
                )
                buy_candidates["rank_ai_score"] = pd.to_numeric(
                    buy_candidates["ai_score"],
                    errors="coerce",
                ).fillna(0.0)
                buy_candidates["rank_momentum"] = pd.to_numeric(
                    buy_candidates["relative_return"],
                    errors="coerce",
                ).fillna(0.0)
                buy_candidates["rank_volatility"] = pd.to_numeric(
                    buy_candidates["volatility"],
                    errors="coerce",
                ).fillna(0.0)
                buy_candidates["rank_score"] = (
                    rank_trend_weight * (buy_candidates["trend_strength"] - 1.0)
                    + rank_ai_weight * buy_candidates["rank_ai_score"]
                    + rank_momentum_weight * buy_candidates["rank_momentum"]
                    - rank_volatility_weight * buy_candidates["rank_volatility"]
                )

                buy_candidates = buy_candidates.sort_values(
                    ["rank_score", "trend_strength", "rsi"],
                    ascending=[False, False, True],
                )

                selected = buy_candidates.head(slots_left)
            candidate_tickers = selected["ticker"].tolist()

            # Compute dynamic weights when using MVO/BL
            if day_allocation_method != "equal_weight" and len(candidate_tickers) > 1:
                candidate_ai_scores = {
                    row["ticker"]: float(
                        pd.to_numeric(row["ai_score"], errors="coerce") or 0.5
                    )
                    for _, row in selected.iterrows()
                }
                alloc_weights = compute_candidate_weights(
                    market_df=market_df,
                    candidate_tickers=candidate_tickers,
                    current_date=current_date,
                    ai_scores=candidate_ai_scores,
                    allocation_method=day_allocation_method,
                    lookback_days=mvo_lookback_days,
                    min_weight=mvo_min_weight,
                    max_weight=mvo_max_weight,
                )
                total_to_deploy = (
                    len(candidate_tickers)
                    * day_target_position_pct
                    * equity
                    * leverage_factor
                )
            else:
                alloc_weights = {t: 1.0 / max(len(candidate_tickers), 1) for t in candidate_tickers}
                total_to_deploy = None  # use original target_position_pct per ticker

            for _, row in selected.iterrows():
                signal_ticker = str(row["ticker"]).upper()
                ticker = signal_ticker
                close = float(row["close"])
                entry_risk = day_entry_risk.get(signal_ticker, {})
                entry_notional_multiplier = float(
                    entry_risk.get("notional_multiplier", 1.0)
                )
                entry_leverage_allowed = bool(
                    entry_risk.get("allow_leveraged", True)
                )

                product = route_map.get(signal_ticker) if prefer_leveraged_products else None
                if (
                    product
                    and product in day_prices
                    and allow_leveraged_etfs
                    and entry_leverage_allowed
                ):
                    current_vix = None
                    if _vix_by_date:
                        past_vix = {
                            date: value
                            for date, value in _vix_by_date.items()
                            if date <= pd.Timestamp(current_date)
                        }
                        current_vix = past_vix[max(past_vix)] if past_vix else None
                    vix_blocked = (
                        current_vix is not None
                        and block_leveraged_etfs_vix_above > 0
                        and float(current_vix) >= block_leveraged_etfs_vix_above
                    )
                    leverage_slots_full = (
                        count_leveraged_etf_positions(set(positions))
                        >= max_leveraged_etf_positions
                    )
                    if not vix_blocked and not leverage_slots_full:
                        ticker = product
                        close = float(day_prices[product])

                instrument = get_instrument(ticker)

                if close <= 0:
                    continue

                if (
                    instrument.is_leveraged_etf
                    and count_leveraged_etf_positions(set(positions))
                    >= max_leveraged_etf_positions
                ):
                    continue

                if crowding_guard_enabled:
                    crowding = apply_factor_crowding_limits(
                        ticker=signal_ticker,
                        open_symbols=held_signal_tickers,
                        ticker_data=asof_ticker_data,
                    )
                    if not crowding.allowed:
                        continue

                if correlation_guard_enabled:
                    correlation_ok, _ = is_correlation_allowed(
                        signal_ticker,
                        held_signal_tickers,
                        asof_ticker_data,
                        max_corr=max_correlation_threshold,
                        max_portfolio_avg_corr=max_portfolio_avg_correlation_threshold,
                        lookback_days=correlation_lookback_days,
                    )
                    if not correlation_ok:
                        continue

                if max_sector_positions is not None and max_sector_positions > 0:
                    sector_ok, _ = is_sector_allowed(
                        signal_ticker,
                        held_signal_tickers,
                        max_sector_positions=max_sector_positions,
                    )
                    if not sector_ok:
                        continue

                entry_day = pd.Timestamp(current_date).strftime("%Y-%m-%d")
                ops_settings = operational_settings if operational_settings is not None else None

                if llm_filter_enabled:
                    llm_ok, _ = evaluate_ticker_consensus(
                        signal_ticker,
                        settings=ops_settings,
                        as_of_date=entry_day,
                        cache_only=llm_cache_only,
                    )
                    if not llm_ok:
                        continue

                if news_sentiment_filter_enabled:
                    sentiment = get_ticker_sentiment(signal_ticker, as_of_date=entry_day)
                    if sentiment is not None and sentiment < news_sentiment_threshold:
                        continue

                if total_to_deploy is not None:
                    target_value = total_to_deploy * alloc_weights.get(
                        ticker, 1.0 / len(candidate_tickers)
                    )
                else:
                    target_value = (
                        equity * day_target_position_pct * leverage_factor
                    )

                target_value = min(
                    target_value,
                    equity * adjust_position_cap_for_instrument(
                        day_target_position_pct * leverage_factor,
                        ticker,
                    ),
                )

                if rank_position_sizing_enabled and use_rank_gate:
                    pct = row.get("rank_ai_percentile")
                    if pct is not None and pd.notna(pct) and ops_settings is not None:
                        cutoff = rank_ai_gate_effective_cutoff(ops_settings)
                        span = max(1.0 - float(cutoff), 1e-6)
                        strength = min(1.0, max(0.0, (float(pct) - float(cutoff)) / span))
                        mult = float(rank_position_sizing_min_mult) + strength * (
                            float(rank_position_sizing_max_mult)
                            - float(rank_position_sizing_min_mult)
                        )
                        target_value *= mult

                target_value *= entry_notional_multiplier

                target_value = min(
                    target_value,
                    equity * adjust_position_cap_for_instrument(
                        day_target_position_pct * leverage_factor,
                        ticker,
                    ),
                )

                current_effective_exposure = sum(
                    float(pos["qty"])
                    * float(day_prices.get(symbol, pos["last_price"]))
                    * get_instrument(symbol).abs_multiple
                    for symbol, pos in positions.items()
                )
                current_gross_exposure = sum(
                    float(pos["qty"])
                    * float(day_prices.get(symbol, pos["last_price"]))
                    for symbol, pos in positions.items()
                )
                current_account_equity = cash + current_gross_exposure
                effective_limit = (
                    current_account_equity
                    * max_effective_leverage_exposure_pct
                )
                effective_capacity = max(
                    0.0,
                    (effective_limit - current_effective_exposure)
                    / instrument.abs_multiple,
                )
                margin_capacity = max(
                    0.0,
                    current_account_equity * leverage_factor
                    - current_gross_exposure,
                )
                reserve_value = current_account_equity * cash_reserve_pct
                reserve_adjusted_capacity = max(
                    0.0,
                    current_account_equity * max(leverage_factor - 1.0, 0.0)
                    + cash
                    - reserve_value,
                )
                available_value = min(
                    target_value,
                    effective_capacity,
                    margin_capacity,
                    reserve_adjusted_capacity,
                )

                if available_value <= 0 or available_value < minimum_order_notional:
                    continue

                cost = available_value * transaction_cost_pct
                net_investment = available_value - cost

                if net_investment <= 0:
                    continue

                qty = net_investment / close
                if fractionable is not None and ticker not in fractionable:
                    qty = math.floor(qty)
                    if qty <= 0:
                        continue
                    net_investment = qty * close
                    available_value = net_investment / (1.0 - transaction_cost_pct)
                    if available_value < minimum_order_notional:
                        continue
                cash -= available_value

                positions[ticker] = {
                    "signal_ticker": signal_ticker,
                    "leveraged": instrument.is_leveraged_etf,
                    "entry_notional_multiplier": entry_notional_multiplier,
                    "entry_leverage_allowed": entry_leverage_allowed,
                    "qty": qty,
                    "entry_price": close,
                    "entry_date": current_date,
                    "cost_basis": available_value,
                    "last_price": close,
                    "highest_price": close,
                    "partial_exit_taken": False,
                }
                entry_events.append(
                    {
                        "market_date": pd.Timestamp(current_date).date().isoformat(),
                        "signal_ticker": signal_ticker,
                        "execution_ticker": ticker,
                        "leveraged": instrument.is_leveraged_etf,
                        "quality_notional_multiplier": entry_notional_multiplier,
                        "quality_allow_leveraged": entry_leverage_allowed,
                        "planned_notional": available_value,
                        "planned_notional_pct": (
                            available_value / current_account_equity
                            if current_account_equity > 0
                            else None
                        ),
                        "rank_ai_score": row.get("rank_ai_score"),
                        "rank_ai_percentile": row.get("rank_ai_percentile"),
                    }
                )
                held_signal_tickers.add(signal_ticker)

        for ticker, pos in positions.items():
            if ticker in day_prices:
                pos["last_price"] = day_prices[ticker]

        positions_value = sum(
            pos["qty"] * pos["last_price"]
            for pos in positions.values()
        )
        equity = cash + positions_value

        equity_rows.append(
            {
                "date": current_date,
                "cash": cash,
                "positions_value": positions_value,
                "equity": equity,
                "borrowed_cash": max(-cash, 0.0),
                "gross_exposure_pct": (
                    positions_value / equity if equity > 0 else float("inf")
                ),
                "cumulative_margin_interest": cumulative_margin_interest,
                "positions_count": len(positions),
                "open_symbols": ",".join(sorted(positions.keys())),
                "open_signal_symbols": ",".join(
                    sorted(
                        str(pos.get("signal_ticker") or symbol).upper()
                        for symbol, pos in positions.items()
                    )
                ),
                "leveraged_positions_count": count_leveraged_etf_positions(
                    set(positions)
                ),
            }
        )

    equity_df = pd.DataFrame(equity_rows)
    equity_df.attrs["entry_events"] = pd.DataFrame(
        entry_events,
        columns=list(PORTFOLIO_ENTRY_COLUMNS),
    )

    if equity_df.empty:
        raise ValueError("No equity rows generated")

    equity_df["daily_return"] = equity_df["equity"].pct_change().fillna(0.0)
    equity_df["running_max"] = equity_df["equity"].cummax()
    equity_df["drawdown"] = equity_df["equity"] / equity_df["running_max"] - 1.0

    trades_df = pd.DataFrame(trades)

    final_equity = float(equity_df["equity"].iloc[-1])
    total_return = final_equity / initial_cash - 1.0
    max_drawdown = float(equity_df["drawdown"].min())

    trades_count = int(len(trades_df))

    if trades_count > 0:
        win_rate = float((trades_df["return_pct"] > 0).mean())
    else:
        win_rate = 0.0

    benchmark_data = ticker_data
    if benchmark_universe is not None:
        allowed_benchmark = {
            str(ticker).strip().upper()
            for ticker in benchmark_universe
            if str(ticker).strip()
        }
        benchmark_data = {
            str(ticker).upper(): frame
            for ticker, frame in ticker_data.items()
            if str(ticker).upper() in allowed_benchmark
        }
        if not benchmark_data:
            raise ValueError("benchmark_universe contains no loaded ticker data")
    benchmark_values = _build_equal_weight_benchmark_values(
        equity_df["date"],
        benchmark_data,
        initial_cash,
    )
    equity_df["benchmark_equity"] = benchmark_values
    last_benchmark = float(equity_df["benchmark_equity"].iloc[-1])
    if not pd.notna(last_benchmark) or last_benchmark <= 0:
        raise ValueError("Equal-weight benchmark equity is invalid at end of backtest")
    benchmark_return = last_benchmark / initial_cash - 1.0

    # Annualized Sharpe (252 trading days, risk-free=0)
    daily_returns = equity_df["daily_return"]
    std = float(daily_returns.std())
    sharpe_ratio = float(daily_returns.mean() / std * (252 ** 0.5)) if std > 1e-10 else 0.0

    result = PortfolioBacktestResult(
        initial_cash=initial_cash,
        final_equity=final_equity,
        total_return=total_return,
        max_drawdown=max_drawdown,
        trades=trades_count,
        win_rate=win_rate,
        benchmark_return=benchmark_return,
        sharpe_ratio=sharpe_ratio,
    )

    return result, equity_df, trades_df


def save_portfolio_backtest_outputs(
    output_dir: str | Path,
    result: PortfolioBacktestResult,
    equity_df: pd.DataFrame,
    trades_df: pd.DataFrame,
) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_df = pd.DataFrame(
        [
            {
                "initial_cash": result.initial_cash,
                "final_equity": result.final_equity,
                "total_return": result.total_return,
                "benchmark_return": result.benchmark_return,
                "max_drawdown": result.max_drawdown,
                "sharpe_ratio": result.sharpe_ratio,
                "trades": result.trades,
                "win_rate": result.win_rate,
            }
        ]
    )

    summary_df.to_csv(output_dir / "portfolio_summary.csv", index=False)
    equity_df.to_csv(output_dir / "portfolio_equity.csv", index=False)
    trades_df.to_csv(output_dir / "portfolio_trades.csv", index=False)
    entry_events = equity_df.attrs.get("entry_events")
    if not isinstance(entry_events, pd.DataFrame):
        entry_events = pd.DataFrame(columns=list(PORTFOLIO_ENTRY_COLUMNS))
    entry_events.reindex(columns=list(PORTFOLIO_ENTRY_COLUMNS)).to_csv(
        output_dir / "portfolio_entries.csv",
        index=False,
    )
    from src.monthly_backtest_review import write_monthly_backtest_review

    write_monthly_backtest_review(
        output_dir,
        equity_df,
        trades_df,
        initial_cash=result.initial_cash,
    )
