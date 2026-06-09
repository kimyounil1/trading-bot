"""Trend summary from logs/paper_validation/history.jsonl."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

DEFAULT_HISTORY_PATH = Path("logs/paper_validation/history.jsonl")
DEFAULT_OUTPUT_DIR = Path("logs/paper_validation")
DEFAULT_OUTPUT_NAME = "trend_summary.json"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_history(path: Path) -> pd.DataFrame:
    if not path.is_file():
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(rec, dict):
            rows.append(rec)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df.get("date"), errors="coerce")
    df = df[df["date"].notna()].sort_values("date").reset_index(drop=True)
    return df


def build_paper_validation_trend_report(
    history_path: str | Path = DEFAULT_HISTORY_PATH,
    *,
    rolling_days: int = 7,
) -> dict[str, Any]:
    path = Path(history_path)
    df = _load_history(path)
    if df.empty:
        return {
            "generated_at": _utc_now_iso(),
            "history_path": str(path),
            "rows": 0,
            "rolling_days": rolling_days,
            "latest": {},
            "rolling": {},
            "alerts": [],
            "notes": ["No history rows yet. Run: bash scripts/run_paper_buy_validation.sh"],
        }

    numeric_cols = [
        "agreement_pct",
        "skip_ai_score",
        "skip_llm_block",
        "skip_rank_gate",
        "buy_submitted",
        "rank_calendar_days",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "rank_gate_ready" in df.columns:
        df["rank_gate_ready"] = df["rank_gate_ready"].astype(bool)

    latest = df.iloc[-1]
    roll = df.tail(max(1, int(rolling_days)))
    rolling = {
        "agreement_pct_mean": (
            float(roll["agreement_pct"].mean())
            if "agreement_pct" in roll and roll["agreement_pct"].notna().any()
            else None
        ),
        "skip_ai_score_mean": (
            float(roll["skip_ai_score"].mean())
            if "skip_ai_score" in roll and roll["skip_ai_score"].notna().any()
            else None
        ),
        "skip_llm_block_mean": (
            float(roll["skip_llm_block"].mean())
            if "skip_llm_block" in roll and roll["skip_llm_block"].notna().any()
            else None
        ),
        "skip_rank_gate_mean": (
            float(roll["skip_rank_gate"].mean())
            if "skip_rank_gate" in roll and roll["skip_rank_gate"].notna().any()
            else None
        ),
        "buy_submitted_mean": (
            float(roll["buy_submitted"].mean())
            if "buy_submitted" in roll and roll["buy_submitted"].notna().any()
            else None
        ),
    }

    alerts: list[str] = []
    if rolling["agreement_pct_mean"] is not None and pd.notna(latest.get("agreement_pct")):
        if float(latest["agreement_pct"]) <= float(rolling["agreement_pct_mean"]) - 10.0:
            alerts.append("agreement_drop_gt_10pp_vs_rolling")
    if len(df) >= 2 and bool(latest.get("rank_gate_ready")):
        prev = bool(df.iloc[-2].get("rank_gate_ready", False))
        if not prev:
            alerts.append("rank_gate_ready_flip_true")
    if rolling["skip_llm_block_mean"] is not None and pd.notna(latest.get("skip_llm_block")):
        mean_llm = float(rolling["skip_llm_block_mean"])
        latest_llm = float(latest["skip_llm_block"])
        if mean_llm > 0 and latest_llm >= mean_llm * 1.5 and latest_llm >= 10:
            alerts.append("skip_llm_block_spike")
    if rolling["skip_rank_gate_mean"] is not None and pd.notna(latest.get("skip_rank_gate")):
        mean_rank = float(rolling["skip_rank_gate_mean"])
        latest_rank = float(latest["skip_rank_gate"])
        if mean_rank > 0 and latest_rank >= mean_rank * 1.5 and latest_rank >= 20:
            alerts.append("skip_rank_gate_spike")

    return {
        "generated_at": _utc_now_iso(),
        "history_path": str(path),
        "rows": int(len(df)),
        "rolling_days": rolling_days,
        "latest": {
            "date": latest["date"].strftime("%Y-%m-%d"),
            "agreement_pct": (
                float(latest["agreement_pct"]) if pd.notna(latest.get("agreement_pct")) else None
            ),
            "skip_ai_score": (
                int(latest["skip_ai_score"]) if pd.notna(latest.get("skip_ai_score")) else None
            ),
            "skip_llm_block": (
                int(latest["skip_llm_block"]) if pd.notna(latest.get("skip_llm_block")) else None
            ),
            "skip_rank_gate": (
                int(latest["skip_rank_gate"]) if pd.notna(latest.get("skip_rank_gate")) else None
            ),
            "buy_submitted": (
                int(latest["buy_submitted"]) if pd.notna(latest.get("buy_submitted")) else None
            ),
            "rank_calendar_days": (
                int(latest["rank_calendar_days"])
                if pd.notna(latest.get("rank_calendar_days"))
                else None
            ),
            "rank_gate_ready": bool(latest.get("rank_gate_ready", False)),
        },
        "rolling": rolling,
        "alerts": alerts,
        "tail": [
            {
                "date": row["date"].strftime("%Y-%m-%d"),
                "agreement_pct": (
                    float(row["agreement_pct"]) if pd.notna(row.get("agreement_pct")) else None
                ),
                "skip_llm_block": (
                    int(row["skip_llm_block"]) if pd.notna(row.get("skip_llm_block")) else None
                ),
                "skip_rank_gate": (
                    int(row["skip_rank_gate"]) if pd.notna(row.get("skip_rank_gate")) else None
                ),
                "buy_submitted": (
                    int(row["buy_submitted"]) if pd.notna(row.get("buy_submitted")) else None
                ),
                "rank_gate_ready": bool(row.get("rank_gate_ready", False)),
            }
            for _, row in roll.iterrows()
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Paper validation trend report from history.jsonl")
    parser.add_argument("--history-path", default=str(DEFAULT_HISTORY_PATH))
    parser.add_argument("--rolling-days", type=int, default=7)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    report = build_paper_validation_trend_report(
        history_path=args.history_path,
        rolling_days=args.rolling_days,
    )
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / DEFAULT_OUTPUT_NAME
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("=== Paper validation trend ===")
    print(f"rows: {report.get('rows', 0)}")
    print(f"alerts: {report.get('alerts', [])}")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
