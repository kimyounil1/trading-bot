"""CLI summary for model promotion reports and documented gate thresholds."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.ml_quality_report import MlQualityPromotionCriteria, PROMOTION_MAX_OVERALL_BRIER, PROMOTION_MIN_AVG_ROC_AUC
from src.promotion_thresholds import ci_portfolio_thresholds, promotion_portfolio_thresholds

DEFAULT_REPORT_PATH = Path("logs/ml/model_promotion_report.json")


def promotion_gate_reference() -> dict[str, Any]:
    ml = MlQualityPromotionCriteria()
    promote_pf = promotion_portfolio_thresholds()
    ci_pf = ci_portfolio_thresholds()
    return {
        "ml_quality": {
            "min_avg_roc_auc": ml.min_avg_roc_auc,
            "max_overall_brier": ml.max_overall_brier,
            "reject_high_fold_variance": ml.reject_high_fold_variance,
            "constants": {
                "PROMOTION_MIN_AVG_ROC_AUC": PROMOTION_MIN_AVG_ROC_AUC,
                "PROMOTION_MAX_OVERALL_BRIER": PROMOTION_MAX_OVERALL_BRIER,
            },
        },
        "portfolio_oos_promotion": {
            "max_drawdown_floor": promote_pf.max_drawdown_floor,
            "min_return_vs_benchmark": promote_pf.min_return_vs_benchmark,
            "min_sharpe": promote_pf.min_sharpe,
            "note": "Retrain promotion; challenger must beat benchmark (>=0 pp).",
        },
        "portfolio_oos_ci": {
            "max_drawdown_floor": ci_pf.max_drawdown_floor,
            "min_return_vs_benchmark": ci_pf.min_return_vs_benchmark,
            "min_sharpe": ci_pf.min_sharpe,
            "note": "Post-workflow / check_portfolio_backtest_gate only.",
        },
        "auc_vs_champion": "challenger avg_roc_auc must exceed champion when champion exists",
        "portfolio_vs_champion": "challenger must beat champion on Sharpe, then return, then drawdown",
    }


def load_promotion_report(path: str | Path = DEFAULT_REPORT_PATH) -> dict[str, Any]:
    report_path = Path(path)
    if not report_path.is_file():
        raise FileNotFoundError(f"Promotion report not found: {report_path}")
    return json.loads(report_path.read_text(encoding="utf-8"))


def format_promotion_summary(report: dict[str, Any]) -> str:
    lines = [
        "=== Model promotion summary ===",
        f"Decision: {report.get('decision')}",
        f"AUC gate: {report.get('auc_gate_passed')}",
        f"ML quality gate: {report.get('ml_quality_gate_passed')}",
        f"Portfolio gate: {report.get('portfolio_gate_passed')}",
        f"Portfolio vs champion: {report.get('portfolio_vs_champion_passed')}",
    ]
    reasons = report.get("reasons") or []
    if reasons:
        lines.append("Reasons:")
        for reason in reasons:
            lines.append(f"  - {reason}")
    ml_eval = report.get("ml_quality_evaluation") or {}
    if ml_eval.get("failures"):
        lines.append("ML quality failures:")
        for failure in ml_eval["failures"]:
            lines.append(f"  - {failure}")
    portfolio_gate = report.get("portfolio_gate") or {}
    for key in ("failures", "warnings"):
        items = portfolio_gate.get(key) or []
        if items:
            lines.append(f"Portfolio {key}:")
            for item in items:
                lines.append(f"  - {item}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Promotion report summary and gate reference")
    parser.add_argument("--report", default=str(DEFAULT_REPORT_PATH))
    parser.add_argument("--gates-only", action="store_true", help="Print threshold reference only")
    args = parser.parse_args()

    if args.gates_only:
        print(json.dumps(promotion_gate_reference(), indent=2, sort_keys=True))
        return

    report = load_promotion_report(args.report)
    print(format_promotion_summary(report))
    print("\n--- Gate reference (code defaults) ---")
    print(json.dumps(promotion_gate_reference(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
