import json

import pandas as pd

from src.regime_weakness_report import build_regime_weakness_report


def test_regime_weakness_report_detects_weak_regimes(tmp_path):
    fold = tmp_path / "fold_metrics.csv"
    pd.DataFrame(
        [
            {"regime": "BULL", "roc_auc": 0.49},
            {"regime": "BULL", "roc_auc": 0.50},
            {"regime": "NEUTRAL", "roc_auc": 0.48},
            {"regime": "NEUTRAL", "roc_auc": 0.52},
            {"regime": "BEAR", "roc_auc": 0.56},
            {"regime": "BEAR", "roc_auc": 0.58},
        ]
    ).to_csv(fold, index=False)
    feature = tmp_path / "feature_stats.json"
    feature.write_text(
        json.dumps(
            {
                "feature_stats": {
                    "spy_rel_return_20d": {"mean": 0.1},
                    "volatility_20d": {"mean": 0.2},
                }
            }
        ),
        encoding="utf-8",
    )

    report = build_regime_weakness_report(
        fold_metrics_path=fold,
        feature_stats_path=feature,
    )
    assert report["status"] == "ok"
    assert "BULL" in report["weak_regimes"]
    assert report["regimes"]["BEAR"]["weak_regime"] is False
    assert "spy_rel_return_20d" in report["feature_watchlist"]


def test_regime_weakness_report_missing_fold_metrics(tmp_path):
    report = build_regime_weakness_report(
        fold_metrics_path=tmp_path / "missing.csv",
        feature_stats_path=tmp_path / "missing_feature.json",
    )
    assert report["status"] == "missing_fold_metrics"
