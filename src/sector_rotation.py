"""섹터 순환매(Sector Rotation) 탐지 및 리더십 분석."""

import pandas as pd
from typing import List, Dict
from src.data_loader import load_price_data_batch

SECTOR_ETFS = {
    "XLK": "Technology",
    "XLF": "Financials",
    "XLV": "Health Care",
    "XLY": "Consumer Discretionary",
    "XLP": "Consumer Staples",
    "XLE": "Energy",
    "XLI": "Industrials",
    "XLB": "Materials",
    "XLRE": "Real Estate",
    "XLU": "Utilities",
    "XLC": "Communication Services"
}

def get_sector_leadership(lookback_days: int = 20) -> List[str]:
    """최근 수익률을 기반으로 시장을 주도하는 상위 3개 섹터를 반환한다."""
    try:
        tickers = list(SECTOR_ETFS.keys())
        # 섹터 데이터 로드
        data = load_price_data_batch(tickers, period="1y")
        
        returns = {}
        for ticker in tickers:
            df = data.get(ticker)
            if df is not None and len(df) > lookback_days:
                close = df["adj_close"] if "adj_close" in df.columns else df["close"]
                ret = (close.iloc[-1] - close.iloc[-lookback_days]) / close.iloc[-lookback_days]
                returns[ticker] = ret
        
        # 수익률 순으로 정렬
        sorted_sectors = sorted(returns.items(), key=lambda x: x[1], reverse=True)
        top_sectors = [s[0] for s in sorted_sectors[:3]]
        
        print(f"Sector Leadership (Top 3): {top_sectors}")
        return top_sectors

    except Exception as e:
        print(f"Error in sector rotation analysis: {e}")
        return []

def get_ticker_sector_bonus(ticker: str, top_sectors: List[str]) -> float:
    """종목이 주도 섹터에 속해있으면 보너스 점수를 부여한다."""
    from src.sector import SECTOR_MAP
    
    ticker_sector = SECTOR_MAP.get(ticker)
    if not ticker_sector:
        return 0.0
    
    # SECTOR_MAP의 섹터명과 ETF를 매핑해야 함
    # 편의상 직접 매핑 또는 유사도 체크
    sector_to_etf = {
        "tech": "XLK",
        "semis": "XLK",
        "software": "XLK",
        "financials": "XLF",
        "healthcare": "XLV",
        "consumer_disc": "XLY",
        "consumer_stap": "XLP",
        "energy": "XLE",
        "industrials": "XLI",
        "materials": "XLB",
        "real_estate": "XLRE",
        "utilities": "XLU",
        "comm_services": "XLC"
    }
    
    mapped_etf = sector_to_etf.get(ticker_sector)
    if mapped_etf in top_sectors:
        return 0.05 # AI Score 보너스
    
    return 0.0
