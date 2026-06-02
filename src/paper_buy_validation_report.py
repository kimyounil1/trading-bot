"""Paper validation: AI+LLM agreement, buy path skips/submits, rank gate accumulation."""

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
from src.llm_advisory_impact_report import _parse_llm_verdict, build_llm_advisory_impact_report
from src.llm_ai_agreement_report import build_llm_ai_agreement_report
from src.settings import load_settings

DEFAULT_OUTPUT_DIR = Path("logs/paper_validation")

_AI_SCORE_BLOCK_RE = re.compile(r"ai score filter blocked", re.IGNORECASE)
_LLM_BLOCK_RE = re.compile(r"LLM Reject|llm reject", re.IGNORECASE)
_RANK_BLOCK_RE = re.compile(r"rank ai gate blocked", re.IGNORECASE)
_RANK_MISSING_RE = re.compile(r"rank ai gate missing score", re.IGNORECASE)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ai_passed(row: pd.Series, threshold: float) -> bool | None:
    score = pd.to_numeric(row.get("ai_score"), errors="coerce")
    if pd.isna(score):
        return None
    return float(score) >= threshold


def _llm_side(row: pd.Series) -> str | None:
    side, _ = _parse_llm_verdict(str(row.get("llm_verdict") or ""))
    return side


def _classify_skip_reason(reason: str) -> str:
    text = str(reason or "")
    if _RANK_BLOCK_RE.search(text):
        return "rank_gate"
    if _RANK_MISSING_RE.search(text):
        return "rank_missing"
    if _LLM_BLOCK_RE.search(text):
        return "llm_block"
    if _AI_SCORE_BLOCK_RE.search(text):
        return "ai_score"
    return "other"


def build_audit_buy_path_comparison(
    audit_df: pd.DataFrame,
    *,
    ai_threshold: float,
    llm_advisory_only: bool,
) -> dict[str, Any]:
    """Compare skips/submits when AI alone vs AI+LLM (blocking mode) apply."""
    if audit_df.empty:
        return {
            "rows": 0,
            "skip_buy_total": 0,
            "buy_submitted": 0,
            "notes": ["No audit rows in lookback window."],
        }

    df = audit_df.copy()
    df["event_type"] = df["event_type"].astype(str)
    skips = df[df["event_type"] == "SKIP_BUY"].copy()
    submitted = df[df["event_type"] == "BUY_SUBMITTED"].copy()
    advisory = df[df["event_type"] == "LLM_ADVISORY"].copy()

    skip_by_layer: dict[str, int] = {}
    for reason in skips.get("reason", pd.Series(dtype=str)).astype(str):
        layer = _classify_skip_reason(reason)
        skip_by_layer[layer] = skip_by_layer.get(layer, 0) + 1

    ai_pass_llm_block = 0
    ai_fail = 0
    for _, row in skips.iterrows():
        ai_ok = _ai_passed(row, ai_threshold)
        layer = _classify_skip_reason(str(row.get("reason") or ""))
        if ai_ok is False or layer == "ai_score":
            ai_fail += 1
        elif ai_ok and layer == "llm_block":
            ai_pass_llm_block += 1

    submitted_accept = 0
    submitted_reject_verdict = 0
    submitted_no_llm = 0
    for _, row in submitted.iterrows():
        side = _llm_side(row)
        if side == "ACCEPT":
            submitted_accept += 1
        elif side == "REJECT":
            submitted_reject_verdict += 1
        else:
            submitted_no_llm += 1

    advisory_ai_pass = 0
    for _, row in advisory.iterrows():
        if _ai_passed(row, ai_threshold):
            advisory_ai_pass += 1

    return {
        "rows": int(len(df)),
        "llm_advisory_only": llm_advisory_only,
        "ai_score_buy_threshold": ai_threshold,
        "skip_buy_total": int(len(skips)),
        "skip_by_layer": skip_by_layer,
        "skip_ai_score_layer": skip_by_layer.get("ai_score", 0),
        "skip_llm_block_layer": skip_by_layer.get("llm_block", 0),
        "skip_rank_gate_layer": skip_by_layer.get("rank_gate", 0),
        "skip_rank_missing_layer": skip_by_layer.get("rank_missing", 0),
        "skip_other_layer": skip_by_layer.get("other", 0),
        "ai_pass_llm_block": ai_pass_llm_block,
        "ai_fail_or_low_score": ai_fail,
        "buy_submitted": int(len(submitted)),
        "buy_submitted_llm_accept": submitted_accept,
        "buy_submitted_llm_reject_verdict": submitted_reject_verdict,
        "buy_submitted_no_llm_verdict": submitted_no_llm,
        "llm_advisory_would_reject_ai_passed": int(len(advisory)),
        "interpretation": (
            "Blocking mode (llm_advisory_only=false): ai_pass_llm_block counts SKIP_BUY "
            "where AI score passed but LLM blocked. submitted_llm_reject_verdict should be ~0."
            if not llm_advisory_only
            else "Advisory mode: compare advisory_would_reject_ai_passed vs buy_submitted_llm_reject_verdict."
        ),
    }


def build_rank_gate_paper_tracker(
    audit_df: pd.DataFrame,
    *,
    min_calendar_days: int = 14,
) -> dict[str, Any]:
    """Track rank-gate audit accumulation for Tier-1 paper validation."""
    if audit_df.empty or "timestamp" not in audit_df.columns:
        return {
            "calendar_days_with_events": 0,
            "min_calendar_days_required": min_calendar_days,
            "gate_ready": False,
            "notes": ["No audit timestamps — run paper dry-runs to accumulate."],
        }

    df = audit_df.copy()
    ts = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    df = df[ts.notna()].copy()
    df["date"] = ts[ts.notna()].dt.strftime("%Y-%m-%d")
    df["event_type"] = df["event_type"].astype(str)
    df["reason"] = df.get("reason", pd.Series(dtype=str)).astype(str)

    df["rank_blocked"] = (df["event_type"] == "SKIP_BUY") & df["reason"].str.contains(
        _RANK_BLOCK_RE, na=False
    )
    df["rank_missing"] = (df["event_type"] == "SKIP_BUY") & df["reason"].str.contains(
        _RANK_MISSING_RE, na=False
    )
    df["is_skip_buy"] = df["event_type"] == "SKIP_BUY"
    df["is_buy_submitted"] = df["event_type"] == "BUY_SUBMITTED"

    daily = (
        df.groupby("date", as_index=False)
        .agg(
            events=("event_type", "count"),
            skip_buy=("is_skip_buy", "sum"),
            rank_blocked=("rank_blocked", "sum"),
            rank_missing=("rank_missing", "sum"),
            buy_submitted=("is_buy_submitted", "sum"),
        )
        .sort_values("date")
    )

    rank_block = df["rank_blocked"]
    rank_missing = df["rank_missing"]
    buy_submitted = df["is_buy_submitted"]

    dates_with_rank_signal = df.loc[rank_block | rank_missing | buy_submitted, "date"].unique()
    calendar_days = len(dates_with_rank_signal)
    span_days = 0
    if len(daily) >= 2:
        first = pd.to_datetime(daily["date"].iloc[0])
        last = pd.to_datetime(daily["date"].iloc[-1])
        span_days = int((last - first).days) + 1

    total_rank_blocked = int(rank_block.sum())
    total_submitted = int(buy_submitted.sum())

    gate_ready = (
        calendar_days >= min_calendar_days
        and total_rank_blocked > 0
        and total_submitted >= 0
    )

    return {
        "min_calendar_days_required": min_calendar_days,
        "calendar_days_with_rank_events": calendar_days,
        "audit_span_calendar_days": span_days,
        "first_date": daily["date"].iloc[0] if len(daily) else None,
        "last_date": daily["date"].iloc[-1] if len(daily) else None,
        "total_skip_buy_rank_blocked": total_rank_blocked,
        "total_skip_buy_rank_missing": int(rank_missing.sum()),
        "total_buy_submitted": total_submitted,
        "gate_ready": gate_ready,
        "daily_tail": daily.tail(14).to_dict(orient="records"),
        "notes": [
            "Tier-1 readiness: ≥14 calendar days with rank skip/submit events and stable dry-run cadence.",
            "Compare logs/rank_ai_gate/latest_summary.json after each bootstrap.",
        ],
    }


def build_paper_buy_validation_report(
    *,
    audit_path: str | Path = EXECUTION_AUDIT_LOG_PATH,
    lookback_days: int = 90,
    min_rank_validation_days: int = 14,
) -> dict[str, Any]:
    settings = load_settings()
    threshold = float(settings.ai_score_buy_threshold)
    llm_advisory_only = bool(getattr(settings, "llm_advisory_only", True))

    audit_df = (
        load_execution_audit(Path(audit_path), lookback_days=lookback_days)
        if Path(audit_path).is_file()
        else pd.DataFrame()
    )

    return {
        "generated_at": _utc_now_iso(),
        "lookback_days": lookback_days,
        "llm_advisory_only": llm_advisory_only,
        "rank_ai_buy_gate_enabled": bool(getattr(settings, "rank_ai_buy_gate_enabled", False)),
        "llm_ai_agreement": build_llm_ai_agreement_report(
            audit_path=audit_path,
            lookback_days=lookback_days,
            ai_threshold=threshold,
        ),
        "llm_advisory_impact": build_llm_advisory_impact_report(
            audit_path=audit_path,
            lookback_days=lookback_days,
        ),
        "audit_buy_paths": build_audit_buy_path_comparison(
            audit_df,
            ai_threshold=threshold,
            llm_advisory_only=llm_advisory_only,
        ),
        "rank_gate_paper_tracker": build_rank_gate_paper_tracker(
            audit_df,
            min_calendar_days=min_rank_validation_days,
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Paper buy validation (AI+LLM + rank gate)")
    parser.add_argument("--audit-path", default=EXECUTION_AUDIT_LOG_PATH)
    parser.add_argument("--lookback-days", type=int, default=90)
    parser.add_argument("--min-rank-days", type=int, default=14)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    report = build_paper_buy_validation_report(
        audit_path=args.audit_path,
        lookback_days=args.lookback_days,
        min_rank_validation_days=args.min_rank_days,
    )
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "latest_summary.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    paths = report["audit_buy_paths"]
    rank = report["rank_gate_paper_tracker"]
    agree = report["llm_ai_agreement"]
    print("=== Paper buy validation ===")
    print(
        f"SKIP_BUY: ai={paths.get('skip_ai_score_layer')} llm={paths.get('skip_llm_block_layer')} "
        f"rank={paths.get('skip_rank_gate_layer')} | submitted={paths.get('buy_submitted')}"
    )
    print(
        f"AI pass + LLM block skips: {paths.get('ai_pass_llm_block')} | "
        f"agreement(cache)={agree.get('agreement_pct')}%"
    )
    print(
        f"Rank paper: {rank.get('calendar_days_with_rank_events')}d rank events / "
        f"{rank.get('min_calendar_days_required')}d required, ready={rank.get('gate_ready')}"
    )
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
