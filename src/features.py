import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD
from ta.volatility import AverageTrueRange


FEATURE_COLUMNS = [
    "return_1d",
    "return_5d",
    "return_10d",
    "return_20d",
    "volatility_10d",
    "volatility_20d",
    "volume_change_5d",
    "ma_ratio_10_50",
    "ma_ratio_20_200",
    "rsi_14",
    "macd",
    "macd_signal",
    "atr_pct",
]

REQUIRED_PRICE_COLUMNS = {"date", "high", "low", "close", "volume"}
MAX_FEATURE_LOOKBACK = 200


def build_features(
    df: pd.DataFrame,
    prediction_horizon: int = 5,
    target_return_threshold: float = 0.0,
) -> pd.DataFrame:
    if prediction_horizon <= 0:
        raise ValueError("prediction_horizon must be positive")

    missing = REQUIRED_PRICE_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing required price columns: {sorted(missing)}")

    minimum_rows = MAX_FEATURE_LOOKBACK + prediction_horizon
    if len(df) < minimum_rows:
        raise ValueError(
            f"Not enough rows to build features: need at least {minimum_rows}, got {len(df)}"
        )

    df = df.copy()
    df = df.sort_values("date").reset_index(drop=True)

    df["return_1d"] = df["close"].pct_change(1)
    df["return_5d"] = df["close"].pct_change(5)
    df["return_10d"] = df["close"].pct_change(10)
    df["return_20d"] = df["close"].pct_change(20)

    df["volatility_10d"] = df["return_1d"].rolling(10).std()
    df["volatility_20d"] = df["return_1d"].rolling(20).std()

    df["volume_change_5d"] = df["volume"].pct_change(5)

    df["ma10"] = df["close"].rolling(10).mean()
    df["ma20"] = df["close"].rolling(20).mean()
    df["ma50"] = df["close"].rolling(50).mean()
    df["ma200"] = df["close"].rolling(200).mean()

    df["ma_ratio_10_50"] = df["ma10"] / df["ma50"] - 1.0
    df["ma_ratio_20_200"] = df["ma20"] / df["ma200"] - 1.0

    df["rsi_14"] = RSIIndicator(close=df["close"], window=14).rsi()

    macd = MACD(close=df["close"])
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()

    atr = AverageTrueRange(
        high=df["high"],
        low=df["low"],
        close=df["close"],
        window=14,
    )
    df["atr_pct"] = atr.average_true_range() / df["close"]

    df["future_return"] = df["close"].shift(-prediction_horizon) / df["close"] - 1.0
    df["target"] = (df["future_return"] > target_return_threshold).astype(int)

    feature_df = df.dropna().reset_index(drop=True)
    if feature_df.empty:
        raise ValueError("Feature frame is empty after indicator construction")

    return feature_df
