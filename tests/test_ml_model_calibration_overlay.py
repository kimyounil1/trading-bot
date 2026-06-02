import pandas as pd

from src.ml_model import predict_ai_score_from_bundle


class _DummyModel:
    def predict_proba(self, df, vix_df=None, spy_df=None, macro_df=None):
        return pd.Series([0.2, 0.8], index=[0, 1])


def test_predict_ai_score_from_bundle_calibration_enabled(monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setattr(
        "src.ml_model.load_settings",
        lambda: SimpleNamespace(
            ai_score_calibration_enabled=True,
            ai_score_calibration_bins_path="dummy.csv",
        ),
    )
    monkeypatch.setattr("src.ml_model.get_current_regime", lambda spy, vix: "BULL")
    monkeypatch.setattr(
        "src.ml_model.calibrate_ai_score",
        lambda raw_score, regime, bins_path: 0.65,
    )

    score = predict_ai_score_from_bundle(
        pd.DataFrame({"close": [1, 2]}),
        _DummyModel(),
        vix_df=pd.DataFrame({"close": [10, 11]}),
        spy_df=pd.DataFrame({"close": [100, 101]}),
    )
    assert score == 0.65


def test_predict_ai_score_from_bundle_calibration_disabled(monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setattr(
        "src.ml_model.load_settings",
        lambda: SimpleNamespace(ai_score_calibration_enabled=False),
    )
    score = predict_ai_score_from_bundle(pd.DataFrame({"close": [1, 2]}), _DummyModel())
    assert score == 0.8
