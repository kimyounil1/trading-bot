"""Summarize model quality artifacts into an operator-facing action plan."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_ML_DIR = Path("logs/ml")
DEFAULT_BENCHMARK_GAP_PATH = Path("logs/benchmark_gap/latest_summary.json")
DEFAULT_OUTPUT_DIR = Path("logs/model_quality")
DEFAULT_RANK_LABEL_GLOB = "rank_label_experiment*/latest_summary.json"

MODEL_QUALITY_SUMMARY_KEYS = (
    "generated_at",
    "decision",
    "health",
    "metrics",
    "blockers",
    "recommendations",
    "sources",
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_rank_label_report(
    *,
    ml_dir: Path,
    rank_label_path: str | Path | None,
) -> tuple[dict[str, Any], str | None]:
    if rank_label_path is not None:
        path = Path(rank_label_path)
        return _read_json(path), str(path)

    candidates: list[tuple[float, Path, dict[str, Any]]] = []
    for path in ml_dir.glob(DEFAULT_RANK_LABEL_GLOB):
        report = _read_json(path)
        portfolio = report.get("portfolio_oos") or {}
        try:
            gap = float(portfolio.get("gap_pct"))
        except (TypeError, ValueError):
            continue
        candidates.append((gap, path, report))

    if not candidates:
        return {}, None
    _, path, report = max(candidates, key=lambda item: item[0])
    return report, str(path)


def _round_or_none(value: Any, digits: int = 4) -> float | None:
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return None


def _brier_from_promotion_failures(promotion: dict[str, Any]) -> float | None:
    text = " ".join(
        str(item)
        for item in (
            list(promotion.get("ml_quality_gate_failures") or [])
            + [promotion.get("reason", "")]
        )
    )
    match = re.search(r"overall_avg_brier_score=([0-9.]+)", text)
    return _round_or_none(match.group(1)) if match else None


def build_model_quality_summary(
    *,
    ml_dir: str | Path = DEFAULT_ML_DIR,
    benchmark_gap_path: str | Path = DEFAULT_BENCHMARK_GAP_PATH,
    rank_label_path: str | Path | None = None,
) -> dict[str, Any]:
    ml_dir = Path(ml_dir)
    promotion_path = ml_dir / "model_promotion_report.json"
    calibration_path = ml_dir / "model_calibration_report.json"
    stability_path = ml_dir / "fold_stability_report.json"
    threshold_path = ml_dir / "threshold_retune_report.json"
    calibration_experiment_path = ml_dir / "calibration_experiment_report.json"
    label_horizon_path = ml_dir / "label_horizon_report.json"
    benchmark_gap_path = Path(benchmark_gap_path)

    promotion = _read_json(promotion_path)
    calibration = _read_json(calibration_path)
    stability = _read_json(stability_path)
    threshold = _read_json(threshold_path)
    calibration_experiment = _read_json(calibration_experiment_path)
    label_horizon = _read_json(label_horizon_path)
    benchmark_gap = _read_json(benchmark_gap_path)
    rank_label, rank_label_source = _read_rank_label_report(
        ml_dir=ml_dir,
        rank_label_path=rank_label_path,
    )
    rank_portfolio = rank_label.get("portfolio_oos") or {}
    rank_metrics = rank_label.get("metrics") or {}

    avg_auc = _round_or_none(
        promotion.get("challenger_avg_roc_auc")
        or (stability.get("roc_auc") or {}).get("mean")
    )
    champion_auc = _round_or_none(promotion.get("champion_avg_roc_auc"))
    brier = _round_or_none(calibration.get("overall_avg_brier_score"))
    if brier == 0 and not calibration.get("bin_count"):
        brier = _brier_from_promotion_failures(promotion)
    roc_std = _round_or_none((stability.get("roc_auc") or {}).get("std"))
    challenger_oos = promotion.get("challenger_portfolio_oos") or {}
    challenger_oos_gap = None
    if challenger_oos:
        challenger_oos_gap = _round_or_none(
            float(challenger_oos.get("total_return", 0.0))
            - float(challenger_oos.get("benchmark_return", 0.0))
        )

    metrics = {
        "challenger_avg_roc_auc": avg_auc,
        "champion_avg_roc_auc": champion_auc,
        "overall_avg_brier_score": brier,
        "roc_auc_std": roc_std,
        "challenger_oos_gap_vs_benchmark": challenger_oos_gap,
        "best_buy_threshold": threshold.get("best_buy_threshold"),
        "best_exit_threshold": threshold.get("best_exit_threshold"),
        "calibration_experiment_status": calibration_experiment.get("status"),
        "calibration_best_method": (
            (calibration_experiment.get("overall") or {}).get("best_method")
        ),
        "calibration_brier_improvement": (
            (calibration_experiment.get("overall") or {}).get("brier_improvement")
        ),
        "label_horizon_status": label_horizon.get("status"),
        "label_horizon_best": label_horizon.get("best_candidate"),
        "rank_label_top_bucket_auc": _round_or_none(rank_metrics.get("top_bucket_auc")),
        "rank_label_oos_gap_pct": _round_or_none(rank_portfolio.get("gap_pct")),
        "rank_label_sharpe": _round_or_none(rank_portfolio.get("sharpe_ratio")),
        "rank_label_max_drawdown": _round_or_none(rank_portfolio.get("max_drawdown")),
        "rank_label_turnover_proxy": _round_or_none(rank_portfolio.get("turnover_proxy")),
        "current_strategy_beats_benchmark": benchmark_gap.get("beats_benchmark"),
        "current_strategy_gap_pct": benchmark_gap.get("gap_pct"),
    }

    blockers: list[str] = []
    if avg_auc is None or avg_auc < 0.53:
        blockers.append("AUC is marginal; model is not strong enough for full buy/sell control.")
    if brier is None or brier > 0.25:
        blockers.append("Probability calibration is poor (Brier above promotion gate).")
    if roc_std is None or roc_std >= 0.05:
        blockers.append("Fold ROC-AUC variance is high; regime/period behavior is unstable.")
    if challenger_oos_gap is not None and challenger_oos_gap < 0:
        blockers.append("Challenger model OOS portfolio still trails its benchmark.")
    if calibration_experiment.get("status") != "ok":
        blockers.append("Calibration candidate experiment needs raw OOF prediction rows from next retrain.")
    if label_horizon.get("status") != "ok":
        blockers.append("Label/horizon candidate report is missing; run model quality report.")
    if rank_label and not (rank_label.get("gate") or {}).get("passed"):
        blockers.append("Cross-sectional rank AI improved AUC but failed the OOS portfolio gate.")

    health = "needs_work" if blockers else "promotion_ready"
    decision = (
        "keep_ai_as_filter_and_sizing_overlay"
        if blockers
        else "eligible_for_broader_ai_control_experiment"
    )

    recommendations = [
        "Do not give AI full buy/sell authority until AUC, Brier, fold variance, and OOS portfolio gates pass together.",
        "Prioritize probability calibration by regime (Platt/isotonic candidate) before increasing AI weight in ranking or exits.",
        "Review label/horizon design: current AI is useful as a filter, but not reliable enough as the sole decision maker.",
        "Keep the 20% trailing-stop change; current strategy now beats equal-weight and SPY without increasing AI dependence.",
    ]
    if rank_label and (rank_label.get("gate") or {}).get("passed"):
        recommendations.append(
            "Promote the best cross-sectional rank label to a paper-only buy/add gate experiment; keep existing sell rules unchanged."
        )
    else:
        recommendations.append(
            "Use cross-sectional rank labels as the next AI research path, but only wire top-bucket buys/adds after OOS portfolio gate passes."
        )
    if stability.get("by_regime"):
        recommendations.append(
            "Inspect weak regimes first: BULL and NEUTRAL AUC are near/below 0.5 while BEAR has high variance."
        )
    if label_horizon.get("recommendation"):
        recommendations.append(str(label_horizon["recommendation"]))

    report = {
        "generated_at": _utc_now_iso(),
        "decision": decision,
        "health": health,
        "metrics": metrics,
        "blockers": blockers,
        "recommendations": recommendations,
        "sources": {
            "promotion": str(promotion_path),
            "calibration": str(calibration_path),
            "fold_stability": str(stability_path),
            "threshold_retune": str(threshold_path),
            "calibration_experiment": str(calibration_experiment_path),
            "label_horizon": str(label_horizon_path),
            "rank_label": rank_label_source,
            "benchmark_gap": str(benchmark_gap_path),
        },
    }
    validate_model_quality_summary(report)
    return report


def validate_model_quality_summary(report: dict[str, Any]) -> dict[str, Any]:
    missing = [key for key in MODEL_QUALITY_SUMMARY_KEYS if key not in report]
    if missing:
        raise ValueError(f"Missing model quality summary keys: {missing}")
    return report


def format_model_quality_summary(report: dict[str, Any]) -> str:
    metrics = report["metrics"]
    lines = [
        "# Model Quality Summary",
        "",
        f"- Decision: `{report['decision']}`",
        f"- Health: `{report['health']}`",
        f"- Challenger AUC: {metrics.get('challenger_avg_roc_auc')}",
        f"- Brier: {metrics.get('overall_avg_brier_score')}",
        f"- Fold ROC-AUC std: {metrics.get('roc_auc_std')}",
        f"- Challenger OOS gap: {metrics.get('challenger_oos_gap_vs_benchmark')}",
        f"- Rank-label OOS gap: {metrics.get('rank_label_oos_gap_pct')}pp",
        f"- Rank-label Sharpe: {metrics.get('rank_label_sharpe')}",
        f"- Rank-label MDD: {metrics.get('rank_label_max_drawdown')}",
        f"- Current strategy gap: {metrics.get('current_strategy_gap_pct')}pp",
        "",
        "## Blockers",
    ]
    blockers = report.get("blockers") or []
    lines.extend([f"- {item}" for item in blockers] or ["- None"])
    lines.extend(["", "## Recommendations"])
    lines.extend(f"- {item}" for item in report.get("recommendations") or [])
    return "\n".join(lines)


def write_model_quality_summary(
    report: dict[str, Any],
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> tuple[Path, Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "latest_summary.json"
    md_path = output_dir / "latest_summary.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(format_model_quality_summary(report), encoding="utf-8")
    return json_path, md_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build operator model quality summary")
    parser.add_argument("--ml-dir", default=str(DEFAULT_ML_DIR))
    parser.add_argument("--benchmark-gap", default=str(DEFAULT_BENCHMARK_GAP_PATH))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    report = build_model_quality_summary(
        ml_dir=args.ml_dir,
        benchmark_gap_path=args.benchmark_gap,
    )
    json_path, md_path = write_model_quality_summary(report, args.output_dir)
    print(format_model_quality_summary(report))
    print(f"\nWrote {json_path} and {md_path}")


if __name__ == "__main__":
    main()
