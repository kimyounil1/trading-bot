"""Walk-forward out-of-sample validation.

Splits 5y data into:
  train : years 0-3  (in-sample)
  test  : years 3-5  (out-of-sample — model never sees this during training)

Trains a fresh model on train period only, then backtests on test period.
Compares:
  A. Full-data model  (trained on all 5y)  → backtest on test 2y
  B. Split model      (trained on first 3y) → backtest on same test 2y

If A ≈ B → not overfitting, patterns are real.
If A >> B → overfitting concern.
"""

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import shutil
import tempfile

from src.settings import load_settings
from src.data_loader import load_price_data_batch
from src.ml_model import train_ai_score_model, load_ai_score_model, MODEL_PATH
from src.portfolio_backtester import run_portfolio_backtest, build_ai_score_frames
from src.macro_loader import load_macro_data


TRAIN_YEARS = 3
TEST_YEARS = 2
TOTAL_YEARS = TRAIN_YEARS + TEST_YEARS


def pct(v: float) -> str:
    return f"{v * 100:.2f}%"


def _filter_by_date(df: pd.DataFrame, start=None, end=None) -> pd.DataFrame:
    d = df.copy()
    d["date"] = pd.to_datetime(d["date"])
    if start:
        d = d[d["date"] >= pd.Timestamp(start)]
    if end:
        d = d[d["date"] < pd.Timestamp(end)]
    return d.reset_index(drop=True)


def _run_backtest(ticker_data, vix_df, macro_df, ai_score_frames, settings):
    result, _, trades_df = run_portfolio_backtest(
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
        ai_exit_threshold=getattr(settings, "ai_exit_threshold", 0.35),
        ai_exit_dynamic_enabled=getattr(settings, "ai_exit_dynamic_enabled", False),
        ai_exit_vix_low=getattr(settings, "ai_exit_vix_low", 15.0),
        ai_exit_vix_high=getattr(settings, "ai_exit_vix_high", 25.0),
        ai_exit_threshold_bull=getattr(settings, "ai_exit_threshold_bull", 0.55),
        ai_exit_threshold_bear=getattr(settings, "ai_exit_threshold_bear", 0.28),
        vix_df=vix_df,
        macro_df=macro_df,
        ai_score_frames=ai_score_frames,
    )
    return result


def main() -> None:
    settings = load_settings()

    today = datetime.now(timezone.utc).date()
    test_start = pd.Timestamp(today) - pd.DateOffset(years=TEST_YEARS)
    train_end = test_start
    train_start = test_start - pd.DateOffset(years=TRAIN_YEARS)

    print(f"Train period: {train_start.date()} ~ {train_end.date()}")
    print(f"Test  period: {test_start.date()} ~ {today}")
    print()

    # ── 데이터 로딩 ────────────────────────────────────────────────
    print(f"Loading {len(settings.tickers)} tickers ({TOTAL_YEARS}y)...")
    tickers_to_load = list(settings.tickers) + ["^VIX"]
    tickers_to_load = list(dict.fromkeys(tickers_to_load))
    loaded = load_price_data_batch(tickers_to_load, period=f"{TOTAL_YEARS}y")
    all_ticker_data = {t: loaded[t] for t in settings.tickers if t in loaded}
    vix_all = loaded.get("^VIX")
    macro_all = load_macro_data(period=f"{TOTAL_YEARS}y")
    print(f"Loaded {len(all_ticker_data)} tickers\n")

    # ── 기간 분할 ──────────────────────────────────────────────────
    train_data = {t: _filter_by_date(df, train_start, train_end)
                  for t, df in all_ticker_data.items()}
    train_data = {t: df for t, df in train_data.items() if len(df) > 300}

    test_data = {t: _filter_by_date(df, test_start)
                 for t, df in all_ticker_data.items()}
    test_data = {t: df for t, df in test_data.items() if len(df) > 50}

    vix_train = _filter_by_date(vix_all, train_start, train_end) if vix_all is not None else None
    vix_test = _filter_by_date(vix_all, test_start) if vix_all is not None else None
    macro_train = _filter_by_date(macro_all, train_start, train_end) if not macro_all.empty else None
    macro_test = _filter_by_date(macro_all, test_start) if not macro_all.empty else None

    print(f"Train tickers: {len(train_data)}, Test tickers: {len(test_data)}")

    # ── 현재 모델 (full 5y) — train 전에 백업 ───────────────────
    print("[B] 현재 모델 백업 중...")
    with tempfile.NamedTemporaryFile(suffix=".joblib", delete=False) as tmp:
        backup_path = tmp.name
    shutil.copy2(MODEL_PATH, backup_path)

    # ── 검증 모델 학습 (train 기간만) ──────────────────────────────
    print(f"\n[A] 검증 모델 학습 (train {TRAIN_YEARS}y only)...")
    spy_train = train_data.get("SPY")
    val_model, val_metrics = train_ai_score_model(
        training_data=train_data,
        prediction_horizon=20,
        target_return_threshold=0.0,
        vix_df=vix_train,
        spy_df=spy_train,
        macro_df=macro_train,
    )
    avg_auc_val = val_metrics["roc_auc"].mean()
    print(f"   검증 모델 avg ROC-AUC: {avg_auc_val:.4f}")

    # ── 현재 모델 (full 5y) — 백업에서 복원 ────────────────────
    print("[B] 현재 모델 로드 (full 5y)...")
    shutil.copy2(backup_path, MODEL_PATH)
    full_model = load_ai_score_model()
    import os; os.unlink(backup_path)

    # ── 테스트 기간 백테스트 ───────────────────────────────────────
    print("\nRunning backtests on test period...\n")

    # No AI (MA baseline)
    print("  MA only (no AI)...", end=" ", flush=True)
    result_nai, _, _ = run_portfolio_backtest(
        ticker_data=test_data,
        initial_cash=10000.0,
        max_positions=settings.max_total_positions,
        target_position_pct=settings.max_position_pct,
        transaction_cost_pct=0.001,
        ma_fast=settings.ma_fast,
        ma_slow=settings.ma_slow,
        rsi_buy_limit=settings.rsi_buy_limit,
        use_ai_score=False,
        volume_filter_enabled=settings.volume_filter_enabled,
        volume_lookback_days=settings.volume_lookback_days,
        min_volume_ratio=settings.min_volume_ratio,
        rank_trend_weight=settings.rank_trend_weight,
        rank_momentum_weight=settings.rank_momentum_weight,
        rank_volatility_weight=settings.rank_volatility_weight,
        vix_df=vix_test,
        macro_df=macro_test,
    )
    print("done")

    # AI score frames for validation model
    print("  [A] 검증 모델 AI scores 계산...", end=" ", flush=True)
    spy_test = test_data.get("SPY")
    val_score_frames = build_ai_score_frames(
        test_data, ai_model_bundle=val_model,
        vix_df=vix_test, spy_df=spy_test, macro_df=macro_test,
    )
    print("done")

    print("  [A] 검증 모델 백테스트...", end=" ", flush=True)
    result_val = _run_backtest(test_data, vix_test, macro_test, val_score_frames, settings)
    print("done")

    # AI score frames for full model
    print("  [B] 현재 모델 AI scores 계산...", end=" ", flush=True)
    full_score_frames = build_ai_score_frames(
        test_data, ai_model_bundle=full_model,
        vix_df=vix_test, spy_df=spy_test, macro_df=macro_test,
    )
    print("done")

    print("  [B] 현재 모델 백테스트...", end=" ", flush=True)
    result_full = _run_backtest(test_data, vix_test, macro_test, full_score_frames, settings)
    print("done")

    # ── 결과 출력 ──────────────────────────────────────────────────
    print()
    print("=" * 72)
    print(f"Out-of-Sample Validation  |  Test period: {test_start.date()} ~ {today}")
    print("=" * 72)
    print(f"{'':30} {'MA only':>10} {'검증모델(A)':>12} {'현재모델(B)':>12}")
    print("-" * 72)

    for label, val, field in [
        ("total_return",    [result_nai, result_val, result_full], "total_return"),
        ("max_drawdown",    [result_nai, result_val, result_full], "max_drawdown"),
        ("sharpe_ratio",    [result_nai, result_val, result_full], "sharpe_ratio"),
        ("trades",          [result_nai, result_val, result_full], "trades"),
        ("win_rate",        [result_nai, result_val, result_full], "win_rate"),
    ]:
        vals = [getattr(r, field) for r in [result_nai, result_val, result_full]]
        if field in ("total_return", "max_drawdown", "win_rate"):
            row = "  ".join(f"{v*100:>10.2f}%" for v in vals)
        elif field == "sharpe_ratio":
            row = "  ".join(f"{v:>10.3f} " for v in vals)
        else:
            row = "  ".join(f"{v:>11}" for v in vals)
        print(f"{label:<30} {row}")

    print("=" * 72)
    gap = result_full.total_return - result_val.total_return
    print(f"\n과적합 갭 (현재모델 - 검증모델): {gap*100:+.2f}%p")
    if abs(gap) < 0.10:
        print("→ 갭 작음: 실제 패턴 학습, 과적합 위험 낮음 ✅")
    elif gap > 0.20:
        print("→ 갭 큼: 현재 모델이 최근 데이터에 과적합됐을 가능성 있음 ⚠️")
    else:
        print("→ 갭 보통: 일부 과적합 가능성 있으나 허용 범위")

    # 결과 저장
    output_dir = Path("logs/validation")
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = [
        {"model": "MA_only",     **{f: getattr(result_nai,  f) for f in ["total_return","max_drawdown","sharpe_ratio","trades","win_rate"]}},
        {"model": "val_model_A", **{f: getattr(result_val,  f) for f in ["total_return","max_drawdown","sharpe_ratio","trades","win_rate"]}},
        {"model": "full_model_B",**{f: getattr(result_full, f) for f in ["total_return","max_drawdown","sharpe_ratio","trades","win_rate"]}},
    ]
    pd.DataFrame(rows).to_csv(output_dir / "oos_validation.csv", index=False)
    print(f"\nSaved to {output_dir}/oos_validation.csv")


if __name__ == "__main__":
    main()
