"""시장 레짐 분류 (BULL, BEAR, NEUTRAL)."""

import pandas as pd
from typing import Union


def compute_daily_regime(
    spy_df: pd.DataFrame,
    vix_df: pd.DataFrame,
    spy_ma_fast: int = 50,
    spy_ma_slow: int = 200,
    vix_high: float = 25.0,
    vix_low: float = 20.0,
) -> pd.Series:
    """SPY 추세와 VIX 수준을 기반으로 일별 시장 레짐을 계산한다."""
    if spy_df is None or spy_df.empty or vix_df is None or vix_df.empty:
        return pd.Series()

    # 데이터 정렬 및 날짜 인덱스 설정 (병합 및 계산용)
    spy_work = spy_df.set_index("date") if "date" in spy_df.columns else spy_df
    vix_work = vix_df.set_index("date") if "date" in vix_df.columns else vix_df

    spy_close = spy_work["adj_close"] if "adj_close" in spy_work.columns else spy_work["close"]
    vix_close = vix_work["adj_close"] if "adj_close" in vix_work.columns else vix_work["close"]

    # 인덱스 합집합으로 병합 (전체 기간 커버)
    combined = pd.DataFrame({"spy": spy_close, "vix": vix_close})
    # VIX와 SPY 모두 존재하는 데이터만 사용하거나 ffill/bfill 고려 (여기서는 단순 dropna)
    combined = combined.dropna()

    combined["spy_fast"] = combined["spy"].rolling(spy_ma_fast).mean()
    combined["spy_slow"] = combined["spy"].rolling(spy_ma_slow).mean()

    # 기본값 NEUTRAL
    combined["regime"] = "NEUTRAL"

    # BEAR: VIX가 높거나 SPY가 강한 하락 추세일 때
    bear_mask = (combined["vix"] > vix_high) | (combined["spy_fast"] < combined["spy_slow"] * 0.95)
    combined.loc[bear_mask, "regime"] = "BEAR"

    # BULL: BEAR가 아니고 SPY가 상승 추세이며 VIX가 낮을 때
    bull_mask = (
        (~bear_mask)
        & (combined["spy_fast"] > combined["spy_slow"])
        & (combined["vix"] < vix_low)
    )
    combined.loc[bull_mask, "regime"] = "BULL"

    return combined["regime"]


def get_current_regime(
    spy_df: pd.DataFrame,
    vix_df: pd.DataFrame,
    spy_ma_fast: int = 50,
    spy_ma_slow: int = 200,
    vix_high: float = 25.0,
    vix_low: float = 20.0,
) -> str:
    """가장 최근의 시장 레짐을 반환한다."""
    regimes = compute_daily_regime(
        spy_df, vix_df, spy_ma_fast, spy_ma_slow, vix_high, vix_low
    )
    if regimes.empty:
        return "NEUTRAL"
    return str(regimes.iloc[-1])
