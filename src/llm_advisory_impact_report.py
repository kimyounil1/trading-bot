"""Compare outcomes when LLM advisory was followed vs ignored (execution_audit)."""

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

DEFAULT_OUTPUT_DIR = Path("logs/llm_advisory")

_VERDICT_RE = re.compile(r"^(ACCEPT|REJECT):\s*(.*)$", re.IGNORECASE | re.DOTALL)


def _parse_llm_verdict(raw: str) -> tuple[str | None, str]:
    text = str(raw or "").strip()
    if not text:
        return None, ""
    match = _VERDICT_RE.match(text)
    if match:
        return match.group(1).upper(), match.group(2).strip()
    return None, text


def build_llm_advisory_impact_report(
    audit_path: str | Path = EXECUTION_AUDIT_LOG_PATH,
    lookback_days: int = 90,
) -> dict[str, Any]:
    """Summarize advisory WOULD_REJECT vs buys executed despite LLM REJECT verdict.

    PnL counterfactual requires fill/PnL logs joined by ticker+timestamp (future).
    """
    path = Path(audit_path)
    df = load_execution_audit(path, lookback_days=lookback_days) if path.is_file() else pd.DataFrame()
    if df.empty:
        return {
            "generated_at": _utc_now_iso(),
            "audit_path": str(path),
            "lookback_days": lookback_days,
            "rows": 0,
            "notes": ["No execution_audit rows — run main.py (dry-run or --execute) to accumulate."],
        }

    if "llm_verdict" not in df.columns:
        df["llm_verdict"] = ""

    df["llm_side"] = df["llm_verdict"].map(lambda v: _parse_llm_verdict(v)[0])
    df["event_type"] = df["event_type"].astype(str)

    advisory = df[df["event_type"] == "LLM_ADVISORY"].copy()
    submitted = df[df["event_type"] == "BUY_SUBMITTED"].copy()
    blocked = df[
        (df["event_type"] == "SKIP_BUY")
        & (df["reason"].astype(str).str.contains("LLM Reject", case=False, na=False))
    ].copy()

    ignored_llm_buys = submitted[submitted["llm_side"] == "REJECT"]

    report: dict[str, Any] = {
        "generated_at": _utc_now_iso(),
        "audit_path": str(path),
        "lookback_days": lookback_days,
        "rows": int(len(df)),
        "advisory_would_reject": int(len(advisory)),
        "buy_submitted": int(len(submitted)),
        "buy_submitted_despite_llm_reject": int(len(ignored_llm_buys)),
        "buy_blocked_by_llm": int(len(blocked)),
        "sample_would_reject": advisory.head(10).to_dict(orient="records"),
        "sample_ignored_reject_buys": ignored_llm_buys.head(10).to_dict(orient="records"),
        "notes": [
            "llm_advisory_only=true: orders proceed; LLM_ADVISORY + BUY_SUBMITTED with REJECT verdict = ignored advice.",
            "PnL diff (followed vs ignored) needs fill prices — join orders/status logs in a later pass.",
        ],
    }
    return report


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM advisory vs blocking stats from execution_audit")
    parser.add_argument("--audit-path", default=EXECUTION_AUDIT_LOG_PATH)
    parser.add_argument("--lookback-days", type=int, default=90)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    report = build_llm_advisory_impact_report(args.audit_path, lookback_days=args.lookback_days)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "latest_summary.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print("=== LLM advisory impact (execution_audit) ===")
    print(f"Advisory WOULD_REJECT: {report.get('advisory_would_reject', 0)}")
    print(f"BUY submitted: {report.get('buy_submitted', 0)}")
    print(f"Submitted despite LLM REJECT: {report.get('buy_submitted_despite_llm_reject', 0)}")
    print(f"Blocked by LLM (blocking mode): {report.get('buy_blocked_by_llm', 0)}")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
