from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from src import news_feed
from src.news_feed import NewsArticle


class TestNewsFeed(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.path_patches = [
            patch.object(news_feed, "NEWS_DB_PATH", root / "news.sqlite3"),
            patch.object(news_feed, "NEWS_RAW_DIR", root / "raw"),
            patch.object(news_feed, "NEWS_CACHE_TTL_SECONDS", 600),
            patch.object(news_feed, "NEWS_BATCH_SIZE", 20),
        ]
        for path_patch in self.path_patches:
            path_patch.start()

    def tearDown(self) -> None:
        for path_patch in reversed(self.path_patches):
            path_patch.stop()
        self.temp_dir.cleanup()

    @staticmethod
    def _article(
        article_id: str = "123",
        *,
        published_at: str = "2026-07-23T10:00:00Z",
    ) -> NewsArticle:
        return NewsArticle(
            provider="alpaca",
            article_id=article_id,
            headline="AAPL issues updated guidance",
            published_at=published_at,
            updated_at=published_at,
            symbols=("AAPL", "MSFT"),
            source="benzinga",
            summary="Management updated forward guidance.",
            content="The company published a detailed guidance update.",
            url="https://example.test/article",
            author="Reporter",
            fetched_at="2026-07-23T10:01:00Z",
        )

    def test_store_deduplicates_and_indexes_each_symbol(self) -> None:
        article = self._article()

        first_new = news_feed._store_articles([article])
        second_new = news_feed._store_articles([article])

        self.assertEqual(first_new, [article])
        self.assertEqual(second_new, [])
        for symbol in ("AAPL", "MSFT"):
            loaded = news_feed.load_news_articles(
                symbol,
                max_articles=5,
                now=datetime(2026, 7, 23, 10, 2, tzinfo=timezone.utc),
            )
            self.assertEqual([row.article_id for row in loaded], ["123"])
            self.assertEqual(loaded[0].content, article.content)

    @patch("src.news_feed._fetch_alpaca_news")
    def test_refresh_uses_ttl_and_archives_only_new_articles(self, mock_fetch) -> None:
        now = datetime(2026, 7, 23, 10, 1, tzinfo=timezone.utc)
        mock_fetch.return_value = [self._article()]

        first = news_feed.refresh_news_cache(
            ["aapl", "MSFT"],
            allow_yfinance_fallback=False,
            now=now,
        )
        second = news_feed.refresh_news_cache(
            ["AAPL", "MSFT"],
            allow_yfinance_fallback=False,
            now=now + timedelta(minutes=5),
        )

        self.assertEqual(first.refreshed_symbols, ("AAPL", "MSFT"))
        self.assertEqual(first.new_articles, 1)
        self.assertEqual(second.refreshed_symbols, ())
        self.assertEqual(mock_fetch.call_count, 1)
        self.assertEqual(
            mock_fetch.call_args.kwargs["start"],
            now - timedelta(hours=news_feed.NEWS_LOOKBACK_HOURS),
        )
        archive = news_feed.NEWS_RAW_DIR / "2026-07-23.jsonl"
        self.assertEqual(len(archive.read_text(encoding="utf-8").splitlines()), 1)

    @patch("src.news_feed._fetch_yfinance_news")
    @patch("src.news_feed._fetch_alpaca_news", side_effect=RuntimeError("rate limited"))
    def test_refresh_records_alpaca_error_and_uses_fallback(
        self,
        _mock_alpaca,
        mock_yfinance,
    ) -> None:
        mock_yfinance.return_value = [
            NewsArticle(
                **{
                    **self._article().__dict__,
                    "provider": "yfinance",
                    "article_id": "yf-1",
                    "symbols": ("AAPL",),
                }
            )
        ]

        now = datetime(2026, 7, 23, 10, 2, tzinfo=timezone.utc)
        result = news_feed.refresh_news_cache(["AAPL"], now=now)

        self.assertEqual(result.failed_symbols, ())
        self.assertEqual(result.refreshed_symbols, ("AAPL",))
        self.assertIn("rate limited", result.errors[0])
        self.assertEqual(
            news_feed.load_news_articles("AAPL", now=now)[0].provider,
            "yfinance",
        )

    @patch("src.news_feed.refresh_news_cache")
    def test_historical_lookup_never_refreshes(self, mock_refresh) -> None:
        news_feed._store_articles([self._article()])

        rows = news_feed.get_ticker_news(
            "AAPL",
            as_of_date="2026-07-23",
            refresh=False,
        )

        self.assertEqual(len(rows), 1)
        mock_refresh.assert_not_called()


if __name__ == "__main__":
    unittest.main()
