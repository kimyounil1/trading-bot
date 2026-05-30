"""Monitor LLM consensus cache size, coverage, and reuse (hit proxy)."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_CACHE_PATH = Path("data/llm_cache.json")
DEFAULT_OUTPUT_DIR = Path("logs/llm_monitoring")

LLM_CACHE_REPORT_KEYS = (
    "generated_at",
    "cache_path",
    "entry_count",
    "unique_tickers",
    "unique_days",
    "approved_count",
    "rejected_count",
    "estimated_cache_hit_rate",
    "entries_per_ticker_day",
    "top_tickers",
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_llm_cache(cache_path: str | Path = DEFAULT_CACHE_PATH) -> dict[str, Any]:
    path = Path(cache_path)
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _parse_cache_key(cache_key: str) -> tuple[str, str]:
    if "_" not in cache_key:
        return cache_key, "unknown"
    ticker, day = cache_key.rsplit("_", 1)
    return ticker, day


def summarize_llm_cache(cache: dict[str, Any]) -> dict[str, Any]:
    if not cache:
        return {
            "generated_at": _utc_now_iso(),
            "cache_path": str(DEFAULT_CACHE_PATH),
            "entry_count": 0,
            "unique_tickers": 0,
            "unique_days": 0,
            "approved_count": 0,
            "rejected_count": 0,
            "estimated_cache_hit_rate": 0.0,
            "entries_per_ticker_day": 0.0,
            "top_tickers": [],
        }

    tickers: list[str] = []
    days: set[str] = set()
    approved = 0
    rejected = 0
    ticker_counter: Counter[str] = Counter()

    for key, payload in cache.items():
        ticker, day = _parse_cache_key(str(key))
        tickers.append(ticker)
        days.add(day)
        ticker_counter[ticker] += 1
        if bool(payload.get("is_approved")):
            approved += 1
        else:
            rejected += 1

    entry_count = len(cache)
    unique_tickers = len(set(tickers))
    unique_days = len(days)
    # One cache row per ticker-day when live runs once per day → reuse rate proxy.
    possible_slots = max(unique_tickers * unique_days, 1)
    hit_rate = round(min(entry_count / possible_slots, 1.0), 4)

    return {
        "generated_at": _utc_now_iso(),
        "cache_path": str(DEFAULT_CACHE_PATH),
        "entry_count": entry_count,
        "unique_tickers": unique_tickers,
        "unique_days": unique_days,
        "approved_count": approved,
        "rejected_count": rejected,
        "estimated_cache_hit_rate": hit_rate,
        "entries_per_ticker_day": round(entry_count / possible_slots, 4),
        "top_tickers": [
            {"ticker": ticker, "count": count}
            for ticker, count in ticker_counter.most_common(10)
        ],
    }


def validate_llm_cache_report(report: dict[str, Any]) -> dict[str, Any]:
    for key in LLM_CACHE_REPORT_KEYS:
        if key not in report:
            raise ValueError(f"Missing LLM cache report key: {key}")
    if report["entry_count"] < 0:
        raise ValueError("entry_count must be non-negative")
    return report


def build_llm_cache_report(cache_path: str | Path = DEFAULT_CACHE_PATH) -> dict[str, Any]:
    report = summarize_llm_cache(load_llm_cache(cache_path))
    report["cache_path"] = str(cache_path)
    return validate_llm_cache_report(report)


def write_llm_cache_artifacts(
    report: dict[str, Any],
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "latest_summary.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return path


def run_llm_cache_report(
    cache_path: str | Path = DEFAULT_CACHE_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    report = build_llm_cache_report(cache_path)
    write_llm_cache_artifacts(report, output_dir)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM cache monitoring report")
    parser.add_argument("--cache-path", default=str(DEFAULT_CACHE_PATH))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    report = run_llm_cache_report(args.cache_path, Path(args.output_dir))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
