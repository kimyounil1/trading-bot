"""Reassess crowding gate status: keep / tune / disable."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_GO_NO_GO_PATH = Path("logs/crowding_paper/go_no_go_checklist.json")
DEFAULT_LIVE_IMPACT_PATH = Path("logs/crowding_live/latest_summary.json")
DEFAULT_OUTPUT_DIR = Path("logs/crowding_paper")
DEFAULT_OUTPUT_NAME = "reassessment.json"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


@dataclass
class CrowdingReassessmentCriteria:
    min_live_skip_rate: float = 0.01
    min_backtest_blocked_trades: int = 1
    min_sharpe_delta_for_keep: float = -0.15


def build_crowding_gate_reassessment(
    *,
    go_no_go_path: str | Path = DEFAULT_GO_NO_GO_PATH,
    live_impact_path: str | Path = DEFAULT_LIVE_IMPACT_PATH,
    criteria: CrowdingReassessmentCriteria | None = None,
) -> dict[str, Any]:
    criteria = criteria or CrowdingReassessmentCriteria()
    go_no_go = _load_json(Path(go_no_go_path))
    live = _load_json(Path(live_impact_path))

    decision = str(go_no_go.get("decision", "UNKNOWN"))
    metrics = go_no_go.get("metrics") or {}
    delta = metrics.get("delta") or {}
    guarded = metrics.get("guarded") or {}
    blocked_trades = int(guarded.get("estimated_crowding_blocked_trades", 0) or 0)
    sharpe_delta = float(delta.get("sharpe_ratio", 0.0) or 0.0)
    ret_delta = float(delta.get("total_return_pct", 0.0) or 0.0)

    live_block = live.get("live") or {}
    live_skip_rate = float(live_block.get("crowding_skip_rate_of_skips", 0.0) or 0.0)
    live_skip_count = int(live_block.get("crowding_skip_count", 0) or 0)

    recommendation = "KEEP"
    rationale: list[str] = []
    if decision == "NO_GO":
        if blocked_trades < criteria.min_backtest_blocked_trades and live_skip_count <= 0:
            recommendation = "DISABLE_OR_KEEP_OFF"
            rationale.append("Backtest blocked_trades=0 and live crowding skips are absent.")
        elif live_skip_rate >= criteria.min_live_skip_rate:
            recommendation = "TUNE"
            rationale.append("Live crowding skips are present; tune thresholds instead of enabling now.")
        else:
            recommendation = "DISABLE_OR_KEEP_OFF"
            rationale.append("NO_GO with weak live evidence; keep guard disabled for now.")
    else:
        if sharpe_delta >= criteria.min_sharpe_delta_for_keep and ret_delta >= -5.0:
            recommendation = "KEEP"
            rationale.append("GO_PAPER and backtest degradation is within tolerance.")
        else:
            recommendation = "TUNE"
            rationale.append("GO_PAPER but risk/return deltas suggest threshold tuning.")

    if not rationale:
        rationale.append("Insufficient data; keep current state and gather more runs.")

    return {
        "generated_at": _utc_now_iso(),
        "go_no_go_path": str(go_no_go_path),
        "live_impact_path": str(live_impact_path),
        "decision": decision,
        "recommendation": recommendation,
        "inputs": {
            "blocked_trades": blocked_trades,
            "sharpe_delta": sharpe_delta,
            "total_return_delta_pct": ret_delta,
            "live_crowding_skip_count": live_skip_count,
            "live_crowding_skip_rate_of_skips": live_skip_rate,
        },
        "criteria": {
            "min_live_skip_rate": criteria.min_live_skip_rate,
            "min_backtest_blocked_trades": criteria.min_backtest_blocked_trades,
            "min_sharpe_delta_for_keep": criteria.min_sharpe_delta_for_keep,
        },
        "rationale": rationale,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Crowding gate keep/tune/disable reassessment")
    parser.add_argument("--go-no-go-path", default=str(DEFAULT_GO_NO_GO_PATH))
    parser.add_argument("--live-impact-path", default=str(DEFAULT_LIVE_IMPACT_PATH))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    report = build_crowding_gate_reassessment(
        go_no_go_path=args.go_no_go_path,
        live_impact_path=args.live_impact_path,
    )
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / DEFAULT_OUTPUT_NAME
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("=== Crowding gate reassessment ===")
    print(f"decision={report['decision']} recommendation={report['recommendation']}")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
