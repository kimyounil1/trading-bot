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
    "high_52w_ratio",
    "low_52w_ratio",
    "vix_level",
    "spy_rel_return_20d",
    # Macro context features (Phase 5-B)
    "yield_spread_10y3m",
    "dxy_20d_return",
    "gold_20d_return",
    "vix_percentile_52w",
]

REQUIRED_PRICE_COLUMNS = {"date", "high", "low", "close", "volume"}
MAX_FEATURE_LOOKBACK = 252


def build_features(
    df: pd.DataFrame,
    prediction_horizon: int = 5,
    target_return_threshold: float = 0.0,
    vix_df: pd.DataFrame | None = None,
    spy_df: pd.DataFrame | None = None,
    macro_df: pd.DataFrame | None = None,
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

    # 신규 상장 등으로 앞부분에 NaN이 있는 경우 제거 (ta 라이브러리 NaN 전파 방지)
    df = df.dropna(subset=["open", "high", "low", "close", "volume"]).reset_index(drop=True)

    if len(df) < minimum_rows:
        raise ValueError(
            f"Not enough rows to build features after dropping NaN: "
            f"need at least {minimum_rows}, got {len(df)}"
        )

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

    # 52주(252거래일) 고점/저점 대비 현재 위치
    df["high_52w"] = df["close"].rolling(252).max()
    df["low_52w"] = df["close"].rolling(252).min()
    df["high_52w_ratio"] = df["close"] / df["high_52w"]
    df["low_52w_ratio"] = df["close"] / df["low_52w"]

    # VIX 공포지수 + 52주 백분위 (제공되지 않으면 0)
    if vix_df is not None and not vix_df.empty and "close" in vix_df.columns:
        vix_aligned = pd.merge(
            df[["date"]],
            vix_df[["date", "close"]].rename(columns={"close": "vix_level"}),
            on="date",
            how="left",
        )
        vix_series = vix_aligned["vix_level"].ffill().bfill()
        df["vix_level"] = vix_series.values
        # 52주 VIX 백분위: 현재 VIX가 지난 1년 중 어느 수준인지 (0=최저공포, 1=최고공포)
        df["vix_percentile_52w"] = (
            vix_series.rolling(252).rank(pct=True).values
        )
    else:
        df["vix_level"] = 0.0
        df["vix_percentile_52w"] = 0.0

    # SPY 대비 상대 수익률 20일 (제공되지 않으면 0)
    if spy_df is not None and not spy_df.empty and "close" in spy_df.columns:
        spy_aligned = pd.merge(
            df[["date"]],
            spy_df[["date", "close"]].rename(columns={"close": "spy_close"}),
            on="date",
            how="left",
        )
        spy_aligned["spy_close"] = spy_aligned["spy_close"].ffill().bfill()
        spy_return_20d = spy_aligned["spy_close"].pct_change(20)
        df["spy_rel_return_20d"] = df["return_20d"] - spy_return_20d.values
    else:
        df["spy_rel_return_20d"] = 0.0

    # 매크로 피처: 금리 스프레드, 달러, 금 (제공되지 않으면 0)
    if macro_df is not None and not macro_df.empty:
        mac = pd.merge(df[["date"]], macro_df, on="date", how="left").ffill().bfill()
        if "tnx_close" in mac.columns and "irx_close" in mac.columns:
            # 10Y-3M 스프레드: 음수 = 역전 (경기침체/위험회피 신호)
            df["yield_spread_10y3m"] = (mac["tnx_close"] - mac["irx_close"]).values
        else:
            df["yield_spread_10y3m"] = 0.0
        if "dxy_close" in mac.columns:
            df["dxy_20d_return"] = mac["dxy_close"].pct_change(20).values
        else:
            df["dxy_20d_return"] = 0.0
        if "gold_close" in mac.columns:
            df["gold_20d_return"] = mac["gold_close"].pct_change(20).values
        else:
            df["gold_20d_return"] = 0.0
    else:
        df["yield_spread_10y3m"] = 0.0
        df["dxy_20d_return"] = 0.0
        df["gold_20d_return"] = 0.0

    df["future_return"] = df["close"].shift(-prediction_horizon) / df["close"] - 1.0
    df["target"] = (df["future_return"] > target_return_threshold).astype(int)

    feature_df = df.dropna().reset_index(drop=True)
    if feature_df.empty:
        raise ValueError("Feature frame is empty after indicator construction")

    return feature_df
