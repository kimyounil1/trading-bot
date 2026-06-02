"""Operator summary: threshold retune + promotion + label sweep."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_OUTPUT = Path("logs/model_quality/threshold_promotion_summary.json")

SUMMARY_KEYS = (
    "generated_at",
    "threshold_retune",
    "promotion",
    "label_sweep",
    "recommended_actions",
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_threshold_promotion_summary(
    *,
    ml_dir: Path = Path("logs/ml"),
    model_quality_dir: Path = Path("logs/model_quality"),
) -> dict[str, Any]:
    threshold = _read_json(ml_dir / "threshold_retune_report.json")
    promotion = _read_json(ml_dir / "model_promotion_report.json")
    label_sweep = _read_json(ml_dir / "label_challenger_sweep_report.json")
    model_quality = _read_json(model_quality_dir / "latest_summary.json")

    actions: list[str] = []
    if threshold.get("best_buy_threshold") is not None:
        actions.append(
            "Consider setting ai_score_buy_threshold="
            f"{threshold['best_buy_threshold']} from latest threshold retune (paper review first)."
        )
    if promotion.get("decision") != "PROMOTE":
        actions.append("Champion promotion remains blocked — do not replace models/ai_score_model.joblib.")
    else:
        actions.append("Promotion report shows PROMOTE — run manual review before deploying champion.")

    if label_sweep.get("recommendation"):
        actions.append(str(label_sweep["recommendation"]))
    elif model_quality.get("recommendations"):
        actions.extend(str(item) for item in model_quality["recommendations"][:2])

    actions.append(
        "Rank AI buy gate stays paper-only per docs/ai_authority_gates.md until 2-week paper validation completes."
    )

    return {
        "generated_at": _utc_now_iso(),
        "threshold_retune": threshold,
        "promotion": {
            "decision": promotion.get("decision"),
            "ml_quality_gate_failures": promotion.get("ml_quality_gate_failures"),
            "portfolio_gate_failures": promotion.get("portfolio_gate_failures"),
        },
        "label_sweep": {
            "best_by_portfolio_gap": label_sweep.get("best_by_portfolio_gap"),
            "recommendation": label_sweep.get("recommendation"),
        },
        "recommended_actions": actions,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build threshold + promotion operator summary")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    report = build_threshold_promotion_summary()
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
