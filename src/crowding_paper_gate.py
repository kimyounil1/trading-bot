"""Go/no-go checklist for enabling crowding_guard on paper (uses guard_impact report)."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_GUARD_IMPACT_PATH = Path("logs/guard_impact/latest_summary.json")
DEFAULT_OUTPUT_DIR = Path("logs/crowding_paper")
PROPOSAL_PATH = Path("config/crowding_paper_proposal.json")

CROWDING_GATE_REPORT_KEYS = (
    "generated_at",
    "guard_impact_path",
    "decision",
    "checklist",
    "paper_proposal_path",
    "metrics",
)


@dataclass
class CrowdingPaperGateCriteria:
    max_sharpe_delta_loss: float = 0.15
    min_drawdown_delta_pp: float = -1.0
    max_trade_count_loss: int = 20
    min_blocked_trades: int = 1


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_guard_impact_summary(path: Path = DEFAULT_GUARD_IMPACT_PATH) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(
            f"Guard impact summary missing: {path}. Run: bash scripts/run_guard_impact_report.sh"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate_crowding_paper_gate(
    guard_report: dict[str, Any],
    criteria: CrowdingPaperGateCriteria | None = None,
) -> dict[str, Any]:
    criteria = criteria or CrowdingPaperGateCriteria()
    baseline = guard_report.get("baseline") or {}
    guarded = guard_report.get("with_crowding_guard") or {}
    delta = guard_report.get("delta") or {}

    blocked = int(guarded.get("estimated_crowding_blocked_trades", 0))
    sharpe_delta = float(delta.get("sharpe_ratio", 0.0))
    dd_delta = float(delta.get("max_drawdown_pct", 0.0))
    trade_delta = int(delta.get("trade_count", 0))

    checks: list[dict[str, Any]] = [
        {
            "id": "guard_active",
            "pass": blocked >= criteria.min_blocked_trades,
            "detail": f"blocked_trades={blocked} (min {criteria.min_blocked_trades})",
        },
        {
            "id": "sharpe_not_too_worse",
            "pass": sharpe_delta >= -criteria.max_sharpe_delta_loss,
            "detail": f"sharpe_delta={sharpe_delta:.4f} (floor -{criteria.max_sharpe_delta_loss})",
        },
        {
            "id": "drawdown_acceptable",
            "pass": dd_delta >= criteria.min_drawdown_delta_pp,
            "detail": f"max_dd_delta_pp={dd_delta:.4f} (floor {criteria.min_drawdown_delta_pp})",
        },
        {
            "id": "trade_count_acceptable",
            "pass": trade_delta >= -criteria.max_trade_count_loss,
            "detail": f"trade_count_delta={trade_delta} (floor -{criteria.max_trade_count_loss})",
        },
    ]
    all_pass = all(item["pass"] for item in checks)
    decision = "GO_PAPER" if all_pass else "NO_GO"

    return {
        "generated_at": _utc_now_iso(),
        "guard_impact_path": str(DEFAULT_GUARD_IMPACT_PATH),
        "decision": decision,
        "checklist": checks,
        "paper_proposal_path": str(PROPOSAL_PATH),
        "metrics": {
            "baseline": baseline,
            "guarded": guarded,
            "delta": delta,
            "blocked_trades": blocked,
        },
    }


def validate_crowding_gate_report(report: dict[str, Any]) -> dict[str, Any]:
    for key in CROWDING_GATE_REPORT_KEYS:
        if key not in report:
            raise ValueError(f"Missing crowding gate report key: {key}")
    return report


def format_crowding_gate_report(report: dict[str, Any]) -> str:
    lines = [
        f"=== Crowding paper gate: {report['decision']} ===",
        f"Proposal file: {report['paper_proposal_path']}",
    ]
    for item in report["checklist"]:
        mark = "PASS" if item["pass"] else "FAIL"
        lines.append(f"  [{mark}] {item['id']}: {item['detail']}")
    return "\n".join(lines)


def write_crowding_gate_artifacts(
    report: dict[str, Any],
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "go_no_go_checklist.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return path


def run_crowding_paper_gate(
    guard_impact_path: Path = DEFAULT_GUARD_IMPACT_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    guard_report = load_guard_impact_summary(guard_impact_path)
    report = validate_crowding_gate_report(evaluate_crowding_paper_gate(guard_report))
    report["guard_impact_path"] = str(guard_impact_path)
    write_crowding_gate_artifacts(report, output_dir)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Crowding guard paper go/no-go checklist")
    parser.add_argument("--guard-impact", default=str(DEFAULT_GUARD_IMPACT_PATH))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    report = run_crowding_paper_gate(Path(args.guard_impact), Path(args.output_dir))
    print(format_crowding_gate_report(report))


if __name__ == "__main__":
    main()
