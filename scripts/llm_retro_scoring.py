"""Retro-score the Alpaca headline archive with the live LLM advisory prompt.

Turns data/news_history/ (2y x 110 tickers of headlines) into a historical
ticker-day LLM score series so LLM judgment can be tested as a rank feature
without waiting for the live cache to accumulate (would otherwise be ~2027-01).

Mirrors the live prompt from src.llm_analyst.evaluate_ticker_consensus (same
APPROVE/REJECT + CATEGORY schema, validated by the block-precision report) and
adds one OUTLOOK [-5..5] line for a graded feature. Point-in-time rule: a day's
context is the latest <=5 headlines from the prior 3 calendar days through that
day. KNOWN BIAS: the LLM's pretraining may include knowledge of what happened
after old headlines — treat backtest results as optimistic; paper A/B required
before any promotion.

Checkpointed: appends to data/research/llm_retro_scores.jsonl, one JSON per
(ticker, date); reruns skip existing keys, so interrupted runs just resume.
Work is ordered by date so partial runs still yield complete cross-sections.

Usage:
  .venv/bin/python -m scripts.llm_retro_scoring --months 6 --max-calls 1000
"""

from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

NEWS_HISTORY_DIR = Path("data/news_history")
OUTPUT_PATH = Path("data/research/llm_retro_scores.jsonl")
CONTEXT_WINDOW_DAYS = 3
MAX_HEADLINES = 5
MAX_CONSECUTIVE_FAILURES = 5

PROMPT_TEMPLATE = """
Analyze the following news headlines for the stock ticker '{ticker}' as of {date}.
Your goal is to identify critical fundamental risks that a purely quantitative model might miss (e.g., fraud, major lawsuits, catastrophic product failure, or terrible forward guidance).
Judge ONLY from the headline text below. Do not use any knowledge of what happened to this company after {date}.

News Headlines:
{news_context}

Based on these headlines, should we proceed with buying this stock?
Provide your decision in the following structured format only (no extra commentary):
DECISION: [APPROVE or REJECT]
CATEGORY: [None, Lawsuit, Fraud, Guidance, Financials, Other]
OUTLOOK: [integer from -5 (very bearish) to 5 (very bullish)]
REASON: [One sentence explanation in Korean]
"""

_OUTLOOK_RE = re.compile(r"OUTLOOK:\s*\[?\s*(-?\d+)", re.IGNORECASE)


def _load_scored_keys(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    keys = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            keys.add(json.loads(line)["key"])
        except (json.JSONDecodeError, KeyError):
            continue
    return keys


def _build_work_items(tickers: list[str], cutoff: pd.Timestamp) -> list[dict]:
    """One item per (ticker, ET date with >=1 new headline), context = trailing window."""
    items: list[dict] = []
    for ticker in tickers:
        path = NEWS_HISTORY_DIR / f"{ticker}.csv"
        if not path.is_file():
            continue
        try:
            df = pd.read_csv(path)
        except Exception:
            continue
        if df.empty or "headline" not in df.columns:
            continue
        ts = pd.to_datetime(df["created_at"], errors="coerce", utc=True)
        df = df.assign(
            ts=ts,
            et_date=ts.dt.tz_convert("US/Eastern").dt.normalize().dt.tz_localize(None),
        ).dropna(subset=["et_date", "headline"])
        df = df.sort_values("ts")
        for day, _ in df[df["et_date"] >= cutoff].groupby("et_date"):
            window = df[
                (df["et_date"] <= day)
                & (df["et_date"] >= day - pd.Timedelta(days=CONTEXT_WINDOW_DAYS))
            ]
            headlines = window["headline"].tail(MAX_HEADLINES).tolist()
            if not headlines:
                continue
            items.append(
                {
                    "ticker": ticker,
                    "date": str(day.date()),
                    "headlines": headlines,
                }
            )
    items.sort(key=lambda it: (it["date"], it["ticker"]))
    return items


def _score_item(item: dict, *, model: str | None = None) -> dict:
    from src.llm_analyst import _generate_llm_text_with_provider, parse_llm_decision

    news_context = "\n".join(f"- {h}" for h in item["headlines"])
    prompt = PROMPT_TEMPLATE.format(
        ticker=item["ticker"], date=item["date"], news_context=news_context
    )
    text, provider = _generate_llm_text_with_provider(prompt, model=model)
    approved, category, reason = parse_llm_decision(text)
    outlook = None
    match = _OUTLOOK_RE.search(text)
    if match:
        outlook = max(-5, min(5, int(match.group(1))))
    return {
        "key": f"{item['ticker']}_{item['date']}",
        "ticker": item["ticker"],
        "date": item["date"],
        "is_approved": approved,
        "category": category,
        "outlook": outlook,
        "n_headlines": len(item["headlines"]),
        "provider": provider,
        "model": model or "default",
        "reason": reason,
        "scored_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--months", type=int, default=6)
    ap.add_argument("--max-calls", type=int, default=1000)
    ap.add_argument("--sleep", type=float, default=0.4, help="seconds between calls")
    ap.add_argument("--tickers", default="", help="comma-separated subset (default: all)")
    ap.add_argument(
        "--model",
        default="gemini-2.5-flash-lite",
        help="Gemini model; per-model free-tier quota is separate from the live "
        "veto's gemini-2.5-flash, so the default avoids starving live trading",
    )
    args = ap.parse_args()

    import src.config  # noqa: F401  (load_dotenv side effect for GEMINI_API_KEY)
    from src.llm_analyst import llm_backend_available
    from src.settings import load_settings

    if not llm_backend_available():
        raise SystemExit("No LLM backend available (GEMINI_API_KEY / vLLM missing)")

    if args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    else:
        tickers = [str(t).strip().upper() for t in load_settings().tickers]

    cutoff = pd.Timestamp.now().normalize() - pd.DateOffset(months=args.months)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    scored = _load_scored_keys(OUTPUT_PATH)
    items = [
        it
        for it in _build_work_items(tickers, cutoff)
        if f"{it['ticker']}_{it['date']}" not in scored
    ]
    print(
        f"Work: {len(items):,} unscored ticker-days (cutoff {cutoff.date()}, "
        f"already scored {len(scored):,}); this run caps at {args.max_calls:,} calls"
    )

    done = failures = consecutive_failures = 0
    started = time.time()
    with OUTPUT_PATH.open("a", encoding="utf-8") as out:
        for item in items:
            if done + failures >= args.max_calls:
                break
            try:
                record = _score_item(item, model=args.model)
                consecutive_failures = 0
            except Exception as exc:
                failures += 1
                consecutive_failures += 1
                print(f"FAIL {item['ticker']}_{item['date']}: {exc}")
                if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                    print("Too many consecutive failures — stopping (resume later)")
                    break
                time.sleep(max(args.sleep, 2.0))
                continue
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            out.flush()
            done += 1
            if done % 25 == 0:
                rate = done / max(time.time() - started, 1)
                print(
                    f"progress: {done:,} scored ({failures} failed), "
                    f"{rate * 60:.0f}/min, last={record['key']}"
                )
            time.sleep(args.sleep)

    remaining = len(items) - done - failures
    print(
        f"\nDone: scored={done:,} failed={failures} remaining={remaining:,} "
        f"-> {OUTPUT_PATH} (rerun to resume)"
    )


if __name__ == "__main__":
    main()
