#!/usr/bin/env python3
"""시장 레짐 및 전략 프로필 재평가 배치 스크립트."""

import argparse
import json
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

from src.settings import load_settings, apply_dynamic_profile
from src.data_loader import load_price_data_batch
from src.market_regime import get_current_regime
from src.notifier import notify_info

STATE_PATH = Path("data/market_regime_state.json")
HISTORICAL_STATE_PATH = Path("data/market_regime_state_historical.json")

def reappraise_regime(current_date_str: str | None = None) -> None:
    print(f"--- Market Regime Re-appraisal Batch started at {datetime.now()} ---")
    
    is_historical = current_date_str is not None
    active_state_path = HISTORICAL_STATE_PATH if is_historical else STATE_PATH

    # 1. 이전 레짐 상태 로드
    old_regime = "UNKNOWN"
    if active_state_path.exists():
        try:
            state_data = json.loads(active_state_path.read_text(encoding="utf-8"))
            old_regime = state_data.get("regime", "UNKNOWN")
        except Exception as e:
            print(f"Warning: Failed to load previous regime state: {e}")

    # 2. 최신 SPY, VIX 데이터 로드
    tickers = ["SPY", "^VIX"]
    print(f"Fetching latest data for {tickers}...")
    try:
        ticker_data = load_price_data_batch(tickers, period="2y")
        spy_df = ticker_data.get("SPY")
        vix_df = ticker_data.get("^VIX")
    except Exception as e:
        print(f"Error: Failed to fetch market data: {e}")
        return

    if spy_df is None or spy_df.empty or vix_df is None or vix_df.empty:
        print("Error: Missing SPY or VIX data.")
        return

    # 특정 일자 기준 시뮬레이션용 데이터 필터링
    if current_date_str:
        try:
            target_dt = pd.to_datetime(current_date_str)
            spy_df = spy_df[pd.to_datetime(spy_df["date"]) <= target_dt]
            vix_df = vix_df[pd.to_datetime(vix_df["date"]) <= target_dt]
        except Exception as e:
            print(f"Error: Failed to filter data for date {current_date_str}: {e}")
            return

    # 3. 시장 레짐 결정
    new_regime = get_current_regime(spy_df, vix_df)
    print(f"Previous Regime: {old_regime}")
    print(f"New Evaluated Regime: {new_regime}")

    # 4. 동적 프로필 적용 확인
    settings = load_settings()
    _, profile_name = apply_dynamic_profile(settings, new_regime)
    print(f"Applied Profile: {profile_name}")

    # 5. 상태 파일 업데이트 (역사적/실시간 경로 구분 저장)
    try:
        active_state_path.parent.mkdir(parents=True, exist_ok=True)
        last_market_date = str(spy_df["date"].iloc[-1]) if "date" in spy_df.columns else datetime.now().date().isoformat()
        
        active_state_path.write_text(json.dumps({
            "regime": new_regime,
            "updated_at": datetime.now().isoformat(),
            "market_date": last_market_date,
            "is_historical": is_historical
        }, indent=2), encoding="utf-8")
        print(f"Saved market regime state to {active_state_path}")
    except Exception as e:
        print(f"Error: Failed to save market regime state: {e}")

    # 6. 레짐이 변경된 경우 알림 발송 (실시간 실행 시에만 발송)
    if not is_historical and old_regime != "UNKNOWN" and old_regime != new_regime:
        msg = (
            f"🔄 Market Regime Changed!\n"
            f"Previous: {old_regime}\n"
            f"Current: {new_regime}\n"
            f"Strategy Profile updated to: {profile_name}"
        )
        print(msg)
        try:
            notify_info("📢 Regime & Profile Updated", msg)
        except Exception as e:
            print(f"Warning: Failed to send notification: {e}")

def main() -> None:
    parser = argparse.ArgumentParser(description="Re-appraise market regime and update active strategy profile.")
    parser.add_argument("--date", help="Target date to evaluate (YYYY-MM-DD). Defaults to latest.")
    args = parser.parse_args()
    reappraise_regime(args.date)

if __name__ == "__main__":
    main()
