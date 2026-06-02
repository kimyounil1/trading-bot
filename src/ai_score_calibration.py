"""Post-hoc calibration overlay for AI scores (no champion model swap)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

DEFAULT_CALIBRATION_BINS_PATH = Path("logs/ml/model_calibration_bins.csv")


def _to_float(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(out):
        return None
    return out


@lru_cache(maxsize=4)
def _load_bins(path: str) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.is_file():
        return pd.DataFrame()
    frame = pd.read_csv(csv_path)
    required = {"regime", "avg_pred", "actual_rate"}
    if not required.issubset(frame.columns):
        return pd.DataFrame()
    out = frame.copy()
    out["regime"] = out["regime"].astype(str).str.upper()
    out["avg_pred"] = pd.to_numeric(out["avg_pred"], errors="coerce")
    out["actual_rate"] = pd.to_numeric(out["actual_rate"], errors="coerce")
    out = out.dropna(subset=["avg_pred", "actual_rate"])
    return out.sort_values(["regime", "avg_pred"]).reset_index(drop=True)


def calibrate_ai_score(
    raw_score: float | None,
    *,
    regime: str = "NEUTRAL",
    bins_path: str | Path = DEFAULT_CALIBRATION_BINS_PATH,
) -> float | None:
    """Map raw score to empirical actual_rate using nearest avg_pred bin."""
    score = _to_float(raw_score)
    if score is None:
        return None
    score = max(0.0, min(1.0, score))

    frame = _load_bins(str(Path(bins_path)))
    if frame.empty:
        return score

    regime_key = str(regime or "NEUTRAL").upper()
    subset = frame[frame["regime"] == regime_key]
    if subset.empty:
        subset = frame[frame["regime"] == "NEUTRAL"]
    if subset.empty:
        subset = frame
    if subset.empty:
        return score

    nearest_idx = (subset["avg_pred"] - score).abs().idxmin()
    calibrated = _to_float(subset.loc[nearest_idx, "actual_rate"])
    if calibrated is None:
        return score
    return max(0.0, min(1.0, calibrated))

