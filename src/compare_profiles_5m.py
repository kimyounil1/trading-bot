"""5개월간의 다양한 전략 프로필 성과 비교 분석 스크립트."""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.settings import load_settings, apply_dynamic_profile, StrategySettings
from src.data_loader import load_price_data_batch
from src.portfolio_backtester import run_portfolio_backtest, build_ai_score_frames
from src.macro_loader import load_macro_data
from src.ml_model import load_ai_score_model


def _run_backtest_with_settings(ticker_data, vix_df, macro_df, ai_score_frames, settings):
    result, _, _ = run_portfolio_backtest(
        ticker_data=ticker_data,
        initial_cash=10000.0,
        max_positions=settings.max_total_positions,
        target_position_pct=settings.max_position_pct,
        transaction_cost_pct=0.001,
        ma_fast=settings.ma_fast,
        ma_slow=settings.ma_slow,
        rsi_buy_limit=settings.rsi_buy_limit,
        use_ai_score=settings.use_ai_score,
        ai_score_buy_threshold=settings.ai_score_buy_threshold,
        volume_filter_enabled=settings.volume_filter_enabled,
        volume_lookback_days=settings.volume_lookback_days,
        min_volume_ratio=settings.min_volume_ratio,
        rank_trend_weight=settings.rank_trend_weight,
        rank_ai_weight=settings.rank_ai_weight,
        rank_momentum_weight=settings.rank_momentum_weight,
        rank_volatility_weight=settings.rank_volatility_weight,
        ai_exit_enabled=getattr(settings, "ai_exit_enabled", True),
        ai_exit_threshold=getattr(settings, "ai_exit_threshold", 0.0),
        ai_exit_dynamic_enabled=getattr(settings, "ai_exit_dynamic_enabled", True),
        ai_exit_vix_low=getattr(settings, "ai_exit_vix_low", 0.0),
        ai_exit_vix_high=getattr(settings, "ai_exit_vix_high", 30.0),
        ai_exit_threshold_bull=getattr(settings, "ai_exit_threshold_bull", 0.0),
        ai_exit_threshold_bear=getattr(settings, "ai_exit_threshold_bear", 0.45),
        vix_df=vix_df,
        macro_df=macro_df,
        ai_score_frames=ai_score_frames,
    )
    return result


def main():
    base_settings = load_settings()
    days_back = 150  # 약 5개월
    # Timezone-naive datetime for pandas comparison fallback
    test_start = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days_back)
    
    print(f"=== 5-Month Strategy Comparison (Dynamic Universe Enabled) ===")
    print(f"Period: {test_start.date()} ~ Today")
    
    # 0. 다이내믹 유니버스 적용 (Phase 13)
    from src.candidate_cache import get_dynamic_universe
    if getattr(base_settings, "dynamic_universe_enabled", False):
        base_settings.tickers = get_dynamic_universe(
            list(base_settings.tickers), 
            limit=int(getattr(base_settings, "dynamic_count", 50))
        )

    # 1. 데이터 로딩
    print(f"Loading data for {len(base_settings.tickers)} tickers...")
    tickers_to_load = list(base_settings.tickers) + ["^VIX", "SPY"]
    tickers_to_load = list(dict.fromkeys(tickers_to_load))
    loaded = load_price_data_batch(tickers_to_load, period="2y") # AI 피처용 넉넉한 기간
    
    vix_all = loaded.get("^VIX")
    spy_all = loaded.get("SPY")
    macro_all = load_macro_data(period="2y")
    
    # AI 스코어 미리 계산
    print(f"Calculating AI scores for all tickers...")
    model = load_ai_score_model()
    
    full_ai_score_frames = {}
    for ticker, df in loaded.items():
        try:
            from src.portfolio_backtester import build_ai_score_frame
            full_ai_score_frames[ticker] = build_ai_score_frame(
                df, ai_model_bundle=model,
                vix_df=vix_all, spy_df=spy_all, macro_df=macro_all
            )
        except Exception:
            # 데이터 부족 등으로 스코어 계산 실패 시 스킵
            continue
    
    # 테스트 기간 필터링
    test_ticker_data = {t: df[pd.to_datetime(df["date"]) >= pd.Timestamp(test_start)] 
                        for t, df in loaded.items() if t in base_settings.tickers}
    test_vix = vix_all[pd.to_datetime(vix_all["date"]) >= pd.Timestamp(test_start)]
    test_macro = macro_all[pd.to_datetime(macro_all["date"]) >= pd.Timestamp(test_start)]
    test_ai_score_frames = {t: df[pd.to_datetime(df["date"]) >= pd.Timestamp(test_start)] 
                           for t, df in full_ai_score_frames.items()}

    # 2. 비교 대상 정의
    variants = []
    
    # A. Baseline (No AI)
    v_nai = load_settings()
    v_nai.use_ai_score = False
    v_nai.name = "MA_ONLY (No AI)"
    variants.append(v_nai)
    
    # B. Static Balanced (기존 보수적 세팅)
    v_bal = load_settings()
    v_bal.name = "STATIC_BALANCED"
    variants.append(v_bal)
    
    # C. Forced Aggressive (공격형 고정)
    v_agg, _ = apply_dynamic_profile(load_settings(), "BULL", profiles_path="config/strategy_profiles.json")
    v_agg.name = "FORCED_AGGRESSIVE"
    variants.append(v_agg)
    
    # D. Forced Defensive (방어형 고정)
    v_def, _ = apply_dynamic_profile(load_settings(), "BEAR", profiles_path="config/strategy_profiles.json")
    v_def.name = "FORCED_DEFENSIVE"
    variants.append(v_def)

    # 3. 백테스트 실행
    print(f"\nRunning {len(variants)} backtests...\n")
    results = []
    for v in variants:
        print(f"  Testing {v.name}...", end=" ", flush=True)
        res = _run_backtest_with_settings(test_ticker_data, test_vix, test_macro, test_ai_score_frames, v)
        results.append({
            "name": v.name,
            "return": res.total_return,
            "mdd": res.max_drawdown,
            "sharpe": res.sharpe_ratio,
            "trades": res.trades,
            "win_rate": res.win_rate
        })
        print("done")

    # 4. 결과 출력
    res_df = pd.DataFrame(results)
    print("\n" + "=" * 80)
    print(f"Performance Comparison (Last {days_back} Days)")
    print("=" * 80)
    
    # 포맷팅
    display_df = res_df.copy()
    display_df["return"] = display_df["return"].apply(lambda x: f"{x*100:+.2f}%")
    display_df["mdd"] = display_df["mdd"].apply(lambda x: f"{x*100:.2f}%")
    display_df["win_rate"] = display_df["win_rate"].apply(lambda x: f"{x*100:.2f}%")
    display_df["sharpe"] = display_df["sharpe"].apply(lambda x: f"{x:.3f}")
    
    print(display_df.to_string(index=False))
    print("=" * 80)

if __name__ == "__main__":
    main()
