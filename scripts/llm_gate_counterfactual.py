"""Counterfactual P&L of LLM buy-gate: blocked vs submitted forward returns.

Answers "does the LLM gate protect or burn money?" by comparing forward
returns of buys the LLM blocked (SKIP_BUY reason contains "LLM Reject")
against buys actually submitted, using the local price cache (data/raw).

Equal-weighted per unique (ticker, US/Eastern date) event; returns are
close-to-close at fixed horizons plus entry-to-latest, with SPY excess.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import EXECUTION_AUDIT_LOG_PATH
from src.daily_audit_summary import load_execution_audit

DEFAULT_OUTPUT_DIR = Path("logs/llm_advisory")
RAW_DATA_DIR = Path("data/raw")
DEFAULT_HORIZONS = (5, 10, 20)

_CATEGORY_WORDS = ("Lawsuit", "Fraud", "Guidance", "Financials", "Product", "Other", "None")
_TEMPLATE_LEAK = "None, Lawsuit, Fraud"


def _load_close_series(ticker: str) -> pd.Series | None:
    for fname in ("1y.csv", "2y.csv"):
        path = RAW_DATA_DIR / ticker / fname
        if not path.is_file():
            continue
        try:
            df = pd.read_csv(path, parse_dates=["date"])
        except (ValueError, pd.errors.ParserError):
            continue
        col = "adj_close" if "adj_close" in df.columns else "close"
        series = df.set_index("date")[col].dropna()
        if not series.empty:
            return series
    return None


def _forward_return(closes: pd.Series, entry_date: pd.Timestamp, horizon: int | None) -> float | None:
    """Return from first close on/after entry_date to `horizon` trading days later (None = latest)."""
    pos = closes.index.searchsorted(entry_date)
    if pos >= len(closes):
        return None
    entry = closes.iloc[pos]
    if horizon is None:
        exit_pos = len(closes) - 1
        if exit_pos <= pos:
            return None
    else:
        exit_pos = pos + horizon
        if exit_pos >= len(closes):
            return None
    return float(closes.iloc[exit_pos] / entry - 1.0)


def _blocked_category(reason: str) -> str:
    match = re.search(r"LLM Reject:\s*\[(.{0,120})", str(reason or ""))
    if not match:
        return "unparsed"
    head = match.group(1)
    if _TEMPLATE_LEAK in head:
        return "template_leak"
    for word in _CATEGORY_WORDS:
        if word in head:
            return word
    return "unparsed"


def _welch_t(a: list[float], b: list[float]) -> float | None:
    if len(a) < 2 or len(b) < 2:
        return None
    sa = pd.Series(a)
    sb = pd.Series(b)
    va, vb = sa.var(ddof=1) / len(a), sb.var(ddof=1) / len(b)
    denom = math.sqrt(va + vb)
    if denom == 0:
        return None
    return float((sa.mean() - sb.mean()) / denom)


def _cohort_events(df: pd.DataFrame) -> pd.DataFrame:
    """Dedupe to one event per (ticker, US/Eastern date)."""
    ts = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    out = df.assign(_et_date=ts.dt.tz_convert("America/New_York").dt.normalize().dt.tz_localize(None))
    out = out.dropna(subset=["_et_date"])
    return out.sort_values("timestamp").groupby(["ticker", "_et_date"], as_index=False).first()


def _cohort_stats(
    events: pd.DataFrame,
    horizons: tuple[int, ...],
    spy_closes: pd.Series | None,
) -> tuple[dict[str, Any], dict[str, list[float]], pd.DataFrame]:
    closes_cache: dict[str, pd.Series | None] = {}
    horizon_keys = [f"h{h}" for h in horizons] + ["to_latest"]
    returns: dict[str, list[float]] = {k: [] for k in horizon_keys}
    excess: dict[str, list[float]] = {k: [] for k in horizon_keys}
    rows: list[dict[str, Any]] = []

    for _, ev in events.iterrows():
        ticker = str(ev["ticker"])
        if ticker not in closes_cache:
            closes_cache[ticker] = _load_close_series(ticker)
        closes = closes_cache[ticker]
        if closes is None:
            continue
        entry_date = ev["_et_date"]
        row: dict[str, Any] = {"ticker": ticker, "date": entry_date.date().isoformat()}
        for key, h in zip(horizon_keys, list(horizons) + [None]):
            ret = _forward_return(closes, entry_date, h)
            row[key] = ret
            if ret is None:
                continue
            returns[key].append(ret)
            if spy_closes is not None:
                spy_ret = _forward_return(spy_closes, entry_date, h)
                if spy_ret is not None:
                    excess[key].append(ret - spy_ret)
        rows.append(row)

    stats: dict[str, Any] = {"events": int(len(events)), "priced_events": len(rows)}
    for key in horizon_keys:
        vals = returns[key]
        stats[key] = {
            "n": len(vals),
            "mean_pct": round(100 * pd.Series(vals).mean(), 3) if vals else None,
            "median_pct": round(100 * pd.Series(vals).median(), 3) if vals else None,
            "win_rate_pct": round(100 * sum(v > 0 for v in vals) / len(vals), 1) if vals else None,
            "mean_excess_spy_pct": (
                round(100 * pd.Series(excess[key]).mean(), 3) if excess[key] else None
            ),
        }
    return stats, returns, pd.DataFrame(rows)


def build_counterfactual_report(
    audit_path: str | Path = EXECUTION_AUDIT_LOG_PATH,
    lookback_days: int = 90,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame]:
    df = load_execution_audit(audit_path, lookback_days=lookback_days)
    if df.empty:
        return (
            {"generated_at": _utc_now_iso(), "rows": 0, "notes": ["No execution_audit rows."]},
            pd.DataFrame(),
            pd.DataFrame(),
        )

    df = df[df["environment"] == "paper"]
    df = df[df["profile_name"] != "TEST_PROFILE"]

    blocked_raw = df[
        (df["event_type"] == "SKIP_BUY")
        & (df["reason"].astype(str).str.contains("LLM Reject", case=False, na=False))
    ]
    submitted_raw = df[df["event_type"] == "BUY_SUBMITTED"]

    blocked = _cohort_events(blocked_raw)
    submitted = _cohort_events(submitted_raw)

    spy_closes = _load_close_series("SPY")
    blocked_stats, blocked_rets, blocked_detail = _cohort_stats(blocked, horizons, spy_closes)
    submitted_stats, submitted_rets, submitted_detail = _cohort_stats(submitted, horizons, spy_closes)

    horizon_keys = [f"h{h}" for h in horizons] + ["to_latest"]
    diff: dict[str, Any] = {}
    for key in horizon_keys:
        sub_vals, blk_vals = submitted_rets[key], blocked_rets[key]
        if sub_vals and blk_vals:
            diff[key] = {
                "submitted_minus_blocked_mean_pct": round(
                    100 * (pd.Series(sub_vals).mean() - pd.Series(blk_vals).mean()), 3
                ),
                "welch_t": (lambda t: round(t, 2) if t is not None else None)(
                    _welch_t(sub_vals, blk_vals)
                ),
            }

    # Same-ticker daily re-entries are serially correlated; clustering by ticker
    # (mean return per ticker, then compare) is the honest significance test.
    clustered: dict[str, Any] = {}
    for key in horizon_keys:
        sub_by_ticker = submitted_detail.groupby("ticker")[key].mean().dropna() if not submitted_detail.empty else pd.Series(dtype=float)
        blk_by_ticker = blocked_detail.groupby("ticker")[key].mean().dropna() if not blocked_detail.empty else pd.Series(dtype=float)
        if len(sub_by_ticker) >= 2 and len(blk_by_ticker) >= 2:
            clustered[key] = {
                "submitted_n_tickers": int(len(sub_by_ticker)),
                "submitted_mean_pct": round(100 * sub_by_ticker.mean(), 3),
                "blocked_n_tickers": int(len(blk_by_ticker)),
                "blocked_mean_pct": round(100 * blk_by_ticker.mean(), 3),
                "diff_pct": round(100 * (sub_by_ticker.mean() - blk_by_ticker.mean()), 3),
                "welch_t": (lambda t: round(t, 2) if t is not None else None)(
                    _welch_t(list(sub_by_ticker), list(blk_by_ticker))
                ),
            }

    cats = blocked_raw["reason"].astype(str).map(_blocked_category)
    category_counts = cats.value_counts().to_dict()

    report = {
        "generated_at": _utc_now_iso(),
        "audit_path": str(audit_path),
        "lookback_days": lookback_days,
        "horizons_trading_days": list(horizons),
        "blocked": blocked_stats,
        "submitted": submitted_stats,
        "diff": diff,
        "diff_ticker_clustered": clustered,
        "blocked_category_counts": category_counts,
        "notes": [
            "Cohorts: paper env, TEST_PROFILE excluded; one event per (ticker, ET date).",
            "Entry = first cached close on/after event ET date; equal-weighted close-to-close returns.",
            "Positive diff (submitted - blocked) means the LLM gate added value at that horizon.",
            "Repeated daily blocks of the same ticker are serially correlated — treat t-stats as optimistic.",
        ],
    }
    return report, blocked_detail, submitted_detail


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM buy-gate counterfactual forward returns")
    parser.add_argument("--audit-path", default=EXECUTION_AUDIT_LOG_PATH)
    parser.add_argument("--lookback-days", type=int, default=90)
    parser.add_argument("--horizons", default="5,10,20", help="comma-separated trading-day horizons")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    horizons = tuple(int(h) for h in args.horizons.split(",") if h.strip())
    report, blocked_detail, submitted_detail = build_counterfactual_report(
        args.audit_path, lookback_days=args.lookback_days, horizons=horizons
    )

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "counterfactual_summary.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    if not blocked_detail.empty:
        blocked_detail.to_csv(out_dir / "counterfactual_blocked_events.csv", index=False)
    if not submitted_detail.empty:
        submitted_detail.to_csv(out_dir / "counterfactual_submitted_events.csv", index=False)

    print("=== LLM gate counterfactual (equal-weight forward returns) ===")
    for cohort in ("blocked", "submitted"):
        stats = report.get(cohort, {})
        print(f"[{cohort}] events={stats.get('events')} priced={stats.get('priced_events')}")
        for key, s in stats.items():
            if isinstance(s, dict):
                print(
                    f"  {key:>9}: n={s['n']:>3} mean={s['mean_pct']}% median={s['median_pct']}% "
                    f"win={s['win_rate_pct']}% excess_spy={s['mean_excess_spy_pct']}%"
                )
    print("[diff submitted - blocked]")
    for key, d in report.get("diff", {}).items():
        print(f"  {key:>9}: {d['submitted_minus_blocked_mean_pct']}%p (welch_t={d['welch_t']})")
    print("[diff ticker-clustered]")
    for key, d in report.get("diff_ticker_clustered", {}).items():
        print(
            f"  {key:>9}: sub {d['submitted_mean_pct']}% (n={d['submitted_n_tickers']}) vs "
            f"blk {d['blocked_mean_pct']}% (n={d['blocked_n_tickers']}) -> "
            f"{d['diff_pct']}%p (welch_t={d['welch_t']})"
        )
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
