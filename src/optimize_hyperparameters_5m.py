"""최적의 파라미터 조합을 찾기 위한 대규모 성과 비교 스크립트."""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from src.settings import load_settings, StrategySettings
from src.data_loader import load_price_data_batch
from src.portfolio_backtester import run_portfolio_backtest, build_ai_score_frames
from src.macro_loader import load_macro_data
from src.ml_model import load_ai_score_model


def _run(ticker_data, vix_df, macro_df, ai_score_frames, s: StrategySettings):
    res, _, _ = run_portfolio_backtest(
        ticker_data=ticker_data, initial_cash=10000.0,
        max_positions=s.max_total_positions, target_position_pct=s.max_position_pct,
        transaction_cost_pct=0.001, ma_fast=s.ma_fast, ma_slow=s.ma_slow,
        rsi_buy_limit=s.rsi_buy_limit, use_ai_score=s.use_ai_score,
        ai_score_buy_threshold=s.ai_score_buy_threshold,
        rank_trend_weight=getattr(s, "rank_trend_weight", 1.0),
        rank_ai_weight=getattr(s, "rank_ai_weight", 0.0),
        rank_momentum_weight=getattr(s, "rank_momentum_weight", 0.5),
        rank_volatility_weight=getattr(s, "rank_volatility_weight", 1.0),
        ai_exit_enabled=True, ai_exit_threshold=0.0, ai_exit_dynamic_enabled=True,
        ai_exit_threshold_bear=0.45, vix_df=vix_df, macro_df=macro_df,
        ai_score_frames=ai_score_frames,
    )
    return res


def main():
    base = load_settings()
    test_start = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=150)
    
    print(f"Loading data for 5-month optimization...")
    loaded = load_price_data_batch(list(base.tickers) + ["^VIX", "SPY"], period="2y")
    vix_all, spy_all, macro_all = loaded.get("^VIX"), loaded.get("SPY"), load_macro_data(period="2y")
    
    print(f"Calculating AI scores...")
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

    # 실험 군 정의
    configs = []
    
    # 1. ULTRA_AGGRESSIVE (33% * 3)
    c1 = load_settings(); c1.name = "ULTRA_AGGRESSIVE"
    c1.max_total_positions = 3; c1.max_position_pct = 0.33; c1.ai_score_buy_threshold = 0.40
    configs.append(c1)
    
    # 2. AI_CONVICTION (AI 중심 랭킹 + 집중투자)
    c2 = load_settings(); c2.name = "AI_CONVICTION"
    c2.rank_ai_weight = 1.5; c2.rank_trend_weight = 0.5
    c2.max_total_positions = 2; c2.max_position_pct = 0.50; c2.ai_score_buy_threshold = 0.48
    configs.append(c2)
    
    # 3. SMART_DIVERSIFIED (15% * 6)
    c3 = load_settings(); c3.name = "SMART_DIVERSIFIED"
    c3.max_total_positions = 6; c3.max_position_pct = 0.15; c3.ai_score_buy_threshold = 0.50
    configs.append(c3)
    
    # 4. MOMENTUM_MAX (AI는 거들뿐, 기술적 지표 중심)
    c4 = load_settings(); c4.name = "MOMENTUM_MAX"
    c4.rank_momentum_weight = 2.0; c4.rank_ai_weight = 0.2
    c4.max_total_positions = 4; c4.max_position_pct = 0.25; c4.ai_score_buy_threshold = 0.45
    configs.append(c4)

    results = []
    for c in configs:
        print(f"Testing {c.name}...")
        r = _run(test_data, test_vix, test_macro, test_scores, c)
        results.append({"name": c.name, "return": r.total_return, "mdd": r.max_drawdown, "sharpe": r.sharpe_ratio, "trades": r.trades})

    res_df = pd.DataFrame(results).sort_values("return", ascending=False)
    print("\n" + "=" * 80 + "\n5-MONTH HYPER-PARAMETER OPTIMIZATION RESULTS\n" + "=" * 80)
    print(res_df.to_string(index=False, formatters={'return': '{:+.2%}'.format, 'mdd': '{:+.2%}'.format, 'sharpe': '{:.3f}'.format}))
    
if __name__ == "__main__":
    main()
