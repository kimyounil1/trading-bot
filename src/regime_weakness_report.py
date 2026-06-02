"""Diagnose regime-level weakness from fold metrics and feature stats."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

DEFAULT_FOLD_METRICS_PATH = Path("logs/ml/fold_metrics.csv")
DEFAULT_FEATURE_STATS_PATH = Path("models/ai_feature_stats.json")
DEFAULT_OUTPUT_DIR = Path("logs/ml")
DEFAULT_OUTPUT_NAME = "regime_weakness_report.json"

WEAK_REGIME_AUC_THRESHOLD = 0.50
HIGH_VARIANCE_STD_THRESHOLD = 0.05


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_float(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(out):
        return None
    return out


def _candidate_feature_watchlist(feature_stats: dict[str, Any]) -> list[str]:
    candidates = [
        "spy_rel_return_20d",
        "ma_ratio_20_200",
        "vix_percentile_52w",
        "volatility_20d",
        "yield_spread_10y3m",
    ]
    return [name for name in candidates if name in feature_stats]


def build_regime_weakness_report(
    *,
    fold_metrics_path: str | Path = DEFAULT_FOLD_METRICS_PATH,
    feature_stats_path: str | Path = DEFAULT_FEATURE_STATS_PATH,
) -> dict[str, Any]:
    fold_path = Path(fold_metrics_path)
    if not fold_path.is_file():
        return {
            "generated_at": _utc_now_iso(),
            "status": "missing_fold_metrics",
            "fold_metrics_path": str(fold_path),
            "feature_stats_path": str(feature_stats_path),
            "regimes": {},
            "weak_regimes": [],
            "recommendations": ["Run retrain first to generate logs/ml/fold_metrics.csv."],
        }

    fold_df = pd.read_csv(fold_path)
    if fold_df.empty or "regime" not in fold_df.columns or "roc_auc" not in fold_df.columns:
        return {
            "generated_at": _utc_now_iso(),
            "status": "invalid_fold_metrics",
            "fold_metrics_path": str(fold_path),
            "feature_stats_path": str(feature_stats_path),
            "regimes": {},
            "weak_regimes": [],
            "recommendations": ["fold_metrics.csv must contain regime and roc_auc columns."],
        }

    fold_df["regime"] = fold_df["regime"].astype(str).str.upper()
    fold_df["roc_auc"] = pd.to_numeric(fold_df["roc_auc"], errors="coerce")
    fold_df = fold_df.dropna(subset=["roc_auc"])

    regimes: dict[str, Any] = {}
    weak_regimes: list[str] = []
    for regime, group in fold_df.groupby("regime"):
        auc_mean = float(group["roc_auc"].mean())
        auc_std = float(group["roc_auc"].std(ddof=0)) if len(group) > 1 else 0.0
        is_weak = auc_mean < WEAK_REGIME_AUC_THRESHOLD
        is_high_var = auc_std >= HIGH_VARIANCE_STD_THRESHOLD
        if is_weak:
            weak_regimes.append(regime)
        regimes[regime] = {
            "folds": int(len(group)),
            "roc_auc_mean": auc_mean,
            "roc_auc_std": auc_std,
            "weak_regime": is_weak,
            "high_variance": is_high_var,
        }

    feature_stats_payload = {}
    stats_path = Path(feature_stats_path)
    if stats_path.is_file():
        try:
            raw = json.loads(stats_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                feature_stats_payload = raw.get("feature_stats") or {}
        except json.JSONDecodeError:
            feature_stats_payload = {}

    watchlist = _candidate_feature_watchlist(feature_stats_payload)
    feature_snapshot = {
        key: feature_stats_payload.get(key)
        for key in watchlist
    }
    recommendations: list[str] = []
    if weak_regimes:
        recommendations.append(
            f"Weak regimes detected: {', '.join(weak_regimes)} (mean ROC-AUC < {WEAK_REGIME_AUC_THRESHOLD:.2f})."
        )
        recommendations.append(
            "Run targeted feature experiments for weak regimes only (report-only; do not promote champion)."
        )
    if any(info.get("high_variance") for info in regimes.values()):
        recommendations.append(
            "Fold variance is high in at least one regime; prioritize stability before any authority expansion."
        )
    if not recommendations:
        recommendations.append("No regime-level weakness flags triggered by current thresholds.")

    return {
        "generated_at": _utc_now_iso(),
        "status": "ok",
        "fold_metrics_path": str(fold_path),
        "feature_stats_path": str(stats_path),
        "thresholds": {
            "weak_regime_auc_mean_lt": WEAK_REGIME_AUC_THRESHOLD,
            "high_variance_auc_std_gte": HIGH_VARIANCE_STD_THRESHOLD,
        },
        "regimes": regimes,
        "weak_regimes": weak_regimes,
        "feature_watchlist": watchlist,
        "feature_watchlist_snapshot": feature_snapshot,
        "recommendations": recommendations,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Regime weakness diagnostic report")
    parser.add_argument("--fold-metrics-path", default=str(DEFAULT_FOLD_METRICS_PATH))
    parser.add_argument("--feature-stats-path", default=str(DEFAULT_FEATURE_STATS_PATH))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    report = build_regime_weakness_report(
        fold_metrics_path=args.fold_metrics_path,
        feature_stats_path=args.feature_stats_path,
    )
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / DEFAULT_OUTPUT_NAME
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("=== Regime weakness report ===")
    print(f"weak_regimes={report.get('weak_regimes', [])}")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
