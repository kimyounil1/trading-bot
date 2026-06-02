"""Rank gate attribution: compare blocked vs passed 20d forward returns."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import EXECUTION_AUDIT_LOG_PATH
from src.daily_audit_summary import load_execution_audit
from src.data_loader import load_price_data_batch
from src.settings import load_settings

DEFAULT_OUTPUT_DIR = Path("logs/rank_ai_gate")
DEFAULT_OUTPUT_NAME = "forward_return.json"

_RANK_BLOCKED_RE = re.compile(r"rank ai gate blocked", re.IGNORECASE)
_RANK_PASSED_RE = re.compile(r"rank ai gate passed", re.IGNORECASE)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_float(value: Any) -> float | None:
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(num):
        return None
    return num


def _classify_group(row: pd.Series, cutoff: float) -> str | None:
    event_type = str(row.get("event_type", ""))
    reason = str(row.get("reason", ""))
    pct = _safe_float(row.get("rank_ai_percentile"))
    if event_type == "SKIP_BUY" and (
        _RANK_BLOCKED_RE.search(reason) or (pct is not None and pct < cutoff)
    ):
        return "blocked"
    if event_type == "BUY_SUBMITTED" and (
        _RANK_PASSED_RE.search(reason) or (pct is not None and pct >= cutoff)
    ):
        return "passed"
    return None


def _prepare_price_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["date"] = pd.to_datetime(out.get("date"), errors="coerce")
    out = out[out["date"].notna()].sort_values("date")
    if "adj_close" in out.columns:
        out["px"] = pd.to_numeric(out["adj_close"], errors="coerce")
    else:
        out["px"] = pd.to_numeric(out.get("close"), errors="coerce")
    out = out[out["px"].notna()]
    return out[["date", "px"]]


def _forward_return(
    price_df: pd.DataFrame,
    event_ts: pd.Timestamp,
    horizon: int,
) -> tuple[float | None, str | None]:
    if price_df.empty:
        return None, "missing_price_rows"
    base_date = pd.Timestamp(event_ts).tz_localize(None).normalize()
    dates = price_df["date"]
    pos = dates.searchsorted(base_date, side="left")
    if pos >= len(price_df):
        return None, "event_after_price_range"
    end_pos = int(pos + horizon)
    if end_pos >= len(price_df):
        return None, "insufficient_forward_bars"
    base_px = float(price_df.iloc[pos]["px"])
    end_px = float(price_df.iloc[end_pos]["px"])
    if base_px <= 0:
        return None, "invalid_base_price"
    return (end_px / base_px) - 1.0, None


def _group_stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {
            "n": 0,
            "mean_return": None,
            "median_return": None,
            "hit_rate": None,
        }
    series = pd.Series(values, dtype=float)
    return {
        "n": int(len(values)),
        "mean_return": float(series.mean()),
        "median_return": float(series.median()),
        "hit_rate": float((series > 0).mean()),
    }


def build_rank_gate_forward_return_report(
    *,
    audit_path: str | Path = EXECUTION_AUDIT_LOG_PATH,
    lookback_days: int = 90,
    horizon_days: int = 20,
    price_period: str = "2y",
) -> dict[str, Any]:
    settings = load_settings()
    cutoff = float(getattr(settings, "rank_ai_buy_gate_min_score_quantile", 0.85))
    gate_enabled = bool(getattr(settings, "rank_ai_buy_gate_enabled", False))

    audit_file = Path(audit_path)
    audit_df = (
        load_execution_audit(audit_file, lookback_days=lookback_days)
        if audit_file.is_file()
        else pd.DataFrame()
    )

    if audit_df.empty:
        return {
            "generated_at": _utc_now_iso(),
            "lookback_days": lookback_days,
            "horizon_days": horizon_days,
            "price_period": price_period,
            "gate_enabled": gate_enabled,
            "min_score_quantile": cutoff,
            "audit_rows": 0,
            "events_used": {"blocked": 0, "passed": 0},
            "forward_return": {
                "blocked": _group_stats([]),
                "passed": _group_stats([]),
                "delta_mean_passed_minus_blocked": None,
                "delta_hit_rate_passed_minus_blocked": None,
            },
            "excluded_rows": {"missing_price_data": 0, "insufficient_forward_bars": 0, "other": 0},
            "notes": ["No audit rows in lookback window."],
        }

    df = audit_df.copy()
    df["ticker"] = df.get("ticker", "").astype(str).str.upper()
    df["timestamp"] = pd.to_datetime(df.get("timestamp"), errors="coerce", utc=True)
    df["group"] = df.apply(lambda row: _classify_group(row, cutoff=cutoff), axis=1)
    df = df[df["group"].notna() & df["timestamp"].notna() & df["ticker"].ne("")]
    if df.empty:
        return {
            "generated_at": _utc_now_iso(),
            "lookback_days": lookback_days,
            "horizon_days": horizon_days,
            "price_period": price_period,
            "gate_enabled": gate_enabled,
            "min_score_quantile": cutoff,
            "audit_rows": int(len(audit_df)),
            "events_used": {"blocked": 0, "passed": 0},
            "forward_return": {
                "blocked": _group_stats([]),
                "passed": _group_stats([]),
                "delta_mean_passed_minus_blocked": None,
                "delta_hit_rate_passed_minus_blocked": None,
            },
            "excluded_rows": {"missing_price_data": 0, "insufficient_forward_bars": 0, "other": 0},
            "notes": [
                "No rank blocked/passed events matched criteria. Ensure audit contains rank gate reasons.",
            ],
        }

    tickers = sorted(df["ticker"].unique().tolist())
    prices = load_price_data_batch(tickers, period=price_period, force_refresh=False)
    price_map = {ticker: _prepare_price_frame(px_df) for ticker, px_df in prices.items()}

    grouped_returns: dict[str, list[float]] = {"blocked": [], "passed": []}
    excluded = {"missing_price_data": 0, "insufficient_forward_bars": 0, "other": 0}
    samples: list[dict[str, Any]] = []

    for _, row in df.iterrows():
        ticker = str(row["ticker"])
        group = str(row["group"])
        price_df = price_map.get(ticker, pd.DataFrame(columns=["date", "px"]))
        fwd, why = _forward_return(price_df, row["timestamp"], horizon_days)
        if fwd is None:
            if why in excluded:
                excluded[why] += 1
            else:
                excluded["other"] += 1
            continue
        grouped_returns[group].append(float(fwd))
        if len(samples) < 15:
            samples.append(
                {
                    "ticker": ticker,
                    "event_type": str(row.get("event_type", "")),
                    "group": group,
                    "timestamp": pd.Timestamp(row["timestamp"]).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "forward_return": float(fwd),
                }
            )

    blocked_stats = _group_stats(grouped_returns["blocked"])
    passed_stats = _group_stats(grouped_returns["passed"])
    delta_mean = None
    if blocked_stats["mean_return"] is not None and passed_stats["mean_return"] is not None:
        delta_mean = float(passed_stats["mean_return"] - blocked_stats["mean_return"])
    delta_hit = None
    if blocked_stats["hit_rate"] is not None and passed_stats["hit_rate"] is not None:
        delta_hit = float(passed_stats["hit_rate"] - blocked_stats["hit_rate"])

    notes: list[str] = []
    if not gate_enabled:
        notes.append("rank_ai_buy_gate_enabled is false; report is informational only.")
    if passed_stats["n"] == 0 or blocked_stats["n"] == 0:
        notes.append(
            "One side has zero usable forward returns; increase lookback or ensure rank gate events accumulate."
        )

    return {
        "generated_at": _utc_now_iso(),
        "lookback_days": lookback_days,
        "horizon_days": horizon_days,
        "price_period": price_period,
        "gate_enabled": gate_enabled,
        "min_score_quantile": cutoff,
        "audit_rows": int(len(audit_df)),
        "events_used": {
            "blocked": int(len(grouped_returns["blocked"])),
            "passed": int(len(grouped_returns["passed"])),
        },
        "forward_return": {
            "blocked": blocked_stats,
            "passed": passed_stats,
            "delta_mean_passed_minus_blocked": delta_mean,
            "delta_hit_rate_passed_minus_blocked": delta_hit,
        },
        "excluded_rows": excluded,
        "sample": samples,
        "notes": notes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rank gate blocked vs passed forward-return attribution"
    )
    parser.add_argument("--audit-path", default=EXECUTION_AUDIT_LOG_PATH)
    parser.add_argument("--lookback-days", type=int, default=90)
    parser.add_argument("--horizon-days", type=int, default=20)
    parser.add_argument("--price-period", default="2y")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    report = build_rank_gate_forward_return_report(
        audit_path=args.audit_path,
        lookback_days=args.lookback_days,
        horizon_days=args.horizon_days,
        price_period=args.price_period,
    )
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / DEFAULT_OUTPUT_NAME
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    fr = report["forward_return"]
    print("=== Rank gate forward-return attribution ===")
    print(f"events used: blocked={report['events_used']['blocked']} passed={report['events_used']['passed']}")
    print(
        f"mean return (blocked/passed): {fr['blocked']['mean_return']} / {fr['passed']['mean_return']}"
    )
    print(f"delta mean (passed-blocked): {fr['delta_mean_passed_minus_blocked']}")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
