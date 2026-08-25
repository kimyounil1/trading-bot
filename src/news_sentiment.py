from __future__ import annotations

"""Live news sentiment using the shared Alpaca/local news store + VADER."""

from datetime import datetime

from src.news_feed import NewsArticle, get_ticker_news, refresh_news_cache


def _format_article_context(article: NewsArticle, *, max_text_chars: int = 1600) -> str:
    """Render one stored article as bounded, attributable LLM context."""
    body = " ".join((article.content or article.summary).split())
    if len(body) > max_text_chars:
        body = body[:max_text_chars].rstrip() + "…"
    source = article.source or article.provider
    lines = [
        f"[{article.published_at}] {source}: {article.headline}",
    ]
    if article.summary and article.summary.strip() != body:
        summary = " ".join(article.summary.split())
        lines.append(f"Summary: {summary[:700]}")
    if body:
        lines.append(f"Article excerpt: {body}")
    if article.url:
        lines.append(f"Source URL: {article.url}")
    return "\n".join(lines)


def _headlines_current(
    ticker: str,
    max_articles: int = 10,
    *,
    include_details: bool = False,
) -> list[str]:
    """Recent shared-cache news, refreshed from Alpaca when stale."""
    articles = get_ticker_news(ticker, max_articles=max_articles)
    if include_details:
        return [_format_article_context(article) for article in articles]
    return [article.headline for article in articles]


def _headlines_before_date(
    ticker: str,
    as_of_date: str,
    max_articles: int = 10,
    *,
    include_details: bool = False,
) -> list[str]:
    """Stored news published on/before the date; historical calls never hit APIs."""
    is_current = str(as_of_date) >= datetime.now().date().isoformat()
    articles = get_ticker_news(
        ticker,
        max_articles=max_articles,
        as_of_date=None if is_current else as_of_date,
        refresh=is_current,
    )
    if include_details:
        return [_format_article_context(article) for article in articles]
    return [article.headline for article in articles]


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
    articles = get_ticker_news(
        ticker,
        max_articles=max_articles,
        as_of_date=as_of_date,
        refresh=as_of_date is None,
    )
    if not articles:
        return None
    sia = _get_vader()
    scores = [
        sia.polarity_scores(article.headline)["compound"]
        for article in articles
        if article.headline
    ]
    return sum(scores) / len(scores) if scores else None


def get_batch_sentiments(tickers: list[str]) -> dict[str, float | None]:
    """Refresh in Alpaca batches, then score every ticker from the same snapshot."""
    refresh_result = refresh_news_cache(tickers)
    for error in refresh_result.errors:
        print(f"Warning: {error}")
    return {
        ticker: get_ticker_sentiment_from_cache(ticker)
        for ticker in tickers
    }


def get_ticker_sentiment_from_cache(
    ticker: str,
    max_articles: int = 10,
    as_of_date: str | None = None,
) -> float | None:
    """VADER score without network access, for an already refreshed batch."""
    articles = get_ticker_news(
        ticker,
        max_articles=max_articles,
        as_of_date=as_of_date,
        refresh=False,
    )
    if not articles:
        return None
    sia = _get_vader()
    scores = [
        sia.polarity_scores(article.headline)["compound"]
        for article in articles
        if article.headline
    ]
    return sum(scores) / len(scores) if scores else None
