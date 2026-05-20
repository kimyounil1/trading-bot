from pathlib import Path

from src.settings import load_settings
from src.data_loader import load_price_data
from src.ml_model import train_ai_score_model


def main() -> None:
    settings = load_settings()

    training_data = {}

    for ticker in settings.tickers:
        print(f"Loading {ticker}...")
        training_data[ticker] = load_price_data(ticker, period="5y")

    model, metrics_df = train_ai_score_model(
        training_data=training_data,
        prediction_horizon=5,
        target_return_threshold=0.0,
    )

    output_dir = Path("logs/ml")
    output_dir.mkdir(parents=True, exist_ok=True)

    metrics_path = output_dir / "ai_model_metrics.csv"
    metrics_df.to_csv(metrics_path, index=False)

    print("AI score model trained.")
    print(f"Saved model to models/ai_score_model.joblib")
    print(f"Saved metrics to {metrics_path}")
    print(metrics_df.to_string(index=False))


if __name__ == "__main__":
    main()
