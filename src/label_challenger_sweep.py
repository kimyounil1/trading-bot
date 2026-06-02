"""Compare label/horizon challengers using portfolio OOS gates (not AUC alone)."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.label_challenger_experiment import (
    build_label_challenger_experiment,
    write_label_challenger_report,
)
from src.portfolio_backtest_validation import check_portfolio_summary_thresholds
from src.promotion_thresholds import promotion_portfolio_thresholds

DEFAULT_OUTPUT = Path("logs/ml/label_challenger_sweep_report.json")

LABEL_CHALLENGER_SWEEP_KEYS = (
    "generated_at",
    "candidates",
    "best_by_portfolio_gap",
    "recommendation",
)


@dataclass(frozen=True)
class LabelCandidate:
    prediction_horizon: int
    target_return_threshold: float

    @property
    def slug(self) -> str:
        thr = f"{self.target_return_threshold:.2f}".replace(".", "p")
        return f"h{self.prediction_horizon}_t{thr}"

    @property
    def output_dir(self) -> Path:
        return Path("logs/ml/label_challenger") / self.slug


DEFAULT_CANDIDATES = (
    LabelCandidate(20, 0.0),
    LabelCandidate(20, 0.02),
    LabelCandidate(10, 0.0),
    LabelCandidate(40, 0.02),
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _portfolio_gap(snapshot: dict[str, Any] | None) -> float | None:
    if not snapshot:
        return None
    try:
        return float(snapshot["total_return"]) - float(snapshot["benchmark_return"])
    except (TypeError, ValueError, KeyError):
        return None


def _gate_status(portfolio: dict[str, Any] | None) -> dict[str, Any]:
    if not portfolio:
        return {"passed": False, "failures": ["missing_portfolio_oos"]}
    thresholds = promotion_portfolio_thresholds()
    result = check_portfolio_summary_thresholds(portfolio, thresholds)
    return {"passed": result.passed, "failures": list(result.failures)}


def _legacy_summary_path(candidate: LabelCandidate) -> Path | None:
    if candidate.prediction_horizon == 20 and candidate.target_return_threshold == 0.02:
        legacy = Path("logs/ml/label_challenger/latest_summary.json")
        if legacy.is_file():
            return legacy
    return None


def _load_or_run_candidate(
    candidate: LabelCandidate,
    *,
    period: str,
    force: bool,
) -> dict[str, Any]:
    summary_path = candidate.output_dir / "latest_summary.json"
    legacy_path = _legacy_summary_path(candidate)
    if not force:
        for path in (summary_path, legacy_path):
            if path is not None and path.is_file():
                return json.loads(path.read_text(encoding="utf-8"))

    report = build_label_challenger_experiment(
        prediction_horizon=candidate.prediction_horizon,
        target_return_threshold=candidate.target_return_threshold,
        period=period,
        output_dir=candidate.output_dir,
    )
    write_label_challenger_report(report, candidate.output_dir)
    return report


def build_label_challenger_sweep(
    *,
    candidates: tuple[LabelCandidate, ...] = DEFAULT_CANDIDATES,
    period: str = "5y",
    force_retrain: bool = False,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for candidate in candidates:
        report = _load_or_run_candidate(candidate, period=period, force=force_retrain)
        portfolio = report.get("challenger_portfolio_oos") or {}
        gap = _portfolio_gap(portfolio)
        metrics = report.get("metrics") or {}
        gate = _gate_status(portfolio)
        rows.append(
            {
                "slug": candidate.slug,
                "prediction_horizon": candidate.prediction_horizon,
                "target_return_threshold": candidate.target_return_threshold,
                "avg_roc_auc": metrics.get("avg_roc_auc"),
                "portfolio_gap_pct": None if gap is None else round(gap * 100.0, 4),
                "sharpe_ratio": portfolio.get("sharpe_ratio"),
                "max_drawdown": portfolio.get("max_drawdown"),
                "decision": report.get("decision"),
                "portfolio_gate": gate,
                "output_dir": str(candidate.output_dir),
            }
        )

    ranked = sorted(
        rows,
        key=lambda row: (
            bool((row.get("portfolio_gate") or {}).get("passed")),
            row.get("portfolio_gap_pct") if row.get("portfolio_gap_pct") is not None else -999.0,
            row.get("avg_roc_auc") if row.get("avg_roc_auc") is not None else 0.0,
        ),
        reverse=True,
    )
    best = ranked[0] if ranked else None
    recommendation = "No candidates evaluated."
    if best:
        if (best.get("portfolio_gate") or {}).get("passed"):
            recommendation = (
                f"Best portfolio candidate: {best['slug']} "
                f"(gap {best.get('portfolio_gap_pct')}pp). Review before promotion."
            )
        else:
            recommendation = (
                f"Best gap {best.get('portfolio_gap_pct')}pp for {best['slug']} "
                "but portfolio gate failed — keep champion."
            )

    return {
        "generated_at": _utc_now_iso(),
        "candidates": ranked,
        "best_by_portfolio_gap": best,
        "recommendation": recommendation,
    }


def validate_label_challenger_sweep(report: dict[str, Any]) -> dict[str, Any]:
    missing = [key for key in LABEL_CHALLENGER_SWEEP_KEYS if key not in report]
    if missing:
        raise ValueError(f"Missing label challenger sweep keys: {missing}")
    return report


def write_label_challenger_sweep(
    report: dict[str, Any],
    output_path: str | Path = DEFAULT_OUTPUT,
) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    validate_label_challenger_sweep(report)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Sweep label/horizon challengers")
    parser.add_argument("--period", default="5y")
    parser.add_argument("--force-retrain", action="store_true")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument(
        "--only",
        nargs="*",
        help="Candidate slugs to run (default: all). Example: h20_t0p00 h10_t0p00",
    )
    args = parser.parse_args()

    candidates = DEFAULT_CANDIDATES
    if args.only:
        allowed = set(args.only)
        candidates = tuple(c for c in DEFAULT_CANDIDATES if c.slug in allowed)
        if not candidates:
            raise ValueError(f"No matching candidates for --only {args.only}")

    report = build_label_challenger_sweep(
        candidates=candidates,
        period=args.period,
        force_retrain=args.force_retrain,
    )
    path = write_label_challenger_sweep(report, args.output)
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
