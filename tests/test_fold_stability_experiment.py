import pandas as pd

from src.fold_stability_experiment import (
    _metrics_summary,
    build_fold_stability_experiment_report,
)


def test_metrics_summary_passes_low_std_gate():
    summary = _metrics_summary(
        [{"roc_auc": 0.52}, {"roc_auc": 0.53}, {"roc_auc": 0.51}]
    )
    assert summary["roc_auc_std"] < 0.05
    assert summary["passes_gate"] is True


def test_fold_stability_experiment_report(monkeypatch):
    frame = pd.DataFrame(
        {
            "regime": ["BEAR"] * 120,
            "target": [i % 2 for i in range(120)],
            "return_1d": [0.0] * 120,
            "return_5d": [0.0] * 120,
            "return_10d": [0.0] * 120,
            "return_20d": [0.0] * 120,
            "volatility_10d": [0.1] * 120,
            "volatility_20d": [0.1] * 120,
            "volume_change_5d": [0.0] * 120,
            "ma_ratio_10_50": [1.0] * 120,
            "ma_ratio_20_200": [1.0] * 120,
            "rsi_14": [50.0] * 120,
            "macd": [0.0] * 120,
            "macd_signal": [0.0] * 120,
            "atr_pct": [0.01] * 120,
            "high_52w_ratio": [0.9] * 120,
            "low_52w_ratio": [1.1] * 120,
            "vix_level": [20.0] * 120,
            "spy_rel_return_20d": [0.0] * 120,
            "yield_spread_10y3m": [0.0] * 120,
            "dxy_20d_return": [0.0] * 120,
            "gold_20d_return": [0.0] * 120,
            "vix_percentile_52w": [0.5] * 120,
            "skew_level": [0.0] * 120,
            "vvix_level": [80.0] * 120,
            "vvix_20d_return": [0.0] * 120,
        }
    )

    monkeypatch.setattr(
        "src.fold_stability_experiment._build_regime_feature_dataset",
        lambda *args, **kwargs: frame,
    )

    call_count = {"n": 0}

    def _fake_cv(regime, data, **kwargs):
        call_count["n"] += 1
        std = 0.08 if kwargs.get("lgbm_params") == {} else 0.03
        mean = 0.51
        return (
            [{"roc_auc": mean + std / 2, "fold": 1}, {"roc_auc": mean - std / 2, "fold": 2}],
            [],
        )

    monkeypatch.setattr("src.fold_stability_experiment._collect_regime_cv_metrics", _fake_cv)

    report = build_fold_stability_experiment_report(training_data={"X": pd.DataFrame()})
    assert report["status"] == "ok"
    assert report["best_overall"] is not None
    assert call_count["n"] > 0
