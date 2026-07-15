"""Counterfactual P&L of crowding/sector guards: blocked vs submitted forward returns.

Same methodology as scripts/llm_gate_counterfactual.py (helpers reused), applied
to SKIP_BUY rows blocked by the momentum-crowding and sector-concentration
guards — the two largest non-rank filters in the buy funnel. Complements the
one-off exp_guard_relaxation_2w sweep with a 90d window, SPY excess, and
ticker-clustered t-stats refreshed by daily ops.
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

DEFAULT_OUTPUT_DIR = Path("logs/guard_gates")

GUARD_PATTERNS = {
    "crowding": "momentum crowding limit reached",
    "sector": "sector concentration limit reached",
}


def _diff_stats(
    submitted_detail: pd.DataFrame,
    blocked_detail: pd.DataFrame,
    horizon_keys: list[str],
) -> dict[str, Any]:
    clustered: dict[str, Any] = {}
    for key in horizon_keys:
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
    return clustered


def build_counterfactual_report(
    audit_path: str | Path = EXECUTION_AUDIT_LOG_PATH,
    lookback_days: int = 90,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
) -> tuple[dict[str, Any], dict[str, pd.DataFrame]]:
    df = load_execution_audit(audit_path, lookback_days=lookback_days)
    if df.empty:
        return (
            {"generated_at": _utc_now_iso(), "rows": 0, "notes": ["No execution_audit rows."]},
            {},
        )

    df = df[df["environment"] == "paper"]
    df = df[df["profile_name"] != "TEST_PROFILE"]
    reason = df["reason"].astype(str)

    submitted = _cohort_events(df[df["event_type"] == "BUY_SUBMITTED"])
    spy_closes = _load_close_series("SPY")
    horizon_keys = [f"h{h}" for h in horizons] + ["to_latest"]
    submitted_stats, _, submitted_detail = _cohort_stats(submitted, horizons, spy_closes)

    report: dict[str, Any] = {
        "generated_at": _utc_now_iso(),
        "audit_path": str(audit_path),
        "lookback_days": lookback_days,
        "horizons_trading_days": list(horizons),
        "submitted": submitted_stats,
        "guards": {},
        "notes": [
            "Cohorts: paper env, TEST_PROFILE excluded; one event per (ticker, ET date).",
            "Entry = first cached close on/after event ET date; equal-weighted close-to-close returns.",
            "Positive clustered diff (submitted - blocked) means the guard added value at that horizon.",
            "Guards fire at different funnel depths than the rank/LLM gates — compare guards to each other with care.",
            "Complements exp_guard_relaxation_2w (portfolio-level scenario sweep, one-off).",
        ],
    }

    details: dict[str, pd.DataFrame] = {"submitted": submitted_detail}
    for guard, pattern in GUARD_PATTERNS.items():
        blocked_raw = df[(df["event_type"] == "SKIP_BUY") & reason.str.contains(pattern, na=False)]
        blocked = _cohort_events(blocked_raw)
        blocked_stats, _, blocked_detail = _cohort_stats(blocked, horizons, spy_closes)
        report["guards"][guard] = {
            "skip_rows": int(len(blocked_raw)),
            "blocked": blocked_stats,
            "diff_ticker_clustered": _diff_stats(submitted_detail, blocked_detail, horizon_keys),
        }
        details[guard] = blocked_detail

    return report, details


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Crowding/sector guard counterfactual forward returns"
    )
    parser.add_argument("--audit-path", default=EXECUTION_AUDIT_LOG_PATH)
    parser.add_argument("--lookback-days", type=int, default=90)
    parser.add_argument("--horizons", default="5,10,20", help="comma-separated trading-day horizons")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    horizons = tuple(int(h) for h in args.horizons.split(",") if h.strip())
    report, details = build_counterfactual_report(
        args.audit_path, lookback_days=args.lookback_days, horizons=horizons
    )

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "counterfactual_summary.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    for name, detail in details.items():
        if not detail.empty:
            detail.to_csv(out_dir / f"counterfactual_{name}_events.csv", index=False)

    print("=== Guard counterfactual (equal-weight forward returns) ===")
    sub = report.get("submitted", {})
    print(f"[submitted] events={sub.get('events')} priced={sub.get('priced_events')}")
    for guard, payload in report.get("guards", {}).items():
        blocked = payload.get("blocked", {})
        print(
            f"[{guard}] skip_rows={payload.get('skip_rows')} "
            f"events={blocked.get('events')} priced={blocked.get('priced_events')}"
        )
        for key, s in blocked.items():
            if isinstance(s, dict):
                print(
                    f"  {key:>9}: n={s['n']:>4} mean={s['mean_pct']}% "
                    f"win={s['win_rate_pct']}% excess_spy={s['mean_excess_spy_pct']}%"
                )
        for key, d in payload.get("diff_ticker_clustered", {}).items():
            print(
                f"  clustered {key:>9}: sub {d['submitted_mean_pct']}% vs "
                f"blk {d['blocked_mean_pct']}% -> {d['diff_pct']}%p (welch_t={d['welch_t']})"
            )
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
