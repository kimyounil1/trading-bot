from __future__ import annotations

"""Live news sentiment using yfinance + VADER. Used for buy filtering only (not training)."""

from datetime import datetime

import pandas as pd
import yfinance as yf


def _headlines_current(ticker: str, max_articles: int = 10) -> list[str]:
    """Recent headlines from yfinance (no date filter). Used when historical replay has no articles."""
    try:
        news = yf.Ticker(ticker).news or []
    except Exception:
        return []
    titles: list[str] = []
    for item in news:
        content = item.get("content") or {}
        title = content.get("title") or item.get("title") or ""
        if title:
            titles.append(title)
        if len(titles) >= max_articles:
            break
    return titles


def _headlines_before_date(ticker: str, as_of_date: str, max_articles: int = 10) -> list[str]:
    """Headlines with pubDate on or before as_of_date (yfinance only retains recent articles)."""
    try:
        news = yf.Ticker(ticker).news or []
    except Exception:
        return []

    end = pd.Timestamp(as_of_date).normalize() + pd.Timedelta(days=1)
    titles: list[str] = []
    for item in news:
        content = item.get("content") or {}
        title = content.get("title") or item.get("title") or ""
        if not title:
            continue
        pub = content.get("pubDate") or content.get("displayTime")
        if pub:
            pub_ts = pd.Timestamp(pub)
            if pub_ts.tzinfo is not None:
                pub_ts = pub_ts.tz_convert("UTC").tz_localize(None)
            if pub_ts >= end:
                continue
        titles.append(title)
        if len(titles) >= max_articles:
            break
    return titles


def _get_vader():
    from nltk.sentiment.vader import SentimentIntensityAnalyzer
    import nltk
    try:
        return SentimentIntensityAnalyzer()
    except LookupError:
        nltk.download("vader_lexicon", quiet=True)
        return SentimentIntensityAnalyzer()


def get_ticker_sentiment(
    ticker: str,
    max_articles: int = 10,
    as_of_date: str | None = None,
) -> float | None:
    """VADER compound sentiment score for recent news headlines.

    Returns compound score in [-1, 1]:
      -1 = very negative, 0 = neutral, +1 = very positive
    Returns None if news is unavailable (don't block on API failure).
    """
    if as_of_date:
        titles = _headlines_before_date(ticker, as_of_date, max_articles=max_articles)
        if not titles:
            return None
        sia = _get_vader()
        scores = [sia.polarity_scores(title)["compound"] for title in titles]
        return sum(scores) / len(scores) if scores else None

    try:
        news = yf.Ticker(ticker).news or []
    except Exception:
        return None

    if not news:
        return None

    sia = _get_vader()
    scores = []
    for item in news[:max_articles]:
        content = item.get("content") or {}
        title = content.get("title") or item.get("title") or ""
        if title:
            scores.append(sia.polarity_scores(title)["compound"])

    return sum(scores) / len(scores) if scores else None


def get_batch_sentiments(tickers: list[str]) -> dict[str, float | None]:
    """Fetch sentiment for multiple tickers. Silently returns None on failure."""
    return {ticker: get_ticker_sentiment(ticker) for ticker in tickers}
