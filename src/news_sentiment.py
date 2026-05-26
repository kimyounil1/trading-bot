"""Live news sentiment using yfinance + VADER. Used for buy filtering only (not training)."""

import yfinance as yf


def _get_vader():
    from nltk.sentiment.vader import SentimentIntensityAnalyzer
    import nltk
    try:
        return SentimentIntensityAnalyzer()
    except LookupError:
        nltk.download("vader_lexicon", quiet=True)
        return SentimentIntensityAnalyzer()


def get_ticker_sentiment(ticker: str, max_articles: int = 10) -> float | None:
    """VADER compound sentiment score for recent news headlines.

    Returns compound score in [-1, 1]:
      -1 = very negative, 0 = neutral, +1 = very positive
    Returns None if news is unavailable (don't block on API failure).
    """
    try:
        news = yf.Ticker(ticker).news or []
    except Exception:
        return None

    if not news:
        return None

    sia = _get_vader()
    scores = []
    for item in news[:max_articles]:
        # yfinance v0.2+ nests content under item["content"]["title"]
        content = item.get("content") or {}
        title = content.get("title") or item.get("title") or ""
        if title:
            scores.append(sia.polarity_scores(title)["compound"])

    return sum(scores) / len(scores) if scores else None


def get_batch_sentiments(tickers: list[str]) -> dict[str, float | None]:
    """Fetch sentiment for multiple tickers. Silently returns None on failure."""
    return {ticker: get_ticker_sentiment(ticker) for ticker in tickers}
