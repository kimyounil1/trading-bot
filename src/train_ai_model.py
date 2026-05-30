import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.features import build_features
from src.settings import load_settings, save_settings
from src.data_loader import load_price_data_batch
from src.ml_model import (
    CHAMPION_ARCHIVE_DIR,
    FEATURE_COLUMNS,
    MODEL_METADATA_PATH,
    MODEL_PATH,
    archive_current_champion,
    build_model_bundle,
    build_promotion_report,
    bundle_to_model_wrapper,
    find_latest_archived_champion,
    load_ai_score_model,
    load_model_metadata,
    restore_archived_champion,
    save_challenger_bundle,
    save_model_bundle,
    train_ai_score_model,
)
from src.macro_loader import load_macro_data
from src.ml_quality_report import (
    CALIBRATION_BINS_FILENAME,
    CALIBRATION_REPORT_FILENAME,
    DEFAULT_ML_OUTPUT_DIR,
    write_ml_quality_reports,
)
from src.retrain_holdout import (
    exclude_holdout_from_ticker_data,
    portfolio_holdout_window,
    slice_ticker_data_to_holdout,
)
from src.notifier import notify_info
from src.portfolio_backtester import (
    PortfolioBacktestResult,
    build_ai_score_frames,
    run_portfolio_backtest,
)

VIX_TICKER = "^VIX"
RETRAIN_LOG_PATH = Path("logs/retrain_history.csv")
ROLLBACK_REPORT_PATH = Path("logs/ml/model_rollback_report.json")
from src.model_governance import (
    evaluate_rollback_need as _evaluate_rollback_need,
    load_recent_performance_snapshot as _load_recent_performance_snapshot,
    resolve_rollback_decision,
)

FEATURE_STATS_PATH = Path("models/ai_feature_stats.json")
DRIFT_REPORT_PATH = Path("logs/ml/feature_drift_report.json")
CALIBRATION_REPORT_PATH = DEFAULT_ML_OUTPUT_DIR / CALIBRATION_REPORT_FILENAME
CALIBRATION_BINS_PATH = DEFAULT_ML_OUTPUT_DIR / CALIBRATION_BINS_FILENAME
THRESHOLD_RETUNE_REPORT_PATH = Path("logs/ml/threshold_retune_report.json")
THRESHOLD_RETUNE_RESULTS_PATH = Path("logs/ml/threshold_retune_results.csv")
DRIFT_ZSCORE_ALERT_THRESHOLD = 1.5
BUY_THRESHOLD_GRID = [0.40, 0.45, 0.50, 0.55, 0.60]
EXIT_THRESHOLD_GRID = [0.20, 0.25, 0.30, 0.35, 0.40, 0.45]


def _append_retrain_log(status: str, metrics_df, elapsed_sec: float) -> None:
    RETRAIN_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_header = not RETRAIN_LOG_PATH.exists()

    avg_roc = 0.0
    avg_precision = 0.0
    if metrics_df is not None and not metrics_df.empty:
        if "roc_auc" in metrics_df.columns:
            avg_roc = float(metrics_df["roc_auc"].mean())
        # precision이 metrics_df에 없으면 0.0으로 유지 (regime별 CV에서 누락 가능)
        if "precision" in metrics_df.columns:
            avg_precision = float(metrics_df["precision"].mean())

    # ROC-AUC 성능 저하 알림 (평균치 기준)
    if avg_roc < 0.51 and status == "success":
        notify_info(
            "⚠️ AI Model Performance Degradation (Regime-Aware)",
            f"Average ROC-AUC across regimes: {avg_roc:.4f}\n"
            f"Retraining completed, but overall model quality may be low."
        )

    row = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": status,
        "avg_roc_auc": round(avg_roc, 4),
        "avg_precision": round(avg_precision, 4),
        "elapsed_sec": round(elapsed_sec, 1),
    }

    with RETRAIN_LOG_PATH.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def _write_rollback_report(payload: dict) -> None:
    ROLLBACK_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ROLLBACK_REPORT_PATH.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _build_feature_stats(
    training_data: dict[str, pd.DataFrame],
    *,
    prediction_horizon: int,
    target_return_threshold: float,
    vix_df: pd.DataFrame | None,
    spy_df: pd.DataFrame | None,
    macro_df: pd.DataFrame | None,
) -> dict:
    frames = []
    for ticker, df in training_data.items():
        try:
            feature_df = build_features(
                df,
                prediction_horizon=prediction_horizon,
                target_return_threshold=target_return_threshold,
                vix_df=vix_df,
                spy_df=spy_df,
                macro_df=macro_df,
            )
        except ValueError:
            continue
        frames.append(feature_df[FEATURE_COLUMNS])

    if not frames:
        return {
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "feature_stats": {},
        }

    dataset = pd.concat(frames, ignore_index=True)
    stats = {}
    for column in FEATURE_COLUMNS:
        series = pd.to_numeric(dataset[column], errors="coerce").dropna()
        if series.empty:
            continue
        stats[column] = {
            "mean": float(series.mean()),
            "std": float(series.std(ddof=0)),
            "p10": float(series.quantile(0.10)),
            "p50": float(series.quantile(0.50)),
            "p90": float(series.quantile(0.90)),
            "count": int(series.count()),
        }

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "feature_stats": stats,
    }


def _load_feature_stats(path: Path = FEATURE_STATS_PATH) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _compare_feature_stats(
    baseline: dict | None,
    current: dict,
    *,
    zscore_threshold: float = DRIFT_ZSCORE_ALERT_THRESHOLD,
) -> dict:
    baseline_stats = (baseline or {}).get("feature_stats", {})
    current_stats = current.get("feature_stats", {})
    drifted_features = []

    for feature, current_values in current_stats.items():
        base_values = baseline_stats.get(feature)
        if not base_values:
            continue
        baseline_std = abs(float(base_values.get("std", 0.0)))
        if baseline_std <= 1e-12:
            continue
        zscore = abs(float(current_values["mean"]) - float(base_values["mean"])) / baseline_std
        if zscore >= zscore_threshold:
            drifted_features.append(
                {
                    "feature": feature,
                    "baseline_mean": float(base_values["mean"]),
                    "current_mean": float(current_values["mean"]),
                    "baseline_std": baseline_std,
                    "zscore_shift": float(zscore),
                }
            )

    drifted_features.sort(key=lambda item: item["zscore_shift"], reverse=True)
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "baseline_generated_at": None if baseline is None else baseline.get("generated_at"),
        "current_generated_at": current.get("generated_at"),
        "zscore_alert_threshold": zscore_threshold,
        "drifted_feature_count": len(drifted_features),
        "drifted_features": drifted_features,
    }


def _write_feature_stats(stats: dict, path: Path = FEATURE_STATS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(stats, indent=2, sort_keys=True), encoding="utf-8")


def _write_drift_report(report: dict, path: Path = DRIFT_REPORT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _pick_latest_date(ticker_data: dict[str, pd.DataFrame]) -> pd.Timestamp:
    latest_dates = []
    for df in ticker_data.values():
        if df is None or df.empty or "date" not in df.columns:
            continue
        series = pd.to_datetime(df["date"], errors="coerce").dropna()
        if not series.empty:
            latest_dates.append(series.max())
    if not latest_dates:
        raise ValueError("No valid dates found in ticker_data")
    return max(latest_dates)


def _score_threshold_row(row: dict) -> tuple[float, float, float, float]:
    return (
        float(row["sharpe_ratio"]),
        float(row["total_return"]),
        -abs(float(row["max_drawdown"])),
        float(row["win_rate"]),
    )


def _portfolio_oos_snapshot(
    result: PortfolioBacktestResult,
    eval_start: pd.Timestamp,
    eval_end: pd.Timestamp,
) -> dict:
    return {
        "evaluation_start": eval_start.strftime("%Y-%m-%d"),
        "evaluation_end": eval_end.strftime("%Y-%m-%d"),
        "total_return": float(result.total_return),
        "benchmark_return": float(result.benchmark_return),
        "max_drawdown": float(result.max_drawdown),
        "sharpe_ratio": float(result.sharpe_ratio),
        "trades": int(result.trades),
        "win_rate": float(result.win_rate),
    }


def _run_retrain_oos_portfolio(
    *,
    settings,
    ticker_data: dict[str, pd.DataFrame],
    vix_df: pd.DataFrame | None,
    macro_df: pd.DataFrame | None,
    model_wrapper,
    eval_start: pd.Timestamp,
    eval_end: pd.Timestamp,
) -> dict:
    """Portfolio backtest on holdout-only price data for model promotion."""
    benchmark_df = (
        ticker_data.get(settings.market_regime_ticker)
        if settings.market_regime_filter_enabled
        else None
    )
    relative_strength_benchmark_df = (
        ticker_data.get(settings.relative_strength_benchmark_ticker)
        if settings.relative_strength_filter_enabled
        else None
    )
    spy_df = ticker_data.get("SPY")

    ai_score_frames = None
    if settings.use_ai_score:
        ai_score_frames = build_ai_score_frames(
            ticker_data,
            ai_model_bundle=model_wrapper,
            vix_df=vix_df,
            spy_df=spy_df,
            macro_df=macro_df,
        )

    result, _, _ = run_portfolio_backtest(
        ticker_data=ticker_data,
        benchmark_df=benchmark_df,
        relative_strength_benchmark_df=relative_strength_benchmark_df,
        initial_cash=10000.0,
        max_positions=settings.max_total_positions,
        target_position_pct=settings.max_position_pct,
        transaction_cost_pct=0.001,
        ma_fast=settings.ma_fast,
        ma_slow=settings.ma_slow,
        rsi_buy_limit=settings.rsi_buy_limit,
        use_ai_score=settings.use_ai_score,
        ai_score_buy_threshold=settings.ai_score_buy_threshold,
        market_regime_filter_enabled=settings.market_regime_filter_enabled,
        market_regime_ma_fast=settings.market_regime_ma_fast,
        market_regime_ma_slow=settings.market_regime_ma_slow,
        relative_strength_filter_enabled=settings.relative_strength_filter_enabled,
        relative_strength_lookback_days=settings.relative_strength_lookback_days,
        relative_strength_min_excess_return=settings.relative_strength_min_excess_return,
        volume_filter_enabled=settings.volume_filter_enabled,
        volume_lookback_days=settings.volume_lookback_days,
        min_volume_ratio=settings.min_volume_ratio,
        volatility_filter_enabled=settings.volatility_filter_enabled,
        volatility_lookback_days=settings.volatility_lookback_days,
        max_volatility=settings.max_volatility,
        rank_trend_weight=settings.rank_trend_weight,
        rank_ai_weight=settings.rank_ai_weight,
        rank_momentum_weight=settings.rank_momentum_weight,
        rank_volatility_weight=settings.rank_volatility_weight,
        stop_loss_pct=settings.stop_loss_pct,
        take_profit_pct=settings.take_profit_pct,
        trailing_stop_pct=settings.trailing_stop_pct,
        allocation_method=settings.allocation_method,
        ai_exit_enabled=getattr(settings, "ai_exit_enabled", False),
        ai_exit_threshold=(
            settings.ai_exit_threshold_bear
            if getattr(settings, "ai_exit_dynamic_enabled", False)
            else settings.ai_exit_threshold
        ),
        ai_exit_dynamic_enabled=getattr(settings, "ai_exit_dynamic_enabled", False),
        ai_exit_vix_low=getattr(settings, "ai_exit_vix_low", 15.0),
        ai_exit_vix_high=getattr(settings, "ai_exit_vix_high", 25.0),
        ai_exit_threshold_bull=getattr(settings, "ai_exit_threshold_bull", 0.22),
        ai_exit_threshold_bear=getattr(settings, "ai_exit_threshold_bear", 0.50),
        vix_df=vix_df,
        macro_df=macro_df,
        ai_score_frames=ai_score_frames,
        evaluation_start_date=eval_start,
        evaluation_end_date=eval_end,
    )
    return _portfolio_oos_snapshot(result, eval_start, eval_end)


def _load_champion_model_wrapper():
    if not MODEL_PATH.exists():
        return None
    try:
        return load_ai_score_model()
    except (FileNotFoundError, ValueError):
        return None


def _run_threshold_retune(
    settings,
    ticker_data: dict[str, pd.DataFrame],
    vix_df: pd.DataFrame | None,
    macro_df: pd.DataFrame | None,
) -> tuple[dict, pd.DataFrame]:
    benchmark_df = (
        ticker_data.get(settings.market_regime_ticker)
        if settings.market_regime_filter_enabled
        else None
    )
    relative_strength_benchmark_df = (
        ticker_data.get(settings.relative_strength_benchmark_ticker)
        if settings.relative_strength_filter_enabled
        else None
    )

    eval_end = _pick_latest_date(ticker_data)
    eval_start = eval_end - pd.DateOffset(months=6)

    rows = []
    for buy_threshold in BUY_THRESHOLD_GRID:
        for exit_threshold in EXIT_THRESHOLD_GRID:
            result, _, _ = run_portfolio_backtest(
                ticker_data=ticker_data,
                benchmark_df=benchmark_df,
                relative_strength_benchmark_df=relative_strength_benchmark_df,
                initial_cash=10000.0,
                max_positions=settings.max_total_positions,
                target_position_pct=settings.max_position_pct,
                transaction_cost_pct=0.001,
                ma_fast=settings.ma_fast,
                ma_slow=settings.ma_slow,
                rsi_buy_limit=settings.rsi_buy_limit,
                use_ai_score=settings.use_ai_score,
                ai_score_buy_threshold=buy_threshold,
                market_regime_filter_enabled=settings.market_regime_filter_enabled,
                market_regime_ma_fast=settings.market_regime_ma_fast,
                market_regime_ma_slow=settings.market_regime_ma_slow,
                relative_strength_filter_enabled=settings.relative_strength_filter_enabled,
                relative_strength_lookback_days=settings.relative_strength_lookback_days,
                relative_strength_min_excess_return=settings.relative_strength_min_excess_return,
                volume_filter_enabled=settings.volume_filter_enabled,
                volume_lookback_days=settings.volume_lookback_days,
                min_volume_ratio=settings.min_volume_ratio,
                volatility_filter_enabled=settings.volatility_filter_enabled,
                volatility_lookback_days=settings.volatility_lookback_days,
                max_volatility=settings.max_volatility,
                rank_trend_weight=settings.rank_trend_weight,
                rank_ai_weight=settings.rank_ai_weight,
                rank_momentum_weight=settings.rank_momentum_weight,
        rank_volatility_weight=settings.rank_volatility_weight,
        stop_loss_pct=settings.stop_loss_pct,
        take_profit_pct=settings.take_profit_pct,
        trailing_stop_pct=settings.trailing_stop_pct,
        allocation_method=settings.allocation_method,
        ai_exit_enabled=getattr(settings, "ai_exit_enabled", False),
        ai_exit_threshold=exit_threshold,
        ai_exit_dynamic_enabled=getattr(settings, "ai_exit_dynamic_enabled", False),
        ai_exit_vix_low=getattr(settings, "ai_exit_vix_low", 15.0),
        ai_exit_vix_high=getattr(settings, "ai_exit_vix_high", 25.0),
        ai_exit_threshold_bull=getattr(settings, "ai_exit_threshold_bull", 0.22),
        ai_exit_threshold_bear=exit_threshold if getattr(settings, "ai_exit_dynamic_enabled", False) else getattr(settings, "ai_exit_threshold_bear", 0.50),
        vix_df=vix_df,
        macro_df=macro_df,
        evaluation_start_date=eval_start,
        evaluation_end_date=eval_end,
    )
            rows.append(
                {
                    "buy_threshold": buy_threshold,
                    "exit_threshold": exit_threshold,
                    "evaluation_start": eval_start.strftime("%Y-%m-%d"),
                    "evaluation_end": eval_end.strftime("%Y-%m-%d"),
                    "total_return": result.total_return,
                    "max_drawdown": result.max_drawdown,
                    "win_rate": result.win_rate,
                    "trades": result.trades,
                    "sharpe_ratio": result.sharpe_ratio,
                }
            )

    results_df = pd.DataFrame(rows)
    best_row = max(rows, key=_score_threshold_row)
    report = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "evaluation_start": best_row["evaluation_start"],
        "evaluation_end": best_row["evaluation_end"],
        "buy_threshold_grid": BUY_THRESHOLD_GRID,
        "exit_threshold_grid": EXIT_THRESHOLD_GRID,
        "best_buy_threshold": best_row["buy_threshold"],
        "best_exit_threshold": best_row["exit_threshold"],
        "best_total_return": best_row["total_return"],
        "best_max_drawdown": best_row["max_drawdown"],
        "best_win_rate": best_row["win_rate"],
        "best_sharpe_ratio": best_row["sharpe_ratio"],
    }
    return report, results_df


def _write_threshold_retune_report(report: dict, results_df: pd.DataFrame) -> None:
    THRESHOLD_RETUNE_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    THRESHOLD_RETUNE_REPORT_PATH.write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    results_df.to_csv(THRESHOLD_RETUNE_RESULTS_PATH, index=False)


def main() -> None:
    import time
    started_at = time.time()

    settings = load_settings()

    print(f"[retrain] started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Loading {len(settings.tickers)} tickers (5y)...")
    training_data = load_price_data_batch(settings.tickers, period="5y")

    print("Loading VIX and SPY context data...")
    context_tickers = [VIX_TICKER]
    if "SPY" not in training_data:
        context_tickers.append("SPY")
    context_data = load_price_data_batch(context_tickers, period="5y")

    vix_df = context_data.get(VIX_TICKER)
    spy_df = training_data.get("SPY") if "SPY" in training_data else context_data.get("SPY")

    print("Loading macro context data (yield, dollar, gold)...")
    macro_df = load_macro_data(period="5y")
    if macro_df.empty:
        print("  WARNING: macro data unavailable, training without macro features")
        macro_df = None
    else:
        print(f"  Macro data: {len(macro_df)} rows, columns: {list(macro_df.columns)}")

    holdout_start, holdout_end = portfolio_holdout_window(training_data)
    training_data_fit = exclude_holdout_from_ticker_data(training_data, holdout_start)
    holdout_ticker_data = slice_ticker_data_to_holdout(
        training_data, holdout_start, holdout_end
    )
    print(
        f"Portfolio promotion holdout: {holdout_start.strftime('%Y-%m-%d')} "
        f"to {holdout_end.strftime('%Y-%m-%d')} (excluded from challenger training)"
    )

    print("Training model with LightGBM + enhanced features (21 features)...")
    model, metrics_df = train_ai_score_model(
        training_data=training_data_fit,
        prediction_horizon=20,
        target_return_threshold=0.0,
        vix_df=vix_df,
        spy_df=spy_df,
        macro_df=macro_df,
    )

    baseline_feature_stats = _load_feature_stats()
    current_feature_stats = _build_feature_stats(
        training_data=training_data,
        prediction_horizon=20,
        target_return_threshold=0.0,
        vix_df=vix_df,
        spy_df=spy_df,
        macro_df=macro_df,
    )
    output_dir = DEFAULT_ML_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    drift_report = _compare_feature_stats(baseline_feature_stats, current_feature_stats)
    _write_drift_report(drift_report)
    _write_feature_stats(current_feature_stats)
    quality_paths = write_ml_quality_reports(output_dir, metrics_df)
    calibration_report = json.loads(
        quality_paths["calibration_report"].read_text(encoding="utf-8")
    )
    stability_report = json.loads(
        quality_paths["fold_stability"].read_text(encoding="utf-8")
    )

    if drift_report["drifted_feature_count"] > 0:
        top_features = ", ".join(
            f"{item['feature']}({item['zscore_shift']:.2f})"
            for item in drift_report["drifted_features"][:5]
        )
        notify_info(
            "⚠️ Feature Drift Detected",
            f"Drifted features: {drift_report['drifted_feature_count']}\n"
            f"Top shifts: {top_features}\n"
            f"Report: {DRIFT_REPORT_PATH}"
        )
    if calibration_report["overall_avg_brier_score"] > 0.25:
        notify_info(
            "⚠️ Calibration Quality Warning",
            f"Average Brier score: {calibration_report['overall_avg_brier_score']:.4f}\n"
            f"Report: {CALIBRATION_REPORT_PATH}"
        )
    if stability_report.get("high_variance_warning"):
        roc = stability_report.get("roc_auc", {})
        notify_info(
            "⚠️ Fold ROC-AUC Variance Warning",
            f"ROC-AUC std={roc.get('std')} (threshold={stability_report.get('roc_auc_std_warn_threshold')})\n"
            f"Report: {quality_paths['fold_stability']}",
        )

    threshold_retune_report, threshold_retune_results_df = _run_threshold_retune(
        settings=settings,
        ticker_data=training_data_fit,
        vix_df=vix_df,
        macro_df=macro_df,
    )
    _write_threshold_retune_report(threshold_retune_report, threshold_retune_results_df)
    settings.ai_score_buy_threshold = float(threshold_retune_report["best_buy_threshold"])
    if getattr(settings, "ai_exit_dynamic_enabled", False):
        settings.ai_exit_threshold_bear = float(threshold_retune_report["best_exit_threshold"])
    else:
        settings.ai_exit_threshold = float(threshold_retune_report["best_exit_threshold"])
    save_settings(settings)

    metrics_path = output_dir / "ai_model_metrics.csv"
    metrics_df.to_csv(metrics_path, index=False)

    bundle = build_model_bundle(
        trained_models=model.models,
        metrics_df=metrics_df,
        training_data=training_data_fit,
        feature_columns=FEATURE_COLUMNS,
        prediction_horizon=model.prediction_horizon,
        target_return_threshold=model.target_return_threshold,
    )

    challenger_portfolio = None
    champion_portfolio = None
    if settings.use_ai_score:
        if holdout_start > holdout_end:
            raise ValueError(
                "Invalid portfolio holdout window; cannot score promotion gates"
            )
        print(
            "Running holdout-window portfolio evaluation for promotion gates "
            "(full history for indicator warmup)..."
        )
        challenger_portfolio = _run_retrain_oos_portfolio(
            settings=settings,
            ticker_data=training_data,
            vix_df=vix_df,
            macro_df=macro_df,
            model_wrapper=bundle_to_model_wrapper(bundle),
            eval_start=holdout_start,
            eval_end=holdout_end,
        )
        challenger_portfolio["holdout_excluded_from_training"] = True
        bundle["metadata"]["portfolio_oos"] = challenger_portfolio
        champion_wrapper = _load_champion_model_wrapper()
        if champion_wrapper is not None:
            champion_portfolio = _run_retrain_oos_portfolio(
                settings=settings,
                ticker_data=training_data,
                vix_df=vix_df,
                macro_df=macro_df,
                model_wrapper=champion_wrapper,
                eval_start=holdout_start,
                eval_end=holdout_end,
            )
            champion_portfolio["holdout_excluded_from_training"] = True

    challenger_model_path, challenger_metadata_path = save_challenger_bundle(bundle)
    champion_metadata = load_model_metadata()
    promotion_report = build_promotion_report(
        challenger_metadata=bundle["metadata"],
        champion_metadata=champion_metadata,
        challenger_portfolio=challenger_portfolio,
        champion_portfolio=champion_portfolio,
        require_portfolio_oos=settings.use_ai_score,
        fold_stability_report=stability_report,
        calibration_report=calibration_report,
        require_ml_quality=True,
    )
    promotion_report.update(
        {
            "challenger_model_path": str(challenger_model_path),
            "challenger_metadata_path": str(challenger_metadata_path),
            "champion_model_path": str(MODEL_PATH),
            "champion_metadata_path": str(MODEL_METADATA_PATH),
        }
    )
    promotion_report_path = output_dir / "model_promotion_report.json"
    promotion_report_path.write_text(
        json.dumps(promotion_report, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    if promotion_report["decision"] == "PROMOTE":
        archived = archive_current_champion()
        save_model_bundle(bundle)
        if archived is not None:
            promotion_report["archived_previous_champion_model_path"] = str(archived[0])
            promotion_report["archived_previous_champion_metadata_path"] = str(archived[1])

    archived = find_latest_archived_champion(CHAMPION_ARCHIVE_DIR)
    rollback_report = resolve_rollback_decision(
        promotion_report["decision"],
        _load_recent_performance_snapshot(),
        archived,
    )
    _write_rollback_report(rollback_report)

    elapsed = time.time() - started_at
    _append_retrain_log("success", metrics_df, elapsed)

    print("AI score model trained.")
    print(f"Model: LightGBM (n_estimators=500, max_depth=6)")
    print(f"Features: {len(model.feature_columns)} ({', '.join(model.feature_columns)})")
    print(f"Saved challenger model to {challenger_model_path}")
    print(f"Saved challenger metadata to {challenger_metadata_path}")
    print(f"Promotion decision: {promotion_report['decision']}")
    if promotion_report["decision"] == "PROMOTE":
        print(f"Promoted challenger to champion at {MODEL_PATH}")
    else:
        print(f"Retained existing champion at {MODEL_PATH}")
    print(f"Saved metrics to {metrics_path}")
    print(f"Saved promotion report to {promotion_report_path}")
    print(f"Saved rollback report to {ROLLBACK_REPORT_PATH}")
    print(f"Saved feature drift report to {DRIFT_REPORT_PATH}")
    print(f"Saved fold metrics to {quality_paths['fold_metrics']}")
    print(f"Saved fold stability report to {quality_paths['fold_stability']}")
    print(f"Saved calibration report to {CALIBRATION_REPORT_PATH}")
    print(f"Saved calibration bins to {CALIBRATION_BINS_PATH}")
    print(f"Saved threshold retune report to {THRESHOLD_RETUNE_REPORT_PATH}")
    print(f"Saved threshold retune results to {THRESHOLD_RETUNE_RESULTS_PATH}")
    print(
        f"Updated thresholds: buy={settings.ai_score_buy_threshold:.2f}, "
        f"exit={settings.ai_exit_threshold_bear if getattr(settings, 'ai_exit_dynamic_enabled', False) else settings.ai_exit_threshold:.2f}"
    )
    print(f"Elapsed: {elapsed:.1f}s")
    print(metrics_df.to_string(index=False))


if __name__ == "__main__":
    main()
