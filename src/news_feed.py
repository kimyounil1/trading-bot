"""Shared Alpaca news collection and local persistence.

SQLite is the query source used by both VADER and the LLM. Newly seen articles
are also appended to date-partitioned JSONL files for audit/reprocessing.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from src.config import ALPACA_API_KEY, ALPACA_SECRET_KEY


NEWS_DB_PATH = Path(os.getenv("NEWS_DB_PATH", "data/news/news.sqlite3"))
NEWS_RAW_DIR = Path(os.getenv("NEWS_RAW_DIR", "data/news/raw"))
NEWS_CACHE_TTL_SECONDS = int(os.getenv("NEWS_CACHE_TTL_SECONDS", "600"))
NEWS_LOOKBACK_HOURS = int(os.getenv("NEWS_LOOKBACK_HOURS", "72"))
NEWS_BATCH_SIZE = max(1, int(os.getenv("NEWS_BATCH_SIZE", "20")))
NEWS_PAGE_LIMIT = min(50, max(1, int(os.getenv("NEWS_PAGE_LIMIT", "50"))))
NEWS_MAX_PAGES_PER_BATCH = max(
    1, int(os.getenv("NEWS_MAX_PAGES_PER_BATCH", "20"))
)
NEWS_YFINANCE_FALLBACK = os.getenv(
    "NEWS_YFINANCE_FALLBACK", "true"
).strip().lower() in {"1", "true", "yes"}
_REFRESH_OVERLAP = timedelta(minutes=5)


@dataclass(frozen=True)
class NewsArticle:
    provider: str
    article_id: str
    headline: str
    published_at: str
    updated_at: str
    symbols: tuple[str, ...]
    source: str = ""
    summary: str = ""
    content: str = ""
    url: str = ""
    author: str = ""
    fetched_at: str = ""


@dataclass(frozen=True)
class NewsRefreshResult:
    requested_symbols: tuple[str, ...]
    refreshed_symbols: tuple[str, ...]
    failed_symbols: tuple[str, ...]
    fetched_articles: int
    new_articles: int
    errors: tuple[str, ...]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value or "").strip()
        if not text:
            return _utc_now()
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _iso_utc(value: Any) -> str:
    return _as_utc(value).isoformat().replace("+00:00", "Z")


def _normalize_symbols(symbols: Iterable[Any]) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            str(symbol).strip().upper()
            for symbol in symbols
            if str(symbol).strip()
        )
    )


def _connect() -> sqlite3.Connection:
    NEWS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(NEWS_DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 10000")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS articles (
            provider TEXT NOT NULL,
            article_id TEXT NOT NULL,
            headline TEXT NOT NULL,
            published_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            source TEXT NOT NULL,
            summary TEXT NOT NULL,
            content TEXT NOT NULL,
            url TEXT NOT NULL,
            author TEXT NOT NULL,
            symbols_json TEXT NOT NULL,
            fetched_at TEXT NOT NULL,
            PRIMARY KEY (provider, article_id)
        );
        CREATE TABLE IF NOT EXISTS article_symbols (
            provider TEXT NOT NULL,
            article_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            PRIMARY KEY (provider, article_id, symbol),
            FOREIGN KEY (provider, article_id)
                REFERENCES articles(provider, article_id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_article_symbols_symbol
            ON article_symbols(symbol);
        CREATE INDEX IF NOT EXISTS idx_articles_published_at
            ON articles(published_at DESC);
        CREATE TABLE IF NOT EXISTS refresh_state (
            symbol TEXT PRIMARY KEY,
            refreshed_at TEXT NOT NULL,
            provider TEXT NOT NULL
        );
        """
    )
    return connection


def _normalize_alpaca_article(raw: Any, fetched_at: datetime) -> NewsArticle | None:
    headline = str(getattr(raw, "headline", "") or "").strip()
    if not headline:
        return None
    article_id = str(getattr(raw, "id", "") or "").strip()
    if not article_id:
        article_id = hashlib.sha256(
            f"{headline}|{getattr(raw, 'url', '')}".encode("utf-8")
        ).hexdigest()
    published = getattr(raw, "created_at", None) or fetched_at
    updated = getattr(raw, "updated_at", None) or published
    return NewsArticle(
        provider="alpaca",
        article_id=article_id,
        headline=headline,
        published_at=_iso_utc(published),
        updated_at=_iso_utc(updated),
        symbols=_normalize_symbols(getattr(raw, "symbols", []) or []),
        source=str(getattr(raw, "source", "") or "").strip(),
        summary=str(getattr(raw, "summary", "") or "").strip(),
        content=str(getattr(raw, "content", "") or "").strip(),
        url=str(getattr(raw, "url", "") or "").strip(),
        author=str(getattr(raw, "author", "") or "").strip(),
        fetched_at=_iso_utc(fetched_at),
    )


def _fetch_alpaca_news(
    symbols: tuple[str, ...],
    *,
    start: datetime,
    end: datetime,
    fetched_at: datetime,
) -> list[NewsArticle]:
    if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
        raise ValueError("Alpaca news requires ALPACA_API_KEY and ALPACA_SECRET_KEY")

    from alpaca.data.historical.news import NewsClient
    from alpaca.data.requests import NewsRequest

    client = NewsClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)
    page_token: str | None = None
    articles: list[NewsArticle] = []
    for page_number in range(NEWS_MAX_PAGES_PER_BATCH):
        response = client.get_news(
            NewsRequest(
                symbols=",".join(symbols),
                start=start,
                end=end,
                sort="desc",
                limit=NEWS_PAGE_LIMIT,
                include_content=True,
                page_token=page_token,
            )
        )
        for raw in response.data.get("news", []):
            article = _normalize_alpaca_article(raw, fetched_at)
            if article is not None:
                articles.append(article)
        page_token = response.next_page_token
        if not page_token:
            break
    else:
        if page_token:
            print(
                "Warning: Alpaca news pagination reached "
                f"NEWS_MAX_PAGES_PER_BATCH={NEWS_MAX_PAGES_PER_BATCH} "
                f"for {','.join(symbols)}"
            )
    return articles


def _fetch_yfinance_news(symbol: str, fetched_at: datetime) -> list[NewsArticle]:
    import yfinance as yf

    raw_news = yf.Ticker(symbol).news or []
    articles: list[NewsArticle] = []
    for raw in raw_news:
        content_block = raw.get("content") or {}
        headline = str(content_block.get("title") or raw.get("title") or "").strip()
        if not headline:
            continue
        published = (
            content_block.get("pubDate")
            or content_block.get("displayTime")
            or raw.get("providerPublishTime")
            or fetched_at
        )
        if isinstance(published, (int, float)):
            published = datetime.fromtimestamp(published, tz=timezone.utc)
        url = str(
            (content_block.get("canonicalUrl") or {}).get("url")
            or raw.get("link")
            or ""
        ).strip()
        article_id = str(raw.get("id") or raw.get("uuid") or "").strip()
        if not article_id:
            article_id = hashlib.sha256(
                f"{headline}|{url}|{published}".encode("utf-8")
            ).hexdigest()
        provider = content_block.get("provider") or {}
        articles.append(
            NewsArticle(
                provider="yfinance",
                article_id=article_id,
                headline=headline,
                published_at=_iso_utc(published),
                updated_at=_iso_utc(published),
                symbols=(symbol,),
                source=str(
                    provider.get("displayName")
                    or raw.get("publisher")
                    or "yfinance"
                ).strip(),
                summary=str(
                    content_block.get("summary") or raw.get("summary") or ""
                ).strip(),
                content="",
                url=url,
                author="",
                fetched_at=_iso_utc(fetched_at),
            )
        )
    return articles


def _store_articles(articles: Iterable[NewsArticle]) -> list[NewsArticle]:
    rows = list(articles)
    if not rows:
        return []
    new_rows: list[NewsArticle] = []
    with _connect() as connection:
        for article in rows:
            exists = connection.execute(
                "SELECT 1 FROM articles WHERE provider = ? AND article_id = ?",
                (article.provider, article.article_id),
            ).fetchone()
            connection.execute(
                """
                INSERT INTO articles (
                    provider, article_id, headline, published_at, updated_at,
                    source, summary, content, url, author, symbols_json, fetched_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(provider, article_id) DO UPDATE SET
                    headline = excluded.headline,
                    published_at = excluded.published_at,
                    updated_at = excluded.updated_at,
                    source = excluded.source,
                    summary = excluded.summary,
                    content = excluded.content,
                    url = excluded.url,
                    author = excluded.author,
                    symbols_json = excluded.symbols_json,
                    fetched_at = excluded.fetched_at
                """,
                (
                    article.provider,
                    article.article_id,
                    article.headline,
                    article.published_at,
                    article.updated_at,
                    article.source,
                    article.summary,
                    article.content,
                    article.url,
                    article.author,
                    json.dumps(article.symbols),
                    article.fetched_at,
                ),
            )
            connection.execute(
                "DELETE FROM article_symbols WHERE provider = ? AND article_id = ?",
                (article.provider, article.article_id),
            )
            connection.executemany(
                """
                INSERT INTO article_symbols(provider, article_id, symbol)
                VALUES (?, ?, ?)
                """,
                [
                    (article.provider, article.article_id, symbol)
                    for symbol in article.symbols
                ],
            )
            if exists is None:
                new_rows.append(article)
    return new_rows


def _archive_new_articles(articles: Iterable[NewsArticle]) -> None:
    grouped: dict[str, list[NewsArticle]] = {}
    for article in articles:
        date_key = _as_utc(article.fetched_at).date().isoformat()
        grouped.setdefault(date_key, []).append(article)
    for date_key, rows in grouped.items():
        NEWS_RAW_DIR.mkdir(parents=True, exist_ok=True)
        path = NEWS_RAW_DIR / f"{date_key}.jsonl"
        payload = "".join(
            json.dumps(asdict(row), ensure_ascii=False, sort_keys=True) + "\n"
            for row in rows
        )
        with path.open("a", encoding="utf-8") as stream:
            stream.write(payload)


def _refresh_times(symbols: tuple[str, ...]) -> dict[str, datetime]:
    if not symbols or not NEWS_DB_PATH.exists():
        return {}
    placeholders = ",".join("?" for _ in symbols)
    with _connect() as connection:
        rows = connection.execute(
            f"SELECT symbol, refreshed_at FROM refresh_state "
            f"WHERE symbol IN ({placeholders})",
            symbols,
        ).fetchall()
    return {str(row["symbol"]): _as_utc(row["refreshed_at"]) for row in rows}


def _mark_refreshed(
    symbols: tuple[str, ...], refreshed_at: datetime, provider: str
) -> None:
    with _connect() as connection:
        connection.executemany(
            """
            INSERT INTO refresh_state(symbol, refreshed_at, provider)
            VALUES (?, ?, ?)
            ON CONFLICT(symbol) DO UPDATE SET
                refreshed_at = excluded.refreshed_at,
                provider = excluded.provider
            """,
            [(symbol, _iso_utc(refreshed_at), provider) for symbol in symbols],
        )


def refresh_news_cache(
    symbols: Iterable[str],
    *,
    force: bool = False,
    allow_yfinance_fallback: bool = NEWS_YFINANCE_FALLBACK,
    now: datetime | None = None,
) -> NewsRefreshResult:
    """Refresh stale symbols in batches and persist normalized articles."""
    requested = _normalize_symbols(symbols)
    current = _as_utc(now or _utc_now())
    refresh_times = _refresh_times(requested)
    stale = tuple(
        symbol
        for symbol in requested
        if force
        or symbol not in refresh_times
        or (current - refresh_times[symbol]).total_seconds()
        >= NEWS_CACHE_TTL_SECONDS
    )
    refreshed: list[str] = []
    failed: list[str] = []
    errors: list[str] = []
    fetched_count = 0
    new_count = 0

    for offset in range(0, len(stale), NEWS_BATCH_SIZE):
        batch = stale[offset : offset + NEWS_BATCH_SIZE]
        known_refreshes = [
            refresh_times[symbol]
            for symbol in batch
            if symbol in refresh_times
        ]
        if len(known_refreshes) == len(batch):
            start = max(
                current - timedelta(hours=NEWS_LOOKBACK_HOURS),
                min(known_refreshes) - _REFRESH_OVERLAP,
            )
        else:
            start = current - timedelta(hours=NEWS_LOOKBACK_HOURS)
        try:
            articles = _fetch_alpaca_news(
                batch,
                start=start,
                end=current,
                fetched_at=current,
            )
            fetched_count += len(articles)
            new_articles = _store_articles(articles)
            _archive_new_articles(new_articles)
            new_count += len(new_articles)
            _mark_refreshed(batch, current, "alpaca")
            refreshed.extend(batch)
            continue
        except Exception as exc:  # provider failure is reported and optionally degraded
            errors.append(f"Alpaca news failed for {','.join(batch)}: {exc}")

        if not allow_yfinance_fallback:
            failed.extend(batch)
            continue

        for symbol in batch:
            try:
                fallback_articles = _fetch_yfinance_news(symbol, current)
                fetched_count += len(fallback_articles)
                new_articles = _store_articles(fallback_articles)
                _archive_new_articles(new_articles)
                new_count += len(new_articles)
                _mark_refreshed((symbol,), current, "yfinance")
                refreshed.append(symbol)
            except Exception as exc:
                failed.append(symbol)
                errors.append(f"yfinance news failed for {symbol}: {exc}")

    return NewsRefreshResult(
        requested_symbols=requested,
        refreshed_symbols=tuple(refreshed),
        failed_symbols=tuple(failed),
        fetched_articles=fetched_count,
        new_articles=new_count,
        errors=tuple(errors),
    )


def load_news_articles(
    symbol: str,
    *,
    max_articles: int = 10,
    as_of_date: str | None = None,
    now: datetime | None = None,
) -> list[NewsArticle]:
    """Load recent stored articles for one symbol without external calls."""
    normalized = _normalize_symbols((symbol,))
    if not normalized or not NEWS_DB_PATH.exists():
        return []
    if as_of_date:
        end = _as_utc(f"{as_of_date}T00:00:00Z") + timedelta(days=1)
    else:
        end = _as_utc(now or _utc_now()) + timedelta(minutes=1)
    start = end - timedelta(hours=NEWS_LOOKBACK_HOURS)
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT a.*
            FROM articles AS a
            JOIN article_symbols AS s
              ON s.provider = a.provider AND s.article_id = a.article_id
            WHERE s.symbol = ?
              AND a.published_at >= ?
              AND a.published_at < ?
            ORDER BY a.published_at DESC
            LIMIT ?
            """,
            (
                normalized[0],
                _iso_utc(start),
                _iso_utc(end),
                max(1, int(max_articles)),
            ),
        ).fetchall()
    return [
        NewsArticle(
            provider=str(row["provider"]),
            article_id=str(row["article_id"]),
            headline=str(row["headline"]),
            published_at=str(row["published_at"]),
            updated_at=str(row["updated_at"]),
            symbols=tuple(json.loads(row["symbols_json"])),
            source=str(row["source"]),
            summary=str(row["summary"]),
            content=str(row["content"]),
            url=str(row["url"]),
            author=str(row["author"]),
            fetched_at=str(row["fetched_at"]),
        )
        for row in rows
    ]


def get_ticker_news(
    symbol: str,
    *,
    max_articles: int = 10,
    as_of_date: str | None = None,
    refresh: bool = True,
) -> list[NewsArticle]:
    """Return shared cached news, refreshing only for live/current requests."""
    normalized = _normalize_symbols((symbol,))
    if not normalized:
        return []
    if refresh and as_of_date is None:
        result = refresh_news_cache(normalized)
        for error in result.errors:
            print(f"Warning: {error}")
    return load_news_articles(
        normalized[0],
        max_articles=max_articles,
        as_of_date=as_of_date,
    )
