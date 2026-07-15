import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pandas as pd

from src.data_loader import load_price_data_batch
from src.features import build_inference_features
from src.ml_model import RegimeAwareModelWrapper
from src.portfolio_backtester import _prepare_ticker_frame, build_ai_score_frames
from src.rank_ai_gate import (
    build_rank_ai_gate_score_history,
    build_rank_ai_gate_scores,
)


def _sample_price_frame(rows: int = 260) -> pd.DataFrame:
    values = np.arange(rows, dtype=float)
    return pd.DataFrame(
        {
            "date": pd.date_range("2023-01-01", periods=rows),
            "open": values + 1.0,
            "high": values + 2.0,
            "low": values + 0.5,
            "close": values + 1.5,
            "adj_close": values + 1.5,
            "volume": values + 100.0,
        }
    )


class DummyClassifier:
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        size = len(X)
        return np.column_stack([np.zeros(size), np.linspace(0.1, 0.9, size)])

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        size = len(X)
        return np.ones(size, dtype=int)


class FixedClassifier:
    def __init__(self, score: float) -> None:
        self.score = score

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        scores = np.full(len(X), self.score)
        return np.column_stack([1.0 - scores, scores])

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return np.full(len(X), int(self.score >= 0.5), dtype=int)


class FixedRegressor:
    def __init__(self, score: float) -> None:
        self.score = score

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return np.full(len(X), self.score)


class DummyModelBundle:
    prediction_horizon = 5
    target_return_threshold = 0.0

    def predict_proba(self, df: pd.DataFrame, vix_df=None, spy_df=None, macro_df=None) -> pd.Series:
        size = len(
            build_inference_features(
                df,
                prediction_horizon=self.prediction_horizon,
                target_return_threshold=self.target_return_threshold,
            )
        )
        return pd.Series(np.linspace(0.2, 0.8, size))


class RecentChangesTest(unittest.TestCase):
    def test_inference_features_include_latest_completed_row(self) -> None:
        raw = _sample_price_frame(280)

        features = build_inference_features(raw, prediction_horizon=20)

        self.assertEqual(
            pd.Timestamp(features["date"].max()),
            pd.Timestamp(raw["date"].max()),
        )

    def test_inference_features_ignore_incomplete_latest_session(self) -> None:
        raw = _sample_price_frame(280)
        incomplete = raw.iloc[-1].copy()
        incomplete["date"] = pd.Timestamp(raw["date"].max()) + pd.Timedelta(days=1)
        incomplete[["open", "high", "low", "close", "adj_close", "volume"]] = np.nan
        with_placeholder = pd.concat(
            [raw, pd.DataFrame([incomplete])],
            ignore_index=True,
        )

        features = build_inference_features(with_placeholder, prediction_horizon=20)

        self.assertEqual(
            pd.Timestamp(features["date"].max()),
            pd.Timestamp(raw["date"].max()),
        )

    def test_sklearn_wrapper_returns_series_from_numpy_outputs(self) -> None:
        feature_df = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=3),
                "feature_a": [1.0, 2.0, 3.0],
                "feature_b": [4.0, 5.0, 6.0],
            }
        )
        wrapper = RegimeAwareModelWrapper(
            {"NEUTRAL": DummyClassifier()},
            ["feature_a", "feature_b"],
            prediction_horizon=5,
            target_return_threshold=0.0,
        )

        with patch("src.ml_model.build_inference_features", return_value=feature_df):
            proba = wrapper.predict_proba(_sample_price_frame(60))
            pred = wrapper.predict(_sample_price_frame(60))

        self.assertEqual(proba.tolist(), [0.1, 0.5, 0.9])
        self.assertEqual(pred.tolist(), [1, 1, 1])

    def test_wrapper_selects_model_using_each_rows_point_in_time_regime(self) -> None:
        feature_df = pd.DataFrame(
            {
                "date": pd.date_range("2026-01-02", periods=3),
                "feature_a": [1.0, 2.0, 3.0],
            }
        )
        regimes = pd.Series(
            ["BULL", "BEAR", "BULL"],
            index=pd.to_datetime(feature_df["date"]),
        )
        wrapper = RegimeAwareModelWrapper(
            {
                "BULL": FixedClassifier(0.8),
                "BEAR": FixedClassifier(0.2),
                "NEUTRAL": FixedClassifier(0.5),
            },
            ["feature_a"],
            prediction_horizon=5,
            target_return_threshold=0.0,
        )

        with (
            patch("src.ml_model.build_inference_features", return_value=feature_df),
            patch("src.ml_model.compute_daily_regime", return_value=regimes),
        ):
            scores = wrapper.predict_proba(
                _sample_price_frame(60),
                spy_df=_sample_price_frame(60),
                vix_df=_sample_price_frame(60),
            )

        self.assertEqual(scores.tolist(), [0.8, 0.2, 0.8])

    def test_prepare_ticker_frame_uses_model_bundle_interface(self) -> None:
        frame = _prepare_ticker_frame(
            "AAPL",
            _sample_price_frame(),
            use_ai_score=True,
            ai_score_buy_threshold=0.0,
            ai_model_bundle=DummyModelBundle(),
        )

        self.assertGreater(frame["ai_score"].notna().sum(), 0)

    def test_ai_score_frames_skip_only_short_history_ticker(self) -> None:
        with self.assertWarnsRegex(RuntimeWarning, "SHORT"):
            frames = build_ai_score_frames(
                {
                    "AAPL": _sample_price_frame(280),
                    "SHORT": _sample_price_frame(20),
                },
                ai_model_bundle=DummyModelBundle(),
            )

        self.assertEqual(set(frames), {"AAPL"})

    def test_rank_history_latest_day_matches_live_point_in_time_score(self) -> None:
        ticker_data = {
            "AAPL": _sample_price_frame(300),
            "MSFT": _sample_price_frame(300),
        }
        settings = SimpleNamespace(
            rank_ai_buy_gate_enabled=True,
            rank_ai_buy_gate_fail_closed=True,
            rank_ai_buy_gate_prediction_horizon=20,
            rank_ai_buy_gate_min_score_quantile=0.85,
            rank_ai_buy_gate_top_bucket_pct=0.15,
        )
        bundle = {
            "classifier": FixedClassifier(0.7),
            "regressor": FixedRegressor(0.6),
            "config": {"prediction_horizon": 20},
        }

        with (
            patch("src.rank_ai_gate._model_path", return_value=Path(__file__)),
            patch("src.rank_ai_gate.joblib.load", return_value=bundle),
        ):
            history = build_rank_ai_gate_score_history(ticker_data, settings)
            latest = build_rank_ai_gate_scores(ticker_data, settings)

        latest_date = pd.Timestamp(ticker_data["AAPL"]["date"].max())
        self.assertIn(latest_date, history)
        for ticker in ticker_data:
            self.assertAlmostEqual(
                history[latest_date][ticker].score,
                latest[ticker].score,
            )
            self.assertAlmostEqual(
                history[latest_date][ticker].percentile,
                latest[ticker].percentile,
            )

    def test_rank_history_uses_point_in_time_universe(self) -> None:
        ticker_data = {
            "AAPL": _sample_price_frame(300),
            "FUTURE": _sample_price_frame(300),
        }
        settings = SimpleNamespace(
            rank_ai_buy_gate_enabled=True,
            rank_ai_buy_gate_fail_closed=True,
            rank_ai_buy_gate_prediction_horizon=20,
            rank_ai_buy_gate_min_score_quantile=0.85,
            rank_ai_buy_gate_top_bucket_pct=0.15,
        )
        bundle = {
            "classifier": FixedClassifier(0.7),
            "regressor": FixedRegressor(0.6),
            "config": {"prediction_horizon": 20},
        }
        first_snapshot = pd.Timestamp(ticker_data["AAPL"]["date"].max()) + pd.Timedelta(days=1)

        with (
            patch("src.rank_ai_gate._model_path", return_value=Path(__file__)),
            patch("src.rank_ai_gate.joblib.load", return_value=bundle),
        ):
            history = build_rank_ai_gate_score_history(
                ticker_data,
                settings,
                historical_universe_by_date={first_snapshot: ["AAPL", "FUTURE"]},
                base_universe={"AAPL"},
            )

        latest_date = pd.Timestamp(ticker_data["AAPL"]["date"].max())
        self.assertEqual(set(history[latest_date]), {"AAPL"})

    def test_load_price_data_batch_raises_when_ticker_is_missing(self) -> None:
        with patch("src.data_loader.yf.download", return_value=pd.DataFrame()):
            with self.assertRaisesRegex(ValueError, "Failed to load batch price data"):
                load_price_data_batch(["AAPL", "MSFT"], force_refresh=True)


if __name__ == "__main__":
    unittest.main()
