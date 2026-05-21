import sys
import os
from pathlib import Path
import pandas as pd

# 프로젝트 루트를 sys.path에 추가하여 모듈을 임포트할 수 있게 함
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data_loader import load_price_data

def test_data_loader_structure():
    ticker = "AAPL"
    period = "5d"  # 테스트를 위해 짧은 기간 설정
    
    print(f"Testing data loading for {ticker} with period {period}...")
    
    # 1. 데이터 로드 실행
    df = load_price_data(ticker, period=period, force_refresh=True)
    
    # 2. 데이터프레임 검증 (adj_close 존재 여부)
    print(f"Checking columns: {df.columns.tolist()}")
    if "adj_close" in df.columns:
        print("✅ Success: 'adj_close' column exists.")
    else:
        print("❌ Failure: 'adj_close' column is missing.")
        return

    # 3. 파일 저장 경로 및 구조 검증
    # 예상 경로: data/raw/AAPL/5d.csv
    # 주의: load_price_data 내부의 _cache_path가 반환하는 값과 실제 저장 경로를 확인해야 함
    # 현재 구현상 _cache_path는 데이터 저장 파일의 'Full Path'를 반환하도록 수정함
    
    # 실제 저장된 파일 경로 찾기 (실제 구현된 _cache_path의 동작 방식에 따라 다름)
    # _cache_path(ticker, period)가 파일 경로를 반환한다고 가정할 때:
    expected_path = Path("data/raw") / ticker / f"{period}.csv"
    
    # 만약 _cache_path가 파일 경로를 직접 반환하도록 수정했다면:
    # (이 테스트는 load_price_data의 내부 구현에 의존함)
    import re
    from src.data_loader import _cache_path
    expected_path = _cache_path(ticker, period)
    
    print(f"Expected path: {expected_path}")
    
    if expected_path.exists():
        print(f"✅ Success: File exists at {expected_path}")
        # 데이터 로드 재시도 (캐시 확인용)
        df_cached = load_price_data(ticker, period=period, force_refresh=False)
        if not df_cached.empty:
            print("✅ Success: Cached data loaded correctly.")
        else:
            print("❌ Failure: Cached data is empty.")
    else:
        print(f"❌ Failure: File not found at {expected_path}")

if __name__ == "__main__":
    try:
        test_data_loader_structure()
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
