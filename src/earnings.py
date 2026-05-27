"""실적 발표 일정(Earnings Calendar) 관리 및 필터링."""

import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Tuple

import pandas as pd
import yfinance as yf

EARNINGS_CACHE_DIR = Path("data/earnings")


def _get_cache_path(ticker: str) -> Path:
    return EARNINGS_CACHE_DIR / f"{ticker.upper()}.json"


def get_next_earnings_date(ticker: str, cache_ttl_hours: int = 24) -> Optional[pd.Timestamp]:
    """티커의 다음 실적 발표일을 가져온다 (캐시 지원)."""
    cache_path = _get_cache_path(ticker)
    
    # 1. 캐시 확인
    if cache_path.exists():
        age_hours = (time.time() - cache_path.stat().st_mtime) / 3600
        if age_hours < cache_ttl_hours:
            try:
                data = json.loads(cache_path.read_text())
                if data.get("next_earnings"):
                    return pd.to_datetime(data["next_earnings"])
            except Exception:
                pass

    # 2. API 요청 (yfinance)
    try:
        t = yf.Ticker(ticker)
        calendar = t.calendar
        
        earnings_date = None
        if isinstance(calendar, dict) and "Earnings Date" in calendar:
            # 리스트 형태일 수 있음 [start, end]
            dates = calendar["Earnings Date"]
            if isinstance(dates, list) and len(dates) > 0:
                earnings_date = pd.to_datetime(dates[0])
            else:
                earnings_date = pd.to_datetime(dates)
        elif isinstance(calendar, pd.DataFrame) and "Earnings Date" in calendar.index:
            val = calendar.loc["Earnings Date"].iloc[0]
            earnings_date = pd.to_datetime(val)
        
        # fallback: earnings_dates property (최근 1~2개 일정 제공)
        if earnings_date is None:
            dates_df = t.earnings_dates
            if dates_df is not None and not dates_df.empty:
                # 미래 날짜 중 가장 가까운 것 선택
                future_dates = dates_df[dates_df.index > pd.Timestamp.now(tz=dates_df.index.tz)]
                if not future_dates.empty:
                    earnings_date = future_dates.index[0]

        if earnings_date:
            # 시간대 정보 제거 (비교 편의성)
            earnings_date = earnings_date.tz_localize(None)
            
            # 캐시 저장
            EARNINGS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps({
                "ticker": ticker,
                "next_earnings": earnings_date.isoformat(),
                "fetched_at": datetime.now().isoformat()
            }))
            return earnings_date

    except Exception as e:
        print(f"Error fetching earnings for {ticker}: {e}")

    return None


def is_earnings_window(
    ticker: str,
    target_date: pd.Timestamp,
    lookback_days: int = 3,
    lookforward_days: int = 1
) -> Tuple[bool, str]:
    """대상 날짜가 실적 발표 전후 금지 기간에 해당하는지 체크한다."""
    next_earnings = get_next_earnings_date(ticker)
    if next_earnings is None:
        return False, "no earnings data"

    # 날짜 정규화 (시분초 제거)
    target_dt = target_date.normalize()
    earnings_dt = next_earnings.normalize()
    
    diff_days = (earnings_dt - target_dt).days
    
    # 예: lookback=3, lookforward=1 이면
    # 실적 발표일 기준 -3일부터 +1일까지 차단
    # diff_days 가 0이면 당일, 3이면 3일 전, -1이면 발표 다음날
    if -lookforward_days <= diff_days <= lookback_days:
        return True, f"earnings in {diff_days} days ({earnings_dt.date()})"
    
    return False, f"next earnings: {earnings_dt.date()} ({diff_days} days left)"
