import json
from pathlib import Path

import pandas as pd

from src.regime_feature_experiment import (
    augment_experiment_features,
    build_regime_feature_experiment_report,
)


def _fake_regime_frame(rows: int = 120) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=rows, freq="D"),
            "regime": ["BULL"] * rows,
            "target": [i % 2 for i in range(rows)],
            "ticker": ["AAPL"] * rows,
            "return_20d": [0.01] * rows,
            "spy_rel_return_20d": [0.0] * rows,
            "ma_ratio_20_200": [1.0] * rows,
            "vix_percentile_52w": [0.5] * rows,
            "volatility_20d": [0.2] * rows,
            "yield_spread_10y3m": [0.1] * rows,
            "return_5d": [0.0] * rows,
            "rsi_14": [50.0] * rows,
        }
    )


def test_augment_experiment_features_adds_sector_and_breadth():
    frame = _fake_regime_frame(10)
    frame.loc[0:4, "ticker"] = "AAPL"
    frame.loc[5:9, "ticker"] = "MSFT"
    out = augment_experiment_features(frame)
    assert "sector_momentum_20d" in out.columns
    assert "market_breadth_20d" in out.columns


def test_regime_feature_experiment_flags_passing_bundle(tmp_path: Path, monkeypatch):
    weakness = tmp_path / "weak.json"
    weakness.write_text(json.dumps({"weak_regimes": ["BULL"]}), encoding="utf-8")

    monkeypatch.setattr(
        "src.regime_feature_experiment._build_regime_feature_dataset",
        lambda *args, **kwargs: _fake_regime_frame(),
    )
    monkeypatch.setattr(
        "src.regime_feature_experiment.augment_experiment_features",
        lambda frame: frame,
    )
    monkeypatch.setattr(
        "src.regime_feature_experiment._collect_regime_cv_metrics",
        lambda regime, data, **kwargs: (
            [{"roc_auc": 0.53, "fold": 1}, {"roc_auc": 0.54, "fold": 2}],
            [],
        ),
    )

    report = build_regime_feature_experiment_report(
        weakness_path=weakness,
        training_data={"AAPL": pd.DataFrame()},
    )
    assert report["status"] == "ok"
    assert report["best_per_regime"]["BULL"]["passes_gate"] is True


def test_regime_feature_experiment_no_weak_regimes(tmp_path: Path):
    weakness = tmp_path / "weak.json"
    weakness.write_text(json.dumps({"weak_regimes": []}), encoding="utf-8")
    report = build_regime_feature_experiment_report(
        weakness_path=weakness,
        training_data={},
    )
    assert report["status"] == "no_weak_regimes"
