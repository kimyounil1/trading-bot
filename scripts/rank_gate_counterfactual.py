"""Counterfactual P&L of the rank-AI buy gate: blocked vs submitted forward returns.

Same methodology as scripts/llm_gate_counterfactual.py (whose helpers are
reused), applied to SKIP_BUY rows blocked by the rank AI gate. Because the
audit rows carry rank_ai_percentile, this also reports forward returns by
percentile bucket — a direct test of whether the cutoff (0.85) sits where
returns actually start.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from scripts.llm_gate_counterfactual import (
    DEFAULT_HORIZONS,
    _cohort_events,
    _cohort_stats,
    _load_close_series,
    _utc_now_iso,
    _welch_t,
)
from src.config import EXECUTION_AUDIT_LOG_PATH
from src.daily_audit_summary import load_execution_audit

DEFAULT_OUTPUT_DIR = Path("logs/rank_gate")

PERCENTILE_BUCKETS = ((0.0, 0.25), (0.25, 0.5), (0.5, 0.7), (0.7, 0.85))


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

    reason = df["reason"].astype(str)
    blocked_raw = df[
        (df["event_type"] == "SKIP_BUY") & reason.str.contains("rank ai gate blocked", na=False)
    ]
    missing_score = df[
        (df["event_type"] == "SKIP_BUY")
        & reason.str.contains("rank ai gate missing score", na=False)
    ]
    submitted_raw = df[df["event_type"] == "BUY_SUBMITTED"]

    blocked = _cohort_events(blocked_raw)
    submitted = _cohort_events(submitted_raw)

    spy_closes = _load_close_series("SPY")
    blocked_stats, blocked_rets, blocked_detail = _cohort_stats(blocked, horizons, spy_closes)
    submitted_stats, submitted_rets, submitted_detail = _cohort_stats(submitted, horizons, spy_closes)

    # Percentile carried onto detail rows for the bucket monotonicity check.
    pct_map = blocked.set_index(["ticker", "_et_date"])["rank_ai_percentile"]
    if not blocked_detail.empty:
        keys = pd.MultiIndex.from_arrays(
            [blocked_detail["ticker"], pd.to_datetime(blocked_detail["date"])]
        )
        blocked_detail["rank_ai_percentile"] = pct_map.reindex(keys).to_numpy()

    horizon_keys = [f"h{h}" for h in horizons] + ["to_latest"]
    diff: dict[str, Any] = {}
    clustered: dict[str, Any] = {}
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
        sub_by_ticker = (
            submitted_detail.groupby("ticker")[key].mean().dropna()
            if not submitted_detail.empty
            else pd.Series(dtype=float)
        )
        blk_by_ticker = (
            blocked_detail.groupby("ticker")[key].mean().dropna()
            if not blocked_detail.empty
            else pd.Series(dtype=float)
        )
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

    buckets: dict[str, Any] = {}
    if not blocked_detail.empty and "rank_ai_percentile" in blocked_detail.columns:
        for lo, hi in PERCENTILE_BUCKETS:
            mask = (blocked_detail["rank_ai_percentile"] >= lo) & (
                blocked_detail["rank_ai_percentile"] < hi
            )
            bucket_rows = blocked_detail[mask]
            entry: dict[str, Any] = {"events": int(len(bucket_rows))}
            for key in horizon_keys:
                vals = bucket_rows[key].dropna()
                entry[key] = {
                    "n": int(len(vals)),
                    "mean_pct": round(100 * vals.mean(), 3) if len(vals) else None,
                    "win_rate_pct": round(100 * (vals > 0).mean(), 1) if len(vals) else None,
                }
            buckets[f"pct_{lo:.2f}_{hi:.2f}"] = entry
    # Submitted cohort = the >= cutoff bucket.
    submitted_bucket: dict[str, Any] = {"events": int(len(submitted_detail))}
    for key in horizon_keys:
        vals = submitted_detail[key].dropna() if not submitted_detail.empty else pd.Series(dtype=float)
        submitted_bucket[key] = {
            "n": int(len(vals)),
            "mean_pct": round(100 * vals.mean(), 3) if len(vals) else None,
            "win_rate_pct": round(100 * (vals > 0).mean(), 1) if len(vals) else None,
        }
    buckets["pct_0.85_1.00_submitted"] = submitted_bucket

    report = {
        "generated_at": _utc_now_iso(),
        "audit_path": str(audit_path),
        "lookback_days": lookback_days,
        "horizons_trading_days": list(horizons),
        "blocked": blocked_stats,
        "submitted": submitted_stats,
        "missing_score_skips": int(len(missing_score)),
        "diff": diff,
        "diff_ticker_clustered": clustered,
        "percentile_buckets": buckets,
        "notes": [
            "Cohorts: paper env, TEST_PROFILE excluded; one event per (ticker, ET date).",
            "Entry = first cached close on/after event ET date; equal-weighted close-to-close returns.",
            "Positive diff (submitted - blocked) means the rank gate added value at that horizon.",
            "percentile_buckets tests monotonicity: returns should rise toward the 0.85 cutoff if the gate is calibrated.",
            "Submitted bucket labeled pct_0.85_1.00 is approximate — submission also required passing other gates.",
        ],
    }
    return report, blocked_detail, submitted_detail


def main() -> None:
    parser = argparse.ArgumentParser(description="Rank-AI buy-gate counterfactual forward returns")
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

    print("=== Rank gate counterfactual (equal-weight forward returns) ===")
    for cohort in ("blocked", "submitted"):
        stats = report.get(cohort, {})
        print(f"[{cohort}] events={stats.get('events')} priced={stats.get('priced_events')}")
        for key, s in stats.items():
            if isinstance(s, dict):
                print(
                    f"  {key:>9}: n={s['n']:>4} mean={s['mean_pct']}% median={s['median_pct']}% "
                    f"win={s['win_rate_pct']}% excess_spy={s['mean_excess_spy_pct']}%"
                )
    print(f"missing-score skips (separate failure mode): {report.get('missing_score_skips')}")
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
    print("[percentile buckets: mean h5 / h10]")
    for name, b in report.get("percentile_buckets", {}).items():
        h5 = b.get("h5", {})
        h10 = b.get("h10", {})
        print(
            f"  {name:>24}: events={b['events']:>4} "
            f"h5={h5.get('mean_pct')}% (n={h5.get('n')}, win={h5.get('win_rate_pct')}%) "
            f"h10={h10.get('mean_pct')}% (n={h10.get('n')}, win={h10.get('win_rate_pct')}%)"
        )
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
