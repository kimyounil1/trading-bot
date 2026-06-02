"""Evaluate post-hoc probability calibration candidates for AI scores."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score


DEFAULT_ROWS_PATH = Path("logs/ml/model_calibration_rows.csv")
DEFAULT_OUTPUT_DIR = Path("logs/ml")

CALIBRATION_EXPERIMENT_KEYS = (
    "generated_at",
    "source_path",
    "status",
    "overall",
    "by_regime",
    "recommendation",
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _empty_report(path: Path, reason: str) -> dict[str, Any]:
    return {
        "generated_at": _utc_now_iso(),
        "source_path": str(path),
        "status": "missing_data",
        "overall": {},
        "by_regime": {},
        "recommendation": reason,
    }


def _score(y_true: pd.Series, y_prob: pd.Series) -> dict[str, float | None]:
    y = pd.to_numeric(y_true, errors="coerce")
    p = pd.to_numeric(y_prob, errors="coerce").clip(0.0, 1.0)
    frame = pd.DataFrame({"y": y, "p": p}).dropna()
    if frame.empty:
        return {"brier": None, "roc_auc": None}
    brier = float(brier_score_loss(frame["y"], frame["p"]))
    try:
        auc = float(roc_auc_score(frame["y"], frame["p"]))
    except ValueError:
        auc = None
    return {"brier": brier, "roc_auc": auc}


def _platt_predict(train: pd.DataFrame, test: pd.DataFrame) -> pd.Series:
    model = LogisticRegression(solver="lbfgs")
    model.fit(train[["y_prob"]], train["y_true"].astype(int))
    return pd.Series(model.predict_proba(test[["y_prob"]])[:, 1], index=test.index)


def _isotonic_predict(train: pd.DataFrame, test: pd.DataFrame) -> pd.Series:
    model = IsotonicRegression(out_of_bounds="clip")
    model.fit(train["y_prob"], train["y_true"].astype(int))
    return pd.Series(model.predict(test["y_prob"]), index=test.index)


def _cross_fold_calibration(frame: pd.DataFrame, method: str) -> pd.Series:
    predictions = pd.Series(index=frame.index, dtype=float)
    folds = sorted(frame["fold"].dropna().unique().tolist())
    if len(folds) < 2:
        return predictions

    for fold in folds:
        train = frame[frame["fold"] != fold]
        test = frame[frame["fold"] == fold]
        if train.empty or test.empty or train["y_true"].nunique() < 2:
            continue
        if method == "platt":
            predictions.loc[test.index] = _platt_predict(train, test)
        elif method == "isotonic":
            predictions.loc[test.index] = _isotonic_predict(train, test)
        else:
            raise ValueError(f"Unknown calibration method: {method}")
    return predictions


def _evaluate_group(frame: pd.DataFrame) -> dict[str, Any]:
    base = _score(frame["y_true"], frame["y_prob"])
    out: dict[str, Any] = {
        "rows": int(len(frame)),
        "base": base,
        "platt": {"brier": None, "roc_auc": None},
        "isotonic": {"brier": None, "roc_auc": None},
    }
    if len(frame) < 50 or frame["fold"].nunique(dropna=True) < 2:
        out["note"] = "Need at least two folds and 50 rows for calibration candidate scoring."
        return out

    for method in ("platt", "isotonic"):
        preds = _cross_fold_calibration(frame, method)
        valid = preds.notna()
        if valid.any():
            out[method] = _score(frame.loc[valid, "y_true"], preds.loc[valid])
    return out


def _best_method(overall: dict[str, Any]) -> tuple[str, float | None]:
    candidates = {
        "base": overall.get("base", {}).get("brier"),
        "platt": overall.get("platt", {}).get("brier"),
        "isotonic": overall.get("isotonic", {}).get("brier"),
    }
    valid = {k: v for k, v in candidates.items() if v is not None}
    if not valid:
        return "none", None
    best = min(valid, key=valid.get)
    return best, valid[best]


def build_calibration_experiment_report(
    rows_path: str | Path = DEFAULT_ROWS_PATH,
) -> dict[str, Any]:
    path = Path(rows_path)
    if not path.is_file():
        return _empty_report(
            path,
            "Run retrain first so logs/ml/model_calibration_rows.csv is generated.",
        )

    frame = pd.read_csv(path)
    required = {"regime", "fold", "y_true", "y_prob"}
    missing = sorted(required - set(frame.columns))
    if missing:
        return _empty_report(path, f"Missing calibration row columns: {missing}")

    frame = frame.dropna(subset=["regime", "fold", "y_true", "y_prob"]).copy()
    if frame.empty:
        return _empty_report(path, "Calibration rows are empty after cleaning.")
    frame["fold"] = pd.to_numeric(frame["fold"], errors="coerce")
    frame["y_true"] = pd.to_numeric(frame["y_true"], errors="coerce").astype(int)
    frame["y_prob"] = pd.to_numeric(frame["y_prob"], errors="coerce").clip(0.0, 1.0)
    frame = frame.dropna(subset=["fold", "y_prob"])

    overall = _evaluate_group(frame)
    by_regime = {
        str(regime): _evaluate_group(regime_df.copy())
        for regime, regime_df in frame.groupby("regime")
    }
    best, best_brier = _best_method(overall)
    base_brier = overall.get("base", {}).get("brier")
    improvement = (
        float(base_brier) - float(best_brier)
        if base_brier is not None and best_brier is not None
        else None
    )
    recommendation = (
        f"Evaluate {best} calibration in paper scoring path."
        if best not in {"none", "base"} and improvement is not None and improvement > 0
        else "Do not add a calibrator yet; candidate did not improve out-of-fold Brier."
    )

    report = {
        "generated_at": _utc_now_iso(),
        "source_path": str(path),
        "status": "ok",
        "overall": {
            **overall,
            "best_method": best,
            "brier_improvement": improvement,
        },
        "by_regime": by_regime,
        "recommendation": recommendation,
    }
    validate_calibration_experiment_report(report)
    return report


def validate_calibration_experiment_report(report: dict[str, Any]) -> dict[str, Any]:
    missing = [key for key in CALIBRATION_EXPERIMENT_KEYS if key not in report]
    if missing:
        raise ValueError(f"Missing calibration experiment report keys: {missing}")
    return report


def write_calibration_experiment_report(
    report: dict[str, Any],
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "calibration_experiment_report.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate AI score calibration candidates")
    parser.add_argument("--rows", default=str(DEFAULT_ROWS_PATH))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    report = build_calibration_experiment_report(args.rows)
    path = write_calibration_experiment_report(report, args.output_dir)
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
