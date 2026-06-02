"""Paper rank AI buy/add gate impact from execution_audit and candidate cache."""

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
from src.settings import load_settings

DEFAULT_OUTPUT_DIR = Path("logs/rank_ai_gate")
DEFAULT_CANDIDATE_BUY = Path("logs/candidate_cache/latest_buy.csv")

_RANK_BLOCKED_RE = re.compile(r"rank ai gate blocked", re.IGNORECASE)
_RANK_PASSED_RE = re.compile(r"rank ai gate passed", re.IGNORECASE)
_RANK_MISSING_RE = re.compile(r"rank ai gate missing score", re.IGNORECASE)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    return text in {"true", "1", "yes"}


def _column_series(df: pd.DataFrame, name: str, default: Any) -> pd.Series:
    if name in df.columns:
        return df[name]
    return pd.Series([default] * len(df), index=df.index)


def _audit_rank_stats(audit_df: pd.DataFrame) -> dict[str, Any]:
    if audit_df.empty:
        return {
            "rows": 0,
            "skip_buy_rank_blocked": 0,
            "skip_buy_rank_missing_score": 0,
            "buy_submitted": 0,
            "buy_submitted_with_rank_pass_reason": 0,
            "top_blocked_tickers": {},
        }

    event_types = audit_df.get("event_type", pd.Series(dtype=str)).astype(str)
    reasons = audit_df.get("reason", pd.Series(dtype=str)).astype(str)
    tickers = audit_df.get("ticker", pd.Series(dtype=str)).astype(str).str.upper()

    skip_mask = event_types == "SKIP_BUY"
    blocked_mask = skip_mask & reasons.str.contains(_RANK_BLOCKED_RE)
    missing_mask = skip_mask & reasons.str.contains(_RANK_MISSING_RE)
    submitted_mask = event_types == "BUY_SUBMITTED"
    passed_reason_mask = submitted_mask & reasons.str.contains(_RANK_PASSED_RE)

    blocked_tickers = tickers[blocked_mask]
    top_blocked = (
        blocked_tickers.value_counts().head(10).to_dict()
        if not blocked_tickers.empty
        else {}
    )

    return {
        "rows": int(len(audit_df)),
        "skip_buy_rank_blocked": int(blocked_mask.sum()),
        "skip_buy_rank_missing_score": int(missing_mask.sum()),
        "buy_submitted": int(submitted_mask.sum()),
        "buy_submitted_with_rank_pass_reason": int(passed_reason_mask.sum()),
        "top_blocked_tickers": top_blocked,
    }


def _candidate_cache_stats(
    buy_path: Path,
    *,
    min_score_quantile: float,
) -> dict[str, Any]:
    if not buy_path.is_file():
        return {
            "available": False,
            "path": str(buy_path),
            "rows": 0,
        }

    df = pd.read_csv(buy_path)
    if df.empty:
        return {"available": True, "path": str(buy_path), "rows": 0}

    df = df.copy()
    df["ticker"] = df.get("ticker", "").astype(str).str.upper()
    reasons = _column_series(df, "reason", "").astype(str)
    risk_allowed = _column_series(df, "risk_allowed", False)
    if risk_allowed.dtype == object:
        risk_allowed = risk_allowed.map(_parse_boolish)

    rank_enabled = _parse_boolish(_column_series(df, "rank_ai_gate_enabled", False).iloc[0])
    pct = pd.to_numeric(_column_series(df, "rank_ai_percentile", None), errors="coerce")
    rank_blocked = reasons.str.contains(_RANK_BLOCKED_RE, na=False)
    rank_passed = risk_allowed & pct.notna() & (pct >= min_score_quantile)

    signal_buy = df.get("signal", pd.Series(dtype=str)).astype(str).str.upper() == "BUY"

    return {
        "available": True,
        "path": str(buy_path),
        "rows": int(len(df)),
        "rank_ai_gate_enabled": rank_enabled,
        "buy_signal_rows": int(signal_buy.sum()),
        "risk_allowed_rows": int(risk_allowed.sum()),
        "rank_blocked_rows": int(rank_blocked.sum()),
        "rank_passed_rows": int(rank_passed.sum()),
        "median_rank_percentile": (
            float(pct.median()) if pct.notna().any() else None
        ),
        "top_blocked_tickers": (
            df.loc[rank_blocked, "ticker"].value_counts().head(10).to_dict()
            if rank_blocked.any()
            else {}
        ),
        "top_passed_tickers": (
            df.loc[rank_passed, "ticker"]
            .value_counts()
            .head(10)
            .to_dict()
            if rank_passed.any()
            else {}
        ),
    }


def build_rank_ai_gate_impact_report(
    *,
    audit_path: str | Path = EXECUTION_AUDIT_LOG_PATH,
    candidate_buy_path: str | Path = DEFAULT_CANDIDATE_BUY,
    lookback_days: int = 30,
) -> dict[str, Any]:
    settings = load_settings()
    audit_file = Path(audit_path)
    audit_df = (
        load_execution_audit(audit_file, lookback_days=lookback_days)
        if audit_file.is_file()
        else pd.DataFrame()
    )

    gate_enabled = bool(getattr(settings, "rank_ai_buy_gate_enabled", False))
    cutoff = float(getattr(settings, "rank_ai_buy_gate_min_score_quantile", 0.85))
    audit_stats = _audit_rank_stats(audit_df)
    cache_stats = _candidate_cache_stats(Path(candidate_buy_path), min_score_quantile=cutoff)

    notes: list[str] = []
    if not gate_enabled:
        notes.append("rank_ai_buy_gate_enabled is false in strategy_config — report is informational only.")
    if audit_stats["rows"] == 0:
        notes.append("No execution_audit rows in lookback — run: bash scripts/run_bot_once.sh dry-run")
    if not cache_stats.get("available"):
        notes.append(
            "Candidate cache missing — run: .venv/bin/python -m src.generate_candidate_cache"
        )
    if gate_enabled and audit_stats["skip_buy_rank_blocked"] == 0 and audit_stats["buy_submitted"] == 0:
        notes.append(
            "Gate enabled but no rank skip/submit events yet — accumulate more dry-run or paper runs."
        )

    return {
        "generated_at": _utc_now_iso(),
        "lookback_days": lookback_days,
        "gate": {
            "enabled": gate_enabled,
            "model_path": str(getattr(settings, "rank_ai_buy_gate_model_path", "")),
            "prediction_horizon": int(
                getattr(settings, "rank_ai_buy_gate_prediction_horizon", 20)
            ),
            "top_bucket_pct": float(
                getattr(settings, "rank_ai_buy_gate_top_bucket_pct", 0.15)
            ),
            "min_score_quantile": cutoff,
            "fail_closed": bool(getattr(settings, "rank_ai_buy_gate_fail_closed", True)),
        },
        "execution_audit": {
            "path": str(audit_file),
            **audit_stats,
        },
        "candidate_cache": cache_stats,
        "notes": notes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Rank AI buy gate paper impact report")
    parser.add_argument("--audit-path", default=EXECUTION_AUDIT_LOG_PATH)
    parser.add_argument("--candidate-buy-path", default=str(DEFAULT_CANDIDATE_BUY))
    parser.add_argument("--lookback-days", type=int, default=30)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    report = build_rank_ai_gate_impact_report(
        audit_path=args.audit_path,
        candidate_buy_path=args.candidate_buy_path,
        lookback_days=args.lookback_days,
    )
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "latest_summary.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    audit = report["execution_audit"]
    cache = report["candidate_cache"]
    print("=== Rank AI gate impact (paper) ===")
    print(f"Gate enabled: {report['gate']['enabled']}")
    print(f"Audit rows: {audit.get('rows', 0)}")
    print(f"SKIP_BUY (rank blocked): {audit.get('skip_buy_rank_blocked', 0)}")
    print(f"BUY submitted: {audit.get('buy_submitted', 0)}")
    if cache.get("available"):
        print(f"Cache rank blocked: {cache.get('rank_blocked_rows', 0)}")
        print(f"Cache rank passed: {cache.get('rank_passed_rows', 0)}")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
