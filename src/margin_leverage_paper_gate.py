"""Go/no-go for margin leverage_factor > 1 on paper (uses leverage_stress report)."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.leverage_stress_report import (
    DEFAULT_EQUITY_PATH,
    run_leverage_stress_report,
)

DEFAULT_STRESS_SUMMARY_PATH = Path("logs/leverage_stress/latest_summary.json")
DEFAULT_OUTPUT_DIR = Path("logs/margin_leverage_paper")
DEFAULT_CONFIG_PATH = Path("config/margin_leverage_paper_config.json")
PROPOSAL_PATH = Path("config/margin_leverage_paper_proposal.json")

MARGIN_LEVERAGE_GATE_REPORT_KEYS = (
    "generated_at",
    "stress_summary_path",
    "decision",
    "checklist",
    "paper_proposal_path",
    "metrics",
)


@dataclass
class MarginLeverageGateConfig:
    max_allowed_leverage_factor: float = 1.5
    stress_leverage: float = 2.0
    stress_summary_path: Path = DEFAULT_STRESS_SUMMARY_PATH
    require_stress_alerts_passed: bool = True
    proposal_path: Path = PROPOSAL_PATH


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_margin_leverage_paper_config(
    path: Path = DEFAULT_CONFIG_PATH,
) -> MarginLeverageGateConfig:
    if not path.is_file():
        return MarginLeverageGateConfig()
    raw = json.loads(path.read_text(encoding="utf-8"))
    return MarginLeverageGateConfig(
        max_allowed_leverage_factor=float(raw.get("max_allowed_leverage_factor", 1.5)),
        stress_leverage=float(raw.get("stress_leverage", 2.0)),
        stress_summary_path=Path(raw.get("stress_summary_path", DEFAULT_STRESS_SUMMARY_PATH)),
        require_stress_alerts_passed=bool(raw.get("require_stress_alerts_passed", True)),
        proposal_path=Path(raw.get("proposal_path", PROPOSAL_PATH)),
    )


def load_stress_summary(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(
            f"Leverage stress summary missing: {path}. "
            "Run: bash scripts/run_leverage_stress_report.sh --leverage 2.0"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate_margin_leverage_paper_gate(
    stress_report: dict[str, Any],
    *,
    configured_leverage_factor: float,
    config: MarginLeverageGateConfig | None = None,
) -> dict[str, Any]:
    config = config or load_margin_leverage_paper_config()
    alerts = stress_report.get("alerts") or {}
    stress_leverage = float(stress_report.get("leverage", config.stress_leverage))
    alerts_passed = bool(alerts.get("passed", False))

    checks: list[dict[str, Any]] = [
        {
            "id": "stress_alerts_passed",
            "pass": (not config.require_stress_alerts_passed) or alerts_passed,
            "detail": f"alerts.passed={alerts_passed} (stress_leverage={stress_leverage})",
        },
        {
            "id": "configured_leverage_within_cap",
            "pass": configured_leverage_factor <= config.max_allowed_leverage_factor,
            "detail": (
                f"leverage_factor={configured_leverage_factor} "
                f"(max {config.max_allowed_leverage_factor})"
            ),
        },
        {
            "id": "leverage_above_flat",
            "pass": configured_leverage_factor > 1.0,
            "detail": f"leverage_factor={configured_leverage_factor} (paper experiment requires >1)",
        },
    ]

    all_pass = all(item["pass"] for item in checks)
    decision = "GO_MARGIN_PAPER" if all_pass else "NO_GO"

    return {
        "generated_at": _utc_now_iso(),
        "stress_summary_path": str(config.stress_summary_path),
        "decision": decision,
        "checklist": checks,
        "paper_proposal_path": str(config.proposal_path),
        "metrics": {
            "stress_leverage": stress_leverage,
            "configured_leverage_factor": configured_leverage_factor,
            "alerts": alerts,
        },
    }


def validate_margin_leverage_gate_report(report: dict[str, Any]) -> dict[str, Any]:
    for key in MARGIN_LEVERAGE_GATE_REPORT_KEYS:
        if key not in report:
            raise ValueError(f"Missing margin leverage gate report key: {key}")
    return report


def write_margin_leverage_gate_artifacts(
    report: dict[str, Any],
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "go_no_go_checklist.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return path


def evaluate_margin_leverage_buy_block(
    leverage_factor: float,
    *,
    margin_leverage_paper_enabled: bool = False,
    margin_leverage_stress_gate_required: bool = True,
    stress_summary_path: Path | None = None,
) -> tuple[bool, str]:
    """Return (block_new_buys, reason) for main.py when margin leverage is active."""
    leverage_factor = float(leverage_factor)
    if leverage_factor <= 1.0:
        return False, ""

    if not margin_leverage_paper_enabled and not margin_leverage_stress_gate_required:
        return False, ""

    config = load_margin_leverage_paper_config()
    summary_path = stress_summary_path or config.stress_summary_path

    try:
        stress_report = load_stress_summary(summary_path)
    except FileNotFoundError as exc:
        return True, f"margin leverage gate: {exc}"

    gate = evaluate_margin_leverage_paper_gate(
        stress_report,
        configured_leverage_factor=leverage_factor,
        config=config,
    )
    if gate["decision"] == "GO_MARGIN_PAPER":
        return False, ""

    failed = [c for c in gate["checklist"] if not c["pass"]]
    detail = "; ".join(f"{c['id']}: {c['detail']}" for c in failed)
    return True, f"margin leverage gate NO_GO ({detail})"


def load_margin_leverage_paper_proposal(
    path: Path = PROPOSAL_PATH,
) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Margin leverage paper proposal missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def apply_margin_leverage_paper_overrides(settings: Any) -> Any:
    """Return a copy-like settings object with proposal order/risk caps (paper only)."""
    from dataclasses import replace

    proposal = load_margin_leverage_paper_proposal()
    overrides = {
        k: proposal[k]
        for k in (
            "leverage_factor",
            "max_gross_exposure_pct",
            "max_test_order_amount",
            "max_orders_per_run",
            "max_daily_order_amount",
            "max_total_positions",
        )
        if k in proposal
    }
    return replace(settings, **overrides)


def run_margin_leverage_paper_gate(
    *,
    equity_path: Path = DEFAULT_EQUITY_PATH,
    configured_leverage_factor: float = 1.25,
    refresh_stress: bool = False,
) -> dict[str, Any]:
    config = load_margin_leverage_paper_config()
    if refresh_stress or not config.stress_summary_path.is_file():
        run_leverage_stress_report(
            equity_path,
            leverage=config.stress_leverage,
            notify_telegram=False,
        )
    stress_report = load_stress_summary(config.stress_summary_path)
    report = validate_margin_leverage_gate_report(
        evaluate_margin_leverage_paper_gate(
            stress_report,
            configured_leverage_factor=configured_leverage_factor,
            config=config,
        )
    )
    write_margin_leverage_gate_artifacts(report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Margin leverage paper go/no-go gate")
    parser.add_argument("--equity-path", default=str(DEFAULT_EQUITY_PATH))
    parser.add_argument("--leverage-factor", type=float, default=1.25)
    parser.add_argument("--refresh-stress", action="store_true")
    args = parser.parse_args()
    report = run_margin_leverage_paper_gate(
        equity_path=Path(args.equity_path),
        configured_leverage_factor=args.leverage_factor,
        refresh_stress=args.refresh_stress,
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
