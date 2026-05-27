"""경제 지표 발표 일정(FOMC, CPI, NFP) 기반 리스크 관리."""

from datetime import datetime, date
from typing import Tuple, List, Optional
import pandas as pd

# 2026년 주요 경제 지표 발표 일정 (ET 기준)
# FOMC: 연준 금리 결정 (발표일 기준)
FOMC_2026 = [
    "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17",
    "2026-07-29", "2026-09-16", "2026-10-28", "2026-12-09"
]

# CPI: 소비자 물가 지수
CPI_2026 = [
    "2026-01-13", "2026-02-13", "2026-03-11", "2026-04-10",
    "2026-05-12", "2026-06-10", "2026-07-14", "2026-08-11",
    "2026-09-11", "2026-10-14", "2026-11-12", "2026-12-11"
]

# NFP: 비농업 고용 지수 (보통 매월 첫째 금요일)
NFP_2026 = [
    "2026-01-09", "2026-02-11", "2026-03-06", "2026-04-03",
    "2026-05-08", "2026-06-05", "2026-07-02", "2026-08-07",
    "2026-09-04", "2026-10-02", "2026-11-06", "2026-12-04"
]

def get_macro_event_risk(
    current_date: Optional[date] = None,
    lookforward_days: int = 2,
    lookback_days: int = 1
) -> Tuple[bool, str]:
    """현재 날짜가 주요 경제 지표 발표 전후 리스크 윈도우에 있는지 확인한다.
    
    Returns:
        (is_high_risk, reason)
    """
    if current_date is None:
        current_date = datetime.now().date()
    
    current_ts = pd.Timestamp(current_date)
    
    all_events = {
        "FOMC": FOMC_2026,
        "CPI": CPI_2026,
        "NFP": NFP_2026
    }
    
    for event_name, dates in all_events.items():
        for d_str in dates:
            event_ts = pd.Timestamp(d_str)
            days_diff = (event_ts - current_ts).days
            
            # 발표 전 N일 (신규 진입 제한)
            if 0 <= days_diff <= lookforward_days:
                return True, f"upcoming {event_name} in {days_diff} days"
            
            # 발표 당일 및 후속 여파 (고변동성)
            if -lookback_days <= days_diff < 0:
                return True, f"recent {event_name} fallout ({abs(days_diff)} days ago)"
                
    return False, ""
