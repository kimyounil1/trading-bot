"""Populate data/llm_cache.json from portfolio backtest entry dates (paper-cache warmup)."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import src.config  # noqa: F401

from src.llm_analyst import CACHE_PATH, evaluate_ticker_consensus
from src.settings import load_settings

DEFAULT_BACKTEST_DIR = Path("logs/portfolio_backtest")
DEFAULT_OUTPUT_DIR = Path("logs/llm_cache_warmup")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_cache() -> dict:
    if not CACHE_PATH.is_file():
        return {}
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _entry_keys_from_backtest(backtest_dir: Path) -> list[tuple[str, str]]:
    trades_path = backtest_dir / "portfolio_trades.csv"
    if not trades_path.is_file():
        raise FileNotFoundError(f"Missing {trades_path}")
    trades = pd.read_csv(trades_path)
    trades["entry_date"] = pd.to_datetime(trades["entry_date"], errors="coerce").dt.strftime(
        "%Y-%m-%d"
    )
    pairs = (
        trades.dropna(subset=["entry_date"])
        .drop_duplicates(subset=["ticker", "entry_date"])
        .sort_values(["entry_date", "ticker"])
    )
    return [(str(row.ticker), str(row.entry_date)) for row in pairs.itertuples(index=False)]


def warm_llm_cache(
    *,
    backtest_dir: Path = DEFAULT_BACKTEST_DIR,
    sleep_seconds: float = 1.5,
    max_entries: int | None = None,
    skip_existing: bool = True,
    fallback_current_headlines: bool = True,
    dry_run: bool = False,
) -> dict:
    settings = load_settings()
    entries = _entry_keys_from_backtest(backtest_dir)
    cache = _load_cache()
    if skip_existing:
        entries = [
            (ticker, entry_date)
            for ticker, entry_date in entries
            if f"{ticker}_{entry_date}" not in cache
        ]
    if max_entries is not None and max_entries > 0:
        entries = entries[: int(max_entries)]

    warmed = 0
    skipped = 0
    rejected = 0
    errors = 0
    details: list[dict] = []

    for ticker, entry_date in entries:
        cache_key = f"{ticker}_{entry_date}"
        if dry_run:
            warmed += 1
            continue

        try:
            ok, reason = evaluate_ticker_consensus(
                ticker,
                settings=settings,
                as_of_date=entry_date,
                cache_only=False,
                fallback_current_headlines=fallback_current_headlines,
            )
            cache = _load_cache()
            warmed += 1
            if not ok:
                rejected += 1
            details.append(
                {
                    "key": cache_key,
                    "is_approved": ok,
                    "reason_preview": (reason or "")[:120],
                }
            )
        except Exception as exc:
            errors += 1
            details.append({"key": cache_key, "error": str(exc)})

        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    report = {
        "generated_at": _utc_now_iso(),
        "backtest_dir": str(backtest_dir),
        "cache_path": str(CACHE_PATH),
        "total_entry_keys": len(_entry_keys_from_backtest(backtest_dir)),
        "processed": len(entries),
        "warmed": warmed,
        "skipped_existing": skipped,
        "pending_before_run": len(entries),
        "rejected": rejected,
        "errors": errors,
        "cache_size_after": len(_load_cache()),
        "fallback_current_headlines": fallback_current_headlines,
        "sample": details[:15],
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Warm LLM cache from backtest trade entries")
    parser.add_argument("--backtest-dir", default=str(DEFAULT_BACKTEST_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--sleep", type=float, default=1.5, help="Seconds between API calls")
    parser.add_argument("--max-entries", type=int, default=None)
    parser.add_argument("--force", action="store_true", help="Re-fetch even if cache key exists")
    parser.add_argument(
        "--no-fallback-headlines",
        action="store_true",
        help="Do not use current headlines when entry-date feed is empty",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    report = warm_llm_cache(
        backtest_dir=Path(args.backtest_dir),
        sleep_seconds=args.sleep,
        max_entries=args.max_entries,
        skip_existing=not args.force,
        fallback_current_headlines=not args.no_fallback_headlines,
        dry_run=args.dry_run,
    )
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "latest_summary.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print("=== LLM cache warmup ===")
    print(f"Cache file: {report['cache_path']}")
    print(
        f"Warmed {report['warmed']} | skipped {report['skipped_existing']} | "
        f"rejected {report['rejected']} | errors {report['errors']} | "
        f"cache size {report['cache_size_after']}"
    )
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
