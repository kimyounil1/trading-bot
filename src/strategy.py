from __future__ import annotations

import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD
from ta.volatility import AverageTrueRange
from src.settings import StrategyProfile


def add_indicators(
    df: pd.DataFrame,
    profile: StrategyProfile | None = None,
    *,
    ma_fast: int | None = None,
    ma_slow: int | None = None,
) -> pd.DataFrame:
    df = df.copy()
    # Some data providers return holiday placeholders with NaN OHLC values.
    # Drop invalid bars so rolling indicators don't become NaN at the latest row.
    required_cols = [col for col in ("close", "high", "low") if col in df.columns]
    if required_cols:
        for col in required_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=required_cols).copy()
    if df.empty:
        return df

    if profile is not None:
        ma_fast = profile.ma_fast
        ma_slow = profile.ma_slow
    if ma_fast is None:
        ma_fast = 20
    if ma_slow is None:
        ma_slow = 50

    df["ma_fast"] = df["close"].rolling(ma_fast).mean()
    df["ma_slow"] = df["close"].rolling(ma_slow).mean()
    df["rsi"] = RSIIndicator(close=df["close"], window=14).rsi()
    if len(df) >= 14:
        df["atr"] = AverageTrueRange(high=df["high"], low=df["low"], close=df["close"], window=14).average_true_range()
    else:
        # ta's AverageTrueRange indexes tr[window-1] and crashes on shorter frames
        # (newly listed tickers from the dynamic universe).
        df["atr"] = float("nan")

    # Legacy aliases
    df["ma20"] = df["ma_fast"]
    df["ma50"] = df["ma_slow"]

    return df


def generate_signal(
    data: pd.Series | pd.DataFrame,
    profile: StrategyProfile | None = None,
    *,
    rsi_buy_limit: float | None = None,
    model: any = None,
    benchmark_df: pd.DataFrame = None,
) -> str:
    """
    Generates a signal from either a legacy indicator frame or a profile row.
    """
    row = data.iloc[-1] if isinstance(data, pd.DataFrame) else data

    # 1. Basic Trend/RSI Signal
    ma_fast = row["ma_fast"]
    ma_slow = row["ma_slow"]
    rsi = row["rsi"]

    trend_up = ma_fast > ma_slow
    buy_limit = (
        profile.rsi_buy_limit
        if profile is not None and rsi_buy_limit is None
        else (70 if rsi_buy_limit is None else rsi_buy_limit)
    )
    rsi_ok = rsi < buy_limit

    # Default action
    action = "HOLD"

    # Sell signal: Trend turns down
    if ma_fast < ma_slow:
        return "SELL"

    # Entry Signal Logic
    if trend_up and rsi_ok:
        # A. AI Score Filter
        if profile is not None and profile.use_ai_score and model is not None:
            if "ai_score" in row and row["ai_score"] < profile.ai_score_buy_threshold:
                return "HOLD"

        # B. Volume Filter
        if profile is not None and profile.volume_filter_enabled:
            if "volume_change_5d" in row and row["volume_change_5d"] < profile.min_volume_ratio:
                return "HOLD"

        # C. Relative Strength Filter
        if (
            profile is not None
            and profile.relative_strength_filter_enabled
            and benchmark_df is not None
        ):
            bench_row = benchmark_df[benchmark_df["date"] == row["date"]]
            if not bench_row.empty:
                ticker_return = row.get("return_20d", 0)
                bench_return = bench_row["return_20d"].iloc[0] if "return_20d" in bench_row.columns else 0

                if ticker_return < bench_return + profile.relative_strength_min_excess_return:
                    return "HOLD"

        # D. Entry Ranking (Placeholder for advanced logic)
        # In a full implementation, this would use profile.rank_* weights

        return "BUY"

    return "HOLD"


def is_bullish_market_regime(
    benchmark_df: pd.DataFrame,
    ma_fast: int = 50,
    ma_slow: int = 200,
) -> bool:
    if benchmark_df.empty:
        raise ValueError("No benchmark price data available for market regime")

    # Temporary helper to mimic add_indicators behavior with raw params
    df = benchmark_df.copy()
    df["ma_fast"] = df["close"].rolling(ma_fast).mean()
    df["ma_slow"] = df["close"].rolling(ma_slow).mean()

    if df.empty or len(df) < ma_slow:
        return False

    latest = df.iloc[-1]
    return bool(latest["ma_fast"] > latest["ma_slow"])


def build_market_regime_frame(
    benchmark_df: pd.DataFrame,
    ma_fast: int = 50,
    ma_slow: int = 200,
) -> pd.DataFrame:
    if benchmark_df.empty:
        raise ValueError("No benchmark price data available for market regime")

    df = benchmark_df.copy()
    df["ma_fast"] = df["close"].rolling(ma_fast).mean()
    df["ma_slow"] = df["close"].rolling(ma_slow).mean()

    if len(df) < ma_slow:
        return pd.DataFrame(columns=["date", "market_regime_bullish"])

    df["date"] = pd.to_datetime(df["date"])
    df["market_regime_bullish"] = df["ma_fast"] > df["ma_slow"]
    return df[["date", "market_regime_bullish"]].copy()
