"""Report-only feature bundle experiments for weak regimes (no champion promotion)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.features import FEATURE_COLUMNS
from src.ml_model import _build_regime_feature_dataset, _collect_regime_cv_metrics
from src.regime_weakness_report import (
    DEFAULT_FOLD_METRICS_PATH,
    DEFAULT_OUTPUT_DIR,
    build_regime_weakness_report,
)
from src.sector import SECTOR_MAP

DEFAULT_WEAKNESS_PATH = DEFAULT_OUTPUT_DIR / "regime_weakness_report.json"
WEAK_REGIME_AUC_GATE = 0.52

EXPERIMENT_FEATURE_BUNDLES: dict[str, list[str]] = {
    "baseline": list(FEATURE_COLUMNS),
    "watchlist": [
        "spy_rel_return_20d",
        "ma_ratio_20_200",
        "vix_percentile_52w",
        "volatility_20d",
        "yield_spread_10y3m",
        "return_5d",
        "return_20d",
        "rsi_14",
    ],
    "macro_stress": [
        "spy_rel_return_20d",
        "vix_level",
        "vix_percentile_52w",
        "vvix_level",
        "yield_spread_10y3m",
        "gold_20d_return",
        "dxy_20d_return",
        "volatility_20d",
    ],
    "momentum_breadth": list(FEATURE_COLUMNS)
    + ["sector_momentum_20d", "market_breadth_20d"],
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def augment_experiment_features(dataset: pd.DataFrame) -> pd.DataFrame:
    """Add report-only sector momentum and market breadth columns."""
    if dataset.empty or "ticker" not in dataset.columns or "return_20d" not in dataset.columns:
        return dataset

    frame = dataset.copy()
    frame["sector"] = frame["ticker"].astype(str).map(SECTOR_MAP).fillna("other")
    frame["sector_momentum_20d"] = frame.groupby(["date", "sector"], observed=False)[
        "return_20d"
    ].transform("mean")
    frame["market_breadth_20d"] = frame.groupby("date", observed=False)["return_20d"].transform(
        lambda values: float((pd.to_numeric(values, errors="coerce") > 0).mean())
    )
    return frame


def _bundle_columns(name: str, dataset: pd.DataFrame) -> list[str]:
    requested = EXPERIMENT_FEATURE_BUNDLES[name]
    return [col for col in requested if col in dataset.columns]


def _evaluate_bundle(
    regime: str,
    regime_data: pd.DataFrame,
    bundle_name: str,
    feature_columns: list[str],
) -> dict[str, Any]:
    metrics, _rows = _collect_regime_cv_metrics(
        regime,
        regime_data,
        feature_columns=feature_columns,
    )
    if not metrics:
        return {
            "bundle": bundle_name,
            "feature_count": len(feature_columns),
            "folds": 0,
            "roc_auc_mean": None,
            "roc_auc_std": None,
            "passes_gate": False,
            "note": "insufficient data or no usable features",
        }

    aucs = pd.Series([row["roc_auc"] for row in metrics], dtype=float)
    mean_auc = float(aucs.mean())
    std_auc = float(aucs.std(ddof=0)) if len(aucs) > 1 else 0.0
    return {
        "bundle": bundle_name,
        "feature_count": len(feature_columns),
        "folds": int(len(metrics)),
        "roc_auc_mean": mean_auc,
        "roc_auc_std": std_auc,
        "passes_gate": mean_auc >= WEAK_REGIME_AUC_GATE,
    }


def build_regime_feature_experiment_report(
    *,
    weakness_path: str | Path = DEFAULT_WEAKNESS_PATH,
    training_data: dict[str, pd.DataFrame],
    prediction_horizon: int = 20,
    target_return_threshold: float = 0.0,
    vix_df: pd.DataFrame | None = None,
    spy_df: pd.DataFrame | None = None,
    macro_df: pd.DataFrame | None = None,
) -> dict[str, Any]:
    weakness = (
        json.loads(Path(weakness_path).read_text(encoding="utf-8"))
        if Path(weakness_path).is_file()
        else build_regime_weakness_report()
    )
    weak_regimes = [str(r).upper() for r in weakness.get("weak_regimes", [])]
    if not weak_regimes:
        return {
            "generated_at": _utc_now_iso(),
            "status": "no_weak_regimes",
            "weak_regimes": [],
            "auc_gate": WEAK_REGIME_AUC_GATE,
            "bundles": list(EXPERIMENT_FEATURE_BUNDLES.keys()),
            "results": {},
            "recommendation": "No weak regimes flagged; skip targeted feature experiments.",
        }

    dataset = augment_experiment_features(
        _build_regime_feature_dataset(
            training_data,
            prediction_horizon=prediction_horizon,
            target_return_threshold=target_return_threshold,
            vix_df=vix_df,
            spy_df=spy_df,
            macro_df=macro_df,
        )
    )
    if dataset.empty:
        return {
            "generated_at": _utc_now_iso(),
            "status": "missing_training_data",
            "weak_regimes": weak_regimes,
            "auc_gate": WEAK_REGIME_AUC_GATE,
            "bundles": list(EXPERIMENT_FEATURE_BUNDLES.keys()),
            "results": {},
            "recommendation": "Training features could not be built.",
        }

    results: dict[str, Any] = {}
    best_per_regime: dict[str, dict[str, Any]] = {}
    for regime in weak_regimes:
        regime_data = dataset[dataset["regime"].astype(str).str.upper() == regime]
        bundle_results: list[dict[str, Any]] = []
        for bundle_name in EXPERIMENT_FEATURE_BUNDLES:
            cols = _bundle_columns(bundle_name, dataset)
            bundle_results.append(_evaluate_bundle(regime, regime_data, bundle_name, cols))
        results[regime] = bundle_results
        passing = [row for row in bundle_results if row.get("passes_gate")]
        best = max(bundle_results, key=lambda row: row.get("roc_auc_mean") or 0.0)
        best_per_regime[regime] = {
            "best_bundle": best.get("bundle"),
            "roc_auc_mean": best.get("roc_auc_mean"),
            "passes_gate": bool(passing),
        }

    any_pass = any(info.get("passes_gate") for info in best_per_regime.values())
    recommendation = (
        "At least one bundle clears the weak-regime AUC gate; review before any paper-only trial."
        if any_pass
        else "No bundle cleared the weak-regime AUC gate; keep champion and remain report-only."
    )

    return {
        "generated_at": _utc_now_iso(),
        "status": "ok",
        "weak_regimes": weak_regimes,
        "auc_gate": WEAK_REGIME_AUC_GATE,
        "bundles": list(EXPERIMENT_FEATURE_BUNDLES.keys()),
        "results": results,
        "best_per_regime": best_per_regime,
        "recommendation": recommendation,
    }


def write_regime_feature_experiment_report(
    report: dict[str, Any],
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "regime_feature_experiment_report.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return path


def main() -> None:
    from src.data_loader import load_price_data_batch
    from src.macro_loader import load_macro_data
    from src.retrain_holdout import exclude_holdout_from_ticker_data, portfolio_holdout_window
    from src.settings import load_settings

    parser = argparse.ArgumentParser(description="Weak-regime feature bundle experiment (report-only)")
    parser.add_argument("--weakness-path", default=str(DEFAULT_WEAKNESS_PATH))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--period", default="5y")
    args = parser.parse_args()

    settings = load_settings()
    training_data = load_price_data_batch(settings.tickers, period=args.period)
    context = load_price_data_batch(["^VIX"] + ([] if "SPY" in training_data else ["SPY"]), period=args.period)
    vix_df = context.get("^VIX")
    spy_df = training_data.get("SPY")
    if spy_df is None:
        spy_df = context.get("SPY")
    macro_df = load_macro_data(period=args.period)
    if macro_df.empty:
        macro_df = None

    holdout_start, _ = portfolio_holdout_window(training_data)
    training_fit = exclude_holdout_from_ticker_data(training_data, holdout_start)

    report = build_regime_feature_experiment_report(
        weakness_path=args.weakness_path,
        training_data=training_fit,
        vix_df=vix_df,
        spy_df=spy_df,
        macro_df=macro_df,
    )
    path = write_regime_feature_experiment_report(report, args.output_dir)
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
