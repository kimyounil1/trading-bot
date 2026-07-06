"""Backfill historical news headlines for the paper universe via Alpaca News API.

Benzinga-sourced, symbol-tagged, reaches back to ~2015 — solves the yfinance
"recent articles only" limitation for research. Headlines only (no bodies).
Caches per ticker to data/news_history/<TICKER>.csv; fresh caches are skipped,
so reruns only fetch what is missing.

Usage:
  .venv/bin/python -m scripts.news_sentiment_backfill [--years 2]
"""

from __future__ import annotations

import argparse
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

NEWS_HISTORY_DIR = Path("data/news_history")
CACHE_TTL_HOURS = 24 * 7


def fetch_ticker_news(client, ticker: str, start: datetime, end: datetime) -> pd.DataFrame:
    from alpaca.data.requests import NewsRequest

    req = NewsRequest(
        symbols=ticker,
        start=start,
        end=end,
        include_content=False,
        exclude_contentless=False,
    )
    res = client.get_news(req)
    items = res.data.get("news", [])
    rows = [
        {
            "created_at": a.created_at.astimezone(timezone.utc).isoformat(),
            "headline": (a.headline or "").strip(),
        }
        for a in items
        if a.headline
    ]
    return pd.DataFrame(rows, columns=["created_at", "headline"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=int, default=2)
    args = ap.parse_args()

    from alpaca.data.historical.news import NewsClient

    from src.config import ALPACA_API_KEY, ALPACA_SECRET_KEY
    from src.settings import load_settings

    NEWS_HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    client = NewsClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=365 * args.years)

    tickers = [str(t).strip().upper() for t in load_settings().tickers]
    total_articles = 0
    fetched = skipped = failed = 0
    for i, ticker in enumerate(tickers, 1):
        cache_path = NEWS_HISTORY_DIR / f"{ticker}.csv"
        if cache_path.exists():
            age_hours = (time.time() - cache_path.stat().st_mtime) / 3600
            if age_hours < CACHE_TTL_HOURS:
                skipped += 1
                continue
        try:
            df = fetch_ticker_news(client, ticker, start, end)
        except Exception as exc:
            print(f"[{i}/{len(tickers)}] {ticker}: FAILED ({exc})")
            failed += 1
            time.sleep(2.0)
            continue
        df.to_csv(cache_path, index=False)
        fetched += 1
        total_articles += len(df)
        if fetched % 10 == 0 or len(df) == 0:
            print(f"[{i}/{len(tickers)}] {ticker}: {len(df)} articles (running total {total_articles:,})")
        time.sleep(0.3)

    print(
        f"\nDone: fetched={fetched} skipped(fresh)={skipped} failed={failed} "
        f"articles={total_articles:,} -> {NEWS_HISTORY_DIR}/"
    )


if __name__ == "__main__":
    main()
