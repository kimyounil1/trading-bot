"""Analyze fold ROC-AUC dispersion from training metrics (report-only)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.ml_quality_report import (
    ROC_AUC_STD_WARN_THRESHOLD,
    build_fold_stability_report,
    normalize_fold_metrics_df,
)

DEFAULT_METRICS_PATH = Path("logs/ml/ai_model_metrics.csv")
DEFAULT_OUTPUT_DIR = Path("logs/ml")

FOLD_VARIANCE_REPORT_KEYS = (
    "generated_at",
    "source_path",
    "stability",
    "drivers",
    "reproduction",
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _infer_drivers(metrics_df: pd.DataFrame, stability: dict[str, Any]) -> list[dict[str, Any]]:
    drivers: list[dict[str, Any]] = []
    if metrics_df.empty:
        return drivers

    frame = normalize_fold_metrics_df(metrics_df)
    roc = pd.to_numeric(frame["roc_auc"], errors="coerce")
    worst_idx = roc.idxmin()
    best_idx = roc.idxmax()
    if pd.notna(worst_idx):
        row = frame.loc[worst_idx]
        drivers.append(
            {
                "type": "worst_fold",
                "fold": int(row.get("fold", worst_idx)),
                "roc_auc": float(row["roc_auc"]),
                "hint": _fold_row_hint(row),
            }
        )
    if pd.notna(best_idx) and best_idx != worst_idx:
        row = frame.loc[best_idx]
        drivers.append(
            {
                "type": "best_fold",
                "fold": int(row.get("fold", best_idx)),
                "roc_auc": float(row["roc_auc"]),
                "hint": _fold_row_hint(row),
            }
        )

    std = (stability.get("roc_auc") or {}).get("std")
    if std is not None and std >= ROC_AUC_STD_WARN_THRESHOLD:
        drivers.append(
            {
                "type": "high_variance",
                "roc_auc_std": std,
                "threshold": ROC_AUC_STD_WARN_THRESHOLD,
                "hint": "Fold spread exceeds promotion stability warning; review regime mix and label balance per fold.",
            }
        )
    return drivers


def _fold_row_hint(row: pd.Series) -> str:
    parts: list[str] = []
    if "test_positive_rate" in row and pd.notna(row["test_positive_rate"]):
        rate = float(row["test_positive_rate"])
        if rate > 0.58:
            parts.append(f"high test positive rate ({rate:.2f})")
        elif rate < 0.48:
            parts.append(f"low test positive rate ({rate:.2f})")
    if "prediction_positive_rate" in row and pd.notna(row["prediction_positive_rate"]):
        pred = float(row["prediction_positive_rate"])
        obs = float(row["test_positive_rate"]) if pd.notna(row.get("test_positive_rate")) else None
        if obs is not None and abs(pred - obs) > 0.15:
            parts.append(f"prediction/label mismatch (pred={pred:.2f}, actual={obs:.2f})")
    if "regime" in row and pd.notna(row["regime"]):
        parts.append(f"regime={row['regime']}")
    return "; ".join(parts) if parts else "inspect fold label distribution and features"


def build_fold_variance_report(
    metrics_path: str | Path = DEFAULT_METRICS_PATH,
) -> dict[str, Any]:
    path = Path(metrics_path)
    if not path.is_file():
        raise FileNotFoundError(f"Fold metrics not found: {path}")

    metrics_df = pd.read_csv(path)
    stability = build_fold_stability_report(metrics_df)
    report = {
        "generated_at": _utc_now_iso(),
        "source_path": str(path),
        "stability": stability,
        "drivers": _infer_drivers(metrics_df, stability),
        "reproduction": {
            "command": f"PYTHONPATH=. .venv/bin/python -m src.fold_variance_report --metrics-path {path}",
            "full_walk_forward": "PYTHONPATH=. .venv/bin/python -m src.walk_forward_validation",
        },
    }
    validate_fold_variance_report(report)
    return report


def validate_fold_variance_report(report: dict[str, Any]) -> dict[str, Any]:
    for key in FOLD_VARIANCE_REPORT_KEYS:
        if key not in report:
            raise ValueError(f"Missing fold variance report key: {key}")
    return report


def format_fold_variance_note(report: dict[str, Any]) -> str:
    stability = report["stability"]
    roc = stability.get("roc_auc", {})
    lines = [
        "# Fold ROC-AUC variance note (generated)",
        "",
        f"Source: `{report['source_path']}`",
        f"Generated: {report['generated_at']}",
        "",
        "## Summary",
        f"- Fold count: {stability.get('fold_count')}",
        f"- ROC-AUC mean: {roc.get('mean')}",
        f"- ROC-AUC std: {roc.get('std')} (warn threshold {ROC_AUC_STD_WARN_THRESHOLD})",
        f"- High variance warning: {stability.get('high_variance_warning')}",
        "",
        "## Likely drivers",
    ]
    for driver in report.get("drivers") or []:
        lines.append(f"- **{driver['type']}**: {driver.get('hint', driver)}")
    lines.extend(
        [
            "",
            "## Reproduce",
            f"- Quick: `{report['reproduction']['command']}`",
            f"- Full walk-forward: `{report['reproduction']['full_walk_forward']}`",
        ]
    )
    return "\n".join(lines)


def write_fold_variance_artifacts(
    report: dict[str, Any],
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "fold_variance_report.json"
    note_path = output_dir / "fold_variance_note.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    note_path.write_text(format_fold_variance_note(report), encoding="utf-8")
    return json_path, note_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Fold ROC-AUC variance analysis report")
    parser.add_argument("--metrics-path", default=str(DEFAULT_METRICS_PATH))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    report = build_fold_variance_report(args.metrics_path)
    json_path, note_path = write_fold_variance_artifacts(report, Path(args.output_dir))
    print(format_fold_variance_note(report))
    print(f"\nWrote {json_path} and {note_path}")


if __name__ == "__main__":
    main()
