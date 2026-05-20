from src.settings import load_settings
from src.data_loader import load_price_data
from src.ml_model import predict_ai_score


def main() -> None:
    settings = load_settings()

    for ticker in settings.tickers:
        try:
            df = load_price_data(ticker, period="5y")
            score = predict_ai_score(df)
            print(f"{ticker}: ai_score={score:.4f}")
        except Exception as exc:
            print(f"{ticker}: ERROR - {exc}")


if __name__ == "__main__":
    main()
