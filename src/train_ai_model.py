import csv
from datetime import datetime, timezone
from pathlib import Path

from src.settings import load_settings
from src.data_loader import load_price_data_batch
from src.ml_model import train_ai_score_model
from src.macro_loader import load_macro_data

VIX_TICKER = "^VIX"
RETRAIN_LOG_PATH = Path("logs/retrain_history.csv")


def _append_retrain_log(status: str, metrics_df, elapsed_sec: float) -> None:
    RETRAIN_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_header = not RETRAIN_LOG_PATH.exists()

    avg_roc = 0.0
    avg_precision = 0.0
    if metrics_df is not None and not metrics_df.empty:
        if "roc_auc" in metrics_df.columns:
            avg_roc = float(metrics_df["roc_auc"].mean())
        if "precision" in metrics_df.columns:
            avg_precision = float(metrics_df["precision"].mean())

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

    print("Training model with LightGBM + enhanced features (21 features)...")
    model, metrics_df = train_ai_score_model(
        training_data=training_data,
        prediction_horizon=20,
        target_return_threshold=0.0,
        vix_df=vix_df,
        spy_df=spy_df,
        macro_df=macro_df,
    )

    output_dir = Path("logs/ml")
    output_dir.mkdir(parents=True, exist_ok=True)

    metrics_path = output_dir / "ai_model_metrics.csv"
    metrics_df.to_csv(metrics_path, index=False)

    elapsed = time.time() - started_at
    _append_retrain_log("success", metrics_df, elapsed)

    print("AI score model trained.")
    print(f"Model: LightGBM (n_estimators=500, max_depth=6)")
    print(f"Features: {len(model.feature_columns)} ({', '.join(model.feature_columns)})")
    print(f"Saved model to models/ai_score_model.joblib")
    print(f"Saved metrics to {metrics_path}")
    print(f"Elapsed: {elapsed:.1f}s")
    print(metrics_df.to_string(index=False))


if __name__ == "__main__":
    main()
