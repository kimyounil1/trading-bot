from src.settings import load_settings
from src.data_loader import load_price_data_batch
from src.ml_model import load_ai_score_model, predict_ai_score_from_bundle


def main() -> None:
    settings = load_settings()
    ticker_data = load_price_data_batch(settings.tickers, period="5y")
    ai_model_bundle = load_ai_score_model()

    for ticker in settings.tickers:
        try:
            score = predict_ai_score_from_bundle(ticker_data[ticker], ai_model_bundle)
            print(f"{ticker}: ai_score={score:.4f}")
        except Exception as exc:
            print(f"{ticker}: ERROR - {exc}")


if __name__ == "__main__":
    main()
