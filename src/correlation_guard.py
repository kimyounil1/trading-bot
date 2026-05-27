"""상관계수 기반 포트폴리오 리스크 관리."""

import pandas as pd
import numpy as np
from typing import Dict, Set, Tuple


def is_correlation_allowed(
    ticker: str,
    open_symbols: Set[str],
    ticker_data: Dict[str, pd.DataFrame],
    max_corr: float = 0.85,
    lookback_days: int = 60,
) -> Tuple[bool, str]:
    """매수 후보 종목과 기존 보유 종목 간의 상관관계를 체크한다.

    상관관계가 max_corr보다 높으면 False를 반환한다.
    """
    if not open_symbols:
        return True, "no open positions to compare"

    target_df = ticker_data.get(ticker)
    if target_df is None or len(target_df) < lookback_days:
        return True, f"insufficient data for {ticker} (skipped correlation check)"

    # 대상 종목의 수익률 계산
    target_close = target_df["adj_close"] if "adj_close" in target_df.columns else target_df["close"]
    target_returns = target_close.pct_change().iloc[-lookback_days:]

    for symbol in open_symbols:
        symbol_df = ticker_data.get(symbol)
        if symbol_df is None or len(symbol_df) < lookback_days:
            continue

        symbol_close = symbol_df["adj_close"] if "adj_close" in symbol_df.columns else symbol_df["close"]
        symbol_returns = symbol_close.pct_change().iloc[-lookback_days:]

        # 날짜 인덱스 정렬 후 상관계수 계산
        combined = pd.concat([target_returns, symbol_returns], axis=1).dropna()
        if len(combined) < lookback_days // 2:
            continue

        correlation = combined.corr().iloc[0, 1]

        if not np.isnan(correlation) and correlation > max_corr:
            return False, f"high correlation ({correlation:.2f}) with {symbol} (threshold={max_corr})"

    return True, "correlation check passed"
