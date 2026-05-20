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
