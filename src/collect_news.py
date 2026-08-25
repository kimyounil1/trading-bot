"""CLI for refreshing the local Alpaca news archive."""

from __future__ import annotations

import argparse
import json

from src.news_feed import refresh_news_cache
from src.settings import load_settings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tickers",
        nargs="*",
        help="Symbols to refresh; defaults to the configured strategy universe",
    )
    parser.add_argument("--force", action="store_true", help="Ignore the freshness TTL")
    parser.add_argument(
        "--no-yfinance-fallback",
        action="store_true",
        help="Fail instead of using yfinance when Alpaca is unavailable",
    )
    args = parser.parse_args()

    tickers = args.tickers or load_settings().tickers
    result = refresh_news_cache(
        tickers,
        force=args.force,
        allow_yfinance_fallback=not args.no_yfinance_fallback,
    )
    print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))
    return 1 if result.failed_symbols else 0


if __name__ == "__main__":
    raise SystemExit(main())
