import pandas as pd
from ta.momentum import RSIIndicator


def add_indicators(
    df: pd.DataFrame,
    ma_fast: int = 20,
    ma_slow: int = 50,
    rsi_window: int = 14,
) -> pd.DataFrame:
    df = df.copy()

    df["ma_fast"] = df["close"].rolling(ma_fast).mean()
    df["ma_slow"] = df["close"].rolling(ma_slow).mean()
    df["rsi"] = RSIIndicator(close=df["close"], window=rsi_window).rsi()

    # 기존 코드 호환용 alias
    df["ma20"] = df["ma_fast"]
    df["ma50"] = df["ma_slow"]

    return df.dropna()


def generate_signal(
    df: pd.DataFrame,
    rsi_buy_limit: float = 70,
) -> str:
    latest = df.iloc[-1]

    if latest["ma_fast"] > latest["ma_slow"] and latest["rsi"] < rsi_buy_limit:
        return "BUY"

    if latest["ma_fast"] < latest["ma_slow"]:
        return "SELL"

    return "HOLD"


def is_bullish_market_regime(
    benchmark_df: pd.DataFrame,
    ma_fast: int = 50,
    ma_slow: int = 200,
) -> bool:
    if benchmark_df.empty:
        raise ValueError("No benchmark price data available for market regime")

    regime_df = add_indicators(
        benchmark_df,
        ma_fast=ma_fast,
        ma_slow=ma_slow,
    )
    if regime_df.empty:
        raise ValueError(
            "Not enough benchmark price history to evaluate market regime "
            f"(rows={len(benchmark_df)}, ma_slow={ma_slow})"
        )

    latest = regime_df.iloc[-1]
    return bool(latest["ma_fast"] > latest["ma_slow"])


def build_market_regime_frame(
    benchmark_df: pd.DataFrame,
    ma_fast: int = 50,
    ma_slow: int = 200,
) -> pd.DataFrame:
    if benchmark_df.empty:
        raise ValueError("No benchmark price data available for market regime")

    regime_df = add_indicators(
        benchmark_df,
        ma_fast=ma_fast,
        ma_slow=ma_slow,
    ).copy()
    if regime_df.empty:
        raise ValueError(
            "Not enough benchmark price history to build market regime frame "
            f"(rows={len(benchmark_df)}, ma_slow={ma_slow})"
        )

    regime_df["date"] = pd.to_datetime(regime_df["date"])
    regime_df["market_regime_bullish"] = regime_df["ma_fast"] > regime_df["ma_slow"]
    return regime_df[["date", "market_regime_bullish"]].copy()
