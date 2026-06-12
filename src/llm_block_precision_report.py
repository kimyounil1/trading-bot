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

# LLM decision events: advisory mode logs LLM_ADVISORY (WOULD_REJECT) and the buy
# still goes through BUY_SUBMITTED; blocking mode logs the reject as SKIP_BUY.
LLM_DECISION_EVENT_TYPES = ("LLM_ADVISORY", "SKIP_BUY", "BUY_SUBMITTED")


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
        return None, "missing_price_data"
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


def _forward_return_block(reject: list[float], accept: list[float]) -> dict[str, Any]:
    reject_stats = _stats(reject)
    accept_stats = _stats(accept)
    delta_mean = None
    if reject_stats["mean_return"] is not None and accept_stats["mean_return"] is not None:
        delta_mean = float(accept_stats["mean_return"] - reject_stats["mean_return"])
    delta_hit = None
    if reject_stats["hit_rate"] is not None and accept_stats["hit_rate"] is not None:
        delta_hit = float(accept_stats["hit_rate"] - reject_stats["hit_rate"])
    return {
        "llm_reject": reject_stats,
        "llm_accept": accept_stats,
        "delta_mean_accept_minus_reject": delta_mean,
        "delta_hit_rate_accept_minus_reject": delta_hit,
    }


def build_llm_block_precision_report(
    *,
    audit_path: str | Path = EXECUTION_AUDIT_LOG_PATH,
    lookback_days: int = 90,
    horizon_days: int = 20,
    short_horizon_days: int = 5,
    price_period: str = "2y",
) -> dict[str, Any]:
    def _empty_report(audit_rows: int, note: str) -> dict[str, Any]:
        return {
            "generated_at": _utc_now_iso(),
            "lookback_days": lookback_days,
            "horizon_days": horizon_days,
            "short_horizon_days": short_horizon_days,
            "price_period": price_period,
            "audit_rows": audit_rows,
            "events_used": {"llm_reject": 0, "llm_accept": 0},
            "events_by_type": {},
            "forward_return": _forward_return_block([], []),
            "forward_return_short": _forward_return_block([], []),
            "excluded_rows": {"missing_price_data": 0, "insufficient_forward_bars": 0, "other": 0},
            "notes": [note],
        }

    path = Path(audit_path)
    audit_df = (
        load_execution_audit(path, lookback_days=lookback_days) if path.is_file() else pd.DataFrame()
    )
    if audit_df.empty:
        return _empty_report(0, "No execution_audit rows in lookback window.")

    df = audit_df.copy()
    df["event_type"] = df.get("event_type", "").astype(str)
    df["timestamp"] = pd.to_datetime(df.get("timestamp"), errors="coerce", utc=True)
    df["ticker"] = df.get("ticker", "").astype(str).str.upper()
    df["llm_side"] = df.get("llm_verdict", "").map(lambda raw: _parse_llm_verdict(raw)[0])
    df = df[
        df["event_type"].isin(LLM_DECISION_EVENT_TYPES)
        & df["timestamp"].notna()
        & df["ticker"].ne("")
        & df["llm_side"].isin(["REJECT", "ACCEPT"])
    ].copy()
    # Same ticker re-evaluated within a day shares the forward return; keep one row.
    df["event_date"] = df["timestamp"].dt.normalize()
    df = df.drop_duplicates(subset=["ticker", "event_date", "llm_side"])
    events_by_type = {
        event_type: int(count) for event_type, count in df["event_type"].value_counts().items()
    }
    if df.empty:
        return _empty_report(
            int(len(audit_df)),
            "No LLM decision rows (LLM_ADVISORY/SKIP_BUY/BUY_SUBMITTED) with parsed ACCEPT/REJECT verdicts.",
        )

    prices = load_price_data_batch(
        sorted(df["ticker"].unique().tolist()),
        period=price_period,
        force_refresh=False,
    )
    price_map = {ticker: _prepare_price_frame(px_df) for ticker, px_df in prices.items()}

    horizon_specs: dict[str, int] = {"primary": horizon_days}
    if short_horizon_days and 0 < short_horizon_days < horizon_days:
        horizon_specs["short"] = short_horizon_days

    grouped: dict[str, dict[str, list[float]]] = {
        name: {"REJECT": [], "ACCEPT": []} for name in horizon_specs
    }
    excluded = {
        name: {"missing_price_data": 0, "insufficient_forward_bars": 0, "other": 0}
        for name in horizon_specs
    }
    sample: list[dict[str, Any]] = []

    for _, row in df.iterrows():
        llm_side = str(row["llm_side"])
        ticker = str(row["ticker"])
        price_df = price_map.get(ticker, pd.DataFrame(columns=["date", "px"]))
        for name, horizon in horizon_specs.items():
            fwd, why = _forward_return(price_df, row["timestamp"], horizon)
            if fwd is None:
                if why in excluded[name]:
                    excluded[name][why] += 1
                else:
                    excluded[name]["other"] += 1
                continue
            grouped[name][llm_side].append(float(fwd))
            if name == "primary" and len(sample) < 15:
                sample.append(
                    {
                        "ticker": ticker,
                        "timestamp": pd.Timestamp(row["timestamp"]).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "llm_side": llm_side,
                        "forward_return": float(fwd),
                    }
                )

    primary = _forward_return_block(grouped["primary"]["REJECT"], grouped["primary"]["ACCEPT"])
    gate_name = "short" if "short" in horizon_specs else "primary"
    short = (
        _forward_return_block(grouped["short"]["REJECT"], grouped["short"]["ACCEPT"])
        if "short" in horizon_specs
        else _forward_return_block([], [])
    )
    gate_block = short if gate_name == "short" else primary

    notes: list[str] = [
        f"events_used counts matured forward returns at the {horizon_specs[gate_name]}d horizon "
        "(shortest configured); primary-horizon stats fill in as events age."
    ]
    if primary["llm_reject"]["n"] == 0 or primary["llm_accept"]["n"] == 0:
        notes.append(
            "One side has zero usable forward returns at the primary horizon; "
            "increase lookback or accumulate more advisory decisions."
        )

    return {
        "generated_at": _utc_now_iso(),
        "lookback_days": lookback_days,
        "horizon_days": horizon_days,
        "short_horizon_days": horizon_specs.get("short"),
        "price_period": price_period,
        "audit_rows": int(len(audit_df)),
        "events_used": {
            "llm_reject": gate_block["llm_reject"]["n"],
            "llm_accept": gate_block["llm_accept"]["n"],
        },
        "events_by_type": events_by_type,
        "forward_return": primary,
        "forward_return_short": short,
        "excluded_rows": excluded["primary"],
        "excluded_rows_short": excluded.get("short"),
        "sample": sample,
        "notes": notes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM REJECT precision via forward returns")
    parser.add_argument("--audit-path", default=EXECUTION_AUDIT_LOG_PATH)
    parser.add_argument("--lookback-days", type=int, default=90)
    parser.add_argument("--horizon-days", type=int, default=20)
    parser.add_argument("--short-horizon-days", type=int, default=5)
    parser.add_argument("--price-period", default="2y")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    report = build_llm_block_precision_report(
        audit_path=args.audit_path,
        lookback_days=args.lookback_days,
        horizon_days=args.horizon_days,
        short_horizon_days=args.short_horizon_days,
        price_period=args.price_period,
    )
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / DEFAULT_OUTPUT_NAME
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    fr = report["forward_return"]
    fr_short = report.get("forward_return_short") or {}
    print("=== LLM block precision (forward return) ===")
    print(f"events used: reject={report['events_used']['llm_reject']} accept={report['events_used']['llm_accept']}")
    print(
        f"mean return {report['horizon_days']}d (reject/accept): "
        f"{fr['llm_reject']['mean_return']} / {fr['llm_accept']['mean_return']}"
    )
    if report.get("short_horizon_days"):
        print(
            f"mean return {report['short_horizon_days']}d (reject/accept): "
            f"{(fr_short.get('llm_reject') or {}).get('mean_return')} / "
            f"{(fr_short.get('llm_accept') or {}).get('mean_return')}"
        )
    print(f"delta mean (accept-reject): {fr['delta_mean_accept_minus_reject']}")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
