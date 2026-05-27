"""Walk-Forward Validation: 슬라이딩 윈도우 기반 연속 OOS 성능 검증."""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import pandas as pd
import numpy as np

from src.settings import load_settings
from src.data_loader import load_price_data_batch
from src.ml_model import train_ai_score_model
from src.portfolio_backtester import run_portfolio_backtest, build_ai_score_frames
from src.macro_loader import load_macro_data

# 설정
TRAIN_WINDOW_YEARS = 3
TEST_WINDOW_MONTHS = 6  # 검증 속도를 위해 6개월 단위로 설정 (원하면 1~3개월로 단축 가능)
TOTAL_YEARS = 5


def _filter_by_date(df: pd.DataFrame, start, end=None) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    d = df.copy()
    d["date"] = pd.to_datetime(d["date"])
    d = d[d["date"] >= pd.Timestamp(start)]
    if end:
        d = d[d["date"] < pd.Timestamp(end)]
    return d.reset_index(drop=True)


def main():
    settings = load_settings()
    output_dir = Path("logs/validation")
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== Walk-Forward Validation Started ===")
    print(f"Parameters: Train={TRAIN_WINDOW_YEARS}y, Test={TEST_WINDOW_MONTHS}m, Total={TOTAL_YEARS}y")

    # 1. 데이터 로딩
    print(f"Loading {len(settings.tickers)} tickers ({TOTAL_YEARS}y)...")
    tickers_to_load = list(settings.tickers) + ["^VIX", "SPY"]
    tickers_to_load = list(dict.fromkeys(tickers_to_load))
    loaded = load_price_data_batch(tickers_to_load, period=f"{TOTAL_YEARS}y")
    
    all_ticker_data = {t: loaded[t] for t in settings.tickers if t in loaded}
    vix_all = loaded.get("^VIX")
    spy_all = loaded.get("SPY")
    macro_all = load_macro_data(period=f"{TOTAL_YEARS}y")

    # 2. 검증 기간 생성 (6개월 단위 슬라이딩)
    end_date = pd.Timestamp(datetime.now(timezone.utc).date())
    start_date = end_date - pd.DateOffset(years=TOTAL_YEARS)
    
    folds = []
    current_test_start = start_date + pd.DateOffset(years=TRAIN_WINDOW_YEARS)
    
    while current_test_start + pd.DateOffset(months=TEST_WINDOW_MONTHS) <= end_date:
        test_end = current_test_start + pd.DateOffset(months=TEST_WINDOW_MONTHS)
        train_end = current_test_start
        train_start = train_end - pd.DateOffset(years=TRAIN_WINDOW_YEARS)
        
        folds.append({
            "train_start": train_start,
            "train_end": train_end,
            "test_start": current_test_start,
            "test_end": test_end
        })
        current_test_start = test_end

    print(f"Generated {len(folds)} validation folds.\n")

    results = []
    
    # 3. 각 Fold별 학습 및 검증
    for i, fold in enumerate(folds, 1):
        t_start, t_end = fold["test_start"], fold["test_end"]
        print(f"Fold {i}/{len(folds)}: Test Period {t_start.date()} ~ {t_end.date()}")

        # 데이터 필터링
        train_data = {t: _filter_by_date(df, fold["train_start"], fold["train_end"]) 
                      for t, df in all_ticker_data.items()}
        # 최소 데이터(1y+) 보유 종목만 학습 사용
        train_data = {t: df for t, df in train_data.items() if len(df) > 250}
        
        test_data = {t: _filter_by_date(df, fold["test_start"], fold["test_end"]) 
                     for t, df in all_ticker_data.items()}
        test_data = {t: df for t, df in test_data.items() if len(df) > 20}

        vix_train = _filter_by_date(vix_all, fold["train_start"], fold["train_end"])
        vix_test = _filter_by_date(vix_all, fold["test_start"], fold["test_end"])
        spy_train = _filter_by_date(spy_all, fold["train_start"], fold["train_end"])
        spy_test = _filter_by_date(spy_all, fold["test_start"], fold["test_end"])
        macro_train = _filter_by_date(macro_all, fold["train_start"], fold["train_end"])
        macro_test = _filter_by_date(macro_all, fold["test_start"], fold["test_end"])

        # 모델 학습
        print(f"  Training model...")
        model, _ = train_ai_score_model(
            training_data=train_data,
            prediction_horizon=20,
            vix_df=vix_train,
            spy_df=spy_train,
            macro_df=macro_train,
        )

        # AI 스코어 계산을 위한 데이터 준비 (피처 생성용 룩백 데이터 포함)
        lookback_start = fold["test_start"] - pd.DateOffset(days=400) # 넉넉하게 400일
        test_data_with_lookback = {t: _filter_by_date(df, lookback_start, fold["test_end"]) 
                                   for t, df in all_ticker_data.items()}
        test_data_with_lookback = {t: df for t, df in test_data_with_lookback.items() if len(df) > 272}

        vix_with_lookback = _filter_by_date(vix_all, lookback_start, fold["test_end"])
        spy_with_lookback = _filter_by_date(spy_all, lookback_start, fold["test_end"])
        macro_with_lookback = _filter_by_date(macro_all, lookback_start, fold["test_end"])

        # AI 스코어 계산
        print(f"  Calculating AI scores...")
        ai_score_frames_full = build_ai_score_frames(
            test_data_with_lookback, ai_model_bundle=model,
            vix_df=vix_with_lookback, spy_df=spy_with_lookback, macro_df=macro_with_lookback,
        )
        
        # 실제 테스트 기간만 필터링
        ai_score_frames = {t: _filter_by_date(df, fold["test_start"], fold["test_end"])
                           for t, df in ai_score_frames_full.items()}

        # 포트폴리오 백테스트
        print(f"  Running backtest...")
        result, _, _ = run_portfolio_backtest(
            ticker_data=test_data,
            initial_cash=10000.0,
            max_positions=settings.max_total_positions,
            target_position_pct=settings.max_position_pct,
            transaction_cost_pct=0.001,
            ma_fast=settings.ma_fast,
            ma_slow=settings.ma_slow,
            rsi_buy_limit=settings.rsi_buy_limit,
            use_ai_score=True,
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
            vix_df=vix_test,
            macro_df=macro_test,
            ai_score_frames=ai_score_frames,
        )
        
        metrics = {
            "period": f"{fold['test_start'].date()} ~ {fold['test_end'].date()}",
            "total_return": result.total_return,
            "max_drawdown": result.max_drawdown,
            "sharpe_ratio": result.sharpe_ratio,
            "trades": result.trades,
            "win_rate": result.win_rate
        }
        results.append(metrics)
        print(f"  Result: Return={metrics['total_return']*100:.2f}%, MDD={metrics['max_drawdown']*100:.2f}%, Sharpe={metrics['sharpe_ratio']:.3f}\n")

    # 4. 종합 결과 출력 및 저장
    res_df = pd.DataFrame(results)
    res_df.to_csv(output_dir / "walk_forward_results.csv", index=False)
    
    print("=" * 72)
    print("Walk-Forward Validation Summary")
    print("=" * 72)
    print(res_df.to_string(index=False))
    print("-" * 72)
    print(f"Average Return per Fold: {res_df['total_return'].mean()*100:.2f}%")
    print(f"Average MDD: {res_df['max_drawdown'].mean()*100:.2f}%")
    print(f"Average Sharpe: {res_df['sharpe_ratio'].mean():.3f}")
    print(f"Total Trades: {res_df['trades'].sum()}")
    print("=" * 72)
    print(f"\nFull results saved to {output_dir}/walk_forward_results.csv")


if __name__ == "__main__":
    main()
