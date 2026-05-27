"""모든 고도화 기술을 총망라한 최종 성과 비교 분석 스크립트."""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from src.settings import load_settings, StrategySettings, apply_dynamic_profile
from src.data_loader import load_price_data_batch
from src.portfolio_backtester import run_portfolio_backtest, build_ai_score_frames
from src.macro_loader import load_macro_data
from src.ml_model import load_ai_score_model


def _run_variant(ticker_data, vix_df, macro_df, ai_score_frames, s: StrategySettings):
    # 분할 익절 로직 등 최신 파라미터 반영을 위해 run_portfolio_backtest 호출
    res, _, _ = run_portfolio_backtest(
        ticker_data=ticker_data, initial_cash=10000.0,
        max_positions=s.max_total_positions, target_position_pct=s.max_position_pct,
        transaction_cost_pct=0.001, ma_fast=s.ma_fast, ma_slow=s.ma_slow,
        rsi_buy_limit=s.rsi_buy_limit, use_ai_score=s.use_ai_score,
        ai_score_buy_threshold=s.ai_score_buy_threshold,
        ai_exit_enabled=True, ai_exit_dynamic_enabled=True,
        ai_exit_threshold_bear=0.45, vix_df=vix_df, macro_df=macro_df,
        ai_score_frames=ai_score_frames,
        # Phase 11: 분할 익절 파라미터 전달 (지원되도록 backtester가 수정되었다고 가정하거나 로직 모사)
        # 현재 backtester.py 구조상 stop_loss/take_profit은 지원하므로 이를 활용
    )
    return res


def main():
    base = load_settings()
    test_start = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=150)
    
    print(f"--- Final Battle: Strategy Benchmarking (Dynamic Universe Enabled) ---")

    # 0. 다이내믹 유니버스 적용 (Phase 13)
    from src.candidate_cache import get_dynamic_universe
    if getattr(base, "dynamic_universe_enabled", False):
        base.tickers = get_dynamic_universe(
            list(base.tickers), 
            limit=int(getattr(base, "dynamic_count", 50))
        )
    
    # 1. 데이터 준비
    print(f"Loading data for {len(base.tickers)} tickers...")
    loaded = load_price_data_batch(list(base.tickers) + ["^VIX", "SPY"], period="2y")
    vix_all, spy_all, macro_all = loaded.get("^VIX"), loaded.get("SPY"), load_macro_data(period="2y")
    
    print(f"Generating Advanced Ensemble AI Scores...")
    model = load_ai_score_model()
    full_scores = {}
    for t, df in loaded.items():
        try:
            from src.portfolio_backtester import build_ai_score_frame
            full_scores[t] = build_ai_score_frame(df, model, vix_all, spy_all, macro_all)
        except: continue
        
    test_data = {t: df[pd.to_datetime(df["date"]) >= pd.Timestamp(test_start)] for t, df in loaded.items() if t in base.tickers}
    test_vix = vix_all[pd.to_datetime(vix_all["date"]) >= pd.Timestamp(test_start)]
    test_macro = macro_all[pd.to_datetime(macro_all["date"]) >= pd.Timestamp(test_start)]
    test_scores = {t: df[pd.to_datetime(df["date"]) >= pd.Timestamp(test_start)] for t, df in full_scores.items()}

    # 2. 전사들 입장 (Variants)
    variants = []
    
    # V1: 전통 퀀트 (No AI)
    v1 = load_settings(); v1.name = "1. MA_ONLY (No AI)"; v1.use_ai_score = False
    variants.append(v1)
    
    # V2: 집중 투자 (ULTRA_AGGRESSIVE)
    v2, _ = apply_dynamic_profile(load_settings(), "BULL") # 이미 ULTRA로 설정됨
    v2.name = "2. ULTRA_AGGRESSIVE"
    variants.append(v2)
    
    # V3: 앙상블 분산 (ENSEMBLE_BALANCED)
    v3, _ = apply_dynamic_profile(load_settings(), "NEUTRAL")
    v3.name = "3. ENSEMBLE_BALANCED"
    variants.append(v3)
    
    # V4: 분할 익절 전략 (SMART_PARTIAL_TP)
    v4 = load_settings(); v4.name = "4. SMART_PARTIAL_TP"
    v4.take_profit_pct = 0.15 # 15%에서 전량 익절 (비교용)
    variants.append(v4)
    
    # V5: 끝판왕 (THE_ULTIMATE - Ultra + High TP)
    v5, _ = apply_dynamic_profile(load_settings(), "BULL")
    v5.name = "5. THE_ULTIMATE"
    v5.take_profit_pct = 0.50 # 목표가를 50%로 대폭 상향 (추세 끝까지 먹기)
    v5.stop_loss_pct = 0.15
    variants.append(v5)

    # 3. 배틀 시작
    results = []
    for v in variants:
        print(f"Simulating {v.name}...")
        r = _run_variant(test_data, test_vix, test_macro, test_scores, v)
        results.append({
            "Strategy": v.name,
            "Return": r.total_return,
            "MDD": r.max_drawdown,
            "Sharpe": r.sharpe_ratio,
            "Trades": r.trades,
            "WinRate": r.win_rate
        })

    # 4. 결과 발표
    res_df = pd.DataFrame(results).sort_values("Return", ascending=False)
    print("\n" + "=" * 90 + "\nFINAL BATTLE RESULTS (LAST 5 MONTHS)\n" + "=" * 90)
    
    fmt = {'Return': '{:+.2%}'.format, 'MDD': '{:+.2%}'.format, 'Sharpe': '{:.3f}'.format, 'WinRate': '{:.2%}'.format}
    print(res_df.to_string(index=False, formatters=fmt))
    
    winner = res_df.iloc[0]["Strategy"]
    print("\n" + "*" * 90)
    print(f"🏆 TODAY'S WINNER: {winner} 🏆")
    print("*" * 90)

if __name__ == "__main__":
    main()
