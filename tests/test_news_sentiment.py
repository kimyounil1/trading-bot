from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from src.news_feed import NewsArticle
from src.news_sentiment import get_batch_sentiments, get_ticker_sentiment


def _article(headline: str) -> NewsArticle:
    return NewsArticle(
        provider="alpaca",
        article_id=headline,
        headline=headline,
        published_at="2026-07-23T10:00:00Z",
        updated_at="2026-07-23T10:00:00Z",
        symbols=("AAPL",),
        source="benzinga",
        fetched_at="2026-07-23T10:01:00Z",
    )


class TestNewsSentiment(unittest.TestCase):
    @patch("src.news_sentiment._get_vader")
    @patch("src.news_sentiment.get_ticker_news")
    def test_scores_headlines_from_shared_store(self, mock_news, mock_vader) -> None:
        mock_news.return_value = [_article("good"), _article("bad")]
        analyzer = MagicMock()
        analyzer.polarity_scores.side_effect = [
            {"compound": 0.8},
            {"compound": -0.2},
        ]
        mock_vader.return_value = analyzer

        score = get_ticker_sentiment("aapl")

        self.assertAlmostEqual(score, 0.3)
        mock_news.assert_called_once_with(
            "aapl",
            max_articles=10,
            as_of_date=None,
            refresh=True,
        )

    @patch("src.news_sentiment.get_ticker_sentiment_from_cache", return_value=0.1)
    @patch("src.news_sentiment.refresh_news_cache")
    def test_batch_refreshes_once_then_reads_cache(
        self,
        mock_refresh,
        mock_cached_sentiment,
    ) -> None:
        mock_refresh.return_value = MagicMock(errors=())

        result = get_batch_sentiments(["AAPL", "MSFT"])

        self.assertEqual(result, {"AAPL": 0.1, "MSFT": 0.1})
        mock_refresh.assert_called_once_with(["AAPL", "MSFT"])
        self.assertEqual(mock_cached_sentiment.call_count, 2)


if __name__ == "__main__":
    unittest.main()
