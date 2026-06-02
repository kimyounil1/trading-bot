"""Measure whether LLM REJECT aligns with weaker forward returns."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import EXECUTION_AUDIT_LOG_PATH
from src.daily_audit_summary import load_execution_audit
from src.data_loader import load_price_data_batch
from src.llm_advisory_impact_report import _parse_llm_verdict

DEFAULT_OUTPUT_DIR = Path("logs/llm_advisory")
DEFAULT_OUTPUT_NAME = "precision.json"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def _stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"n": 0, "mean_return": None, "median_return": None, "hit_rate": None}
    s = pd.Series(values, dtype=float)
    return {
        "n": int(len(values)),
        "mean_return": float(s.mean()),
        "median_return": float(s.median()),
        "hit_rate": float((s > 0).mean()),
    }


def build_llm_block_precision_report(
    *,
    audit_path: str | Path = EXECUTION_AUDIT_LOG_PATH,
    lookback_days: int = 90,
    horizon_days: int = 20,
    price_period: str = "2y",
) -> dict[str, Any]:
    path = Path(audit_path)
    audit_df = (
        load_execution_audit(path, lookback_days=lookback_days) if path.is_file() else pd.DataFrame()
    )
    if audit_df.empty:
        return {
            "generated_at": _utc_now_iso(),
            "lookback_days": lookback_days,
            "horizon_days": horizon_days,
            "price_period": price_period,
            "audit_rows": 0,
            "events_used": {"llm_reject": 0, "llm_accept": 0},
            "forward_return": {
                "llm_reject": _stats([]),
                "llm_accept": _stats([]),
                "delta_mean_accept_minus_reject": None,
                "delta_hit_rate_accept_minus_reject": None,
            },
            "excluded_rows": {"missing_price_data": 0, "insufficient_forward_bars": 0, "other": 0},
            "notes": ["No execution_audit rows in lookback window."],
        }

    df = audit_df.copy()
    df["event_type"] = df.get("event_type", "").astype(str)
    df["timestamp"] = pd.to_datetime(df.get("timestamp"), errors="coerce", utc=True)
    df["ticker"] = df.get("ticker", "").astype(str).str.upper()
    df["llm_side"] = df.get("llm_verdict", "").map(lambda raw: _parse_llm_verdict(raw)[0])
    df = df[
        (df["event_type"] == "BUY_SUBMITTED")
        & df["timestamp"].notna()
        & df["ticker"].ne("")
        & df["llm_side"].isin(["REJECT", "ACCEPT"])
    ].copy()
    if df.empty:
        return {
            "generated_at": _utc_now_iso(),
            "lookback_days": lookback_days,
            "horizon_days": horizon_days,
            "price_period": price_period,
            "audit_rows": int(len(audit_df)),
            "events_used": {"llm_reject": 0, "llm_accept": 0},
            "forward_return": {
                "llm_reject": _stats([]),
                "llm_accept": _stats([]),
                "delta_mean_accept_minus_reject": None,
                "delta_hit_rate_accept_minus_reject": None,
            },
            "excluded_rows": {"missing_price_data": 0, "insufficient_forward_bars": 0, "other": 0},
            "notes": ["No BUY_SUBMITTED rows with parsed LLM ACCEPT/REJECT verdicts."],
        }

    prices = load_price_data_batch(
        sorted(df["ticker"].unique().tolist()),
        period=price_period,
        force_refresh=False,
    )
    price_map = {ticker: _prepare_price_frame(px_df) for ticker, px_df in prices.items()}

    grouped: dict[str, list[float]] = {"REJECT": [], "ACCEPT": []}
    excluded = {"missing_price_data": 0, "insufficient_forward_bars": 0, "other": 0}
    sample: list[dict[str, Any]] = []

    for _, row in df.iterrows():
        llm_side = str(row["llm_side"])
        ticker = str(row["ticker"])
        price_df = price_map.get(ticker, pd.DataFrame(columns=["date", "px"]))
        fwd, why = _forward_return(price_df, row["timestamp"], horizon_days)
        if fwd is None:
            if why in excluded:
                excluded[why] += 1
            else:
                excluded["other"] += 1
            continue
        grouped[llm_side].append(float(fwd))
        if len(sample) < 15:
            sample.append(
                {
                    "ticker": ticker,
                    "timestamp": pd.Timestamp(row["timestamp"]).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "llm_side": llm_side,
                    "forward_return": float(fwd),
                }
            )

    reject_stats = _stats(grouped["REJECT"])
    accept_stats = _stats(grouped["ACCEPT"])
    delta_mean = None
    if reject_stats["mean_return"] is not None and accept_stats["mean_return"] is not None:
        delta_mean = float(accept_stats["mean_return"] - reject_stats["mean_return"])
    delta_hit = None
    if reject_stats["hit_rate"] is not None and accept_stats["hit_rate"] is not None:
        delta_hit = float(accept_stats["hit_rate"] - reject_stats["hit_rate"])

    notes: list[str] = []
    if reject_stats["n"] == 0 or accept_stats["n"] == 0:
        notes.append(
            "One side has zero usable forward returns; increase lookback or accumulate more advisory decisions."
        )

    return {
        "generated_at": _utc_now_iso(),
        "lookback_days": lookback_days,
        "horizon_days": horizon_days,
        "price_period": price_period,
        "audit_rows": int(len(audit_df)),
        "events_used": {
            "llm_reject": int(len(grouped["REJECT"])),
            "llm_accept": int(len(grouped["ACCEPT"])),
        },
        "forward_return": {
            "llm_reject": reject_stats,
            "llm_accept": accept_stats,
            "delta_mean_accept_minus_reject": delta_mean,
            "delta_hit_rate_accept_minus_reject": delta_hit,
        },
        "excluded_rows": excluded,
        "sample": sample,
        "notes": notes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM REJECT precision via forward returns")
    parser.add_argument("--audit-path", default=EXECUTION_AUDIT_LOG_PATH)
    parser.add_argument("--lookback-days", type=int, default=90)
    parser.add_argument("--horizon-days", type=int, default=20)
    parser.add_argument("--price-period", default="2y")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    report = build_llm_block_precision_report(
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
    print("=== LLM block precision (forward return) ===")
    print(f"events used: reject={report['events_used']['llm_reject']} accept={report['events_used']['llm_accept']}")
    print(
        f"mean return (reject/accept): {fr['llm_reject']['mean_return']} / {fr['llm_accept']['mean_return']}"
    )
    print(f"delta mean (accept-reject): {fr['delta_mean_accept_minus_reject']}")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
