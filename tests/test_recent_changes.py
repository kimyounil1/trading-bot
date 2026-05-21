import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from src.data_loader import load_price_data_batch
from src.features import build_features
from src.ml_model import SklearnModelWrapper
from src.portfolio_backtester import _prepare_ticker_frame


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


class DummyModelBundle:
    prediction_horizon = 5
    target_return_threshold = 0.0

    def predict_proba(self, df: pd.DataFrame) -> pd.Series:
        size = len(
            build_features(
                df,
                prediction_horizon=self.prediction_horizon,
                target_return_threshold=self.target_return_threshold,
            )
        )
        return pd.Series(np.linspace(0.2, 0.8, size))


class RecentChangesTest(unittest.TestCase):
    def test_sklearn_wrapper_returns_series_from_numpy_outputs(self) -> None:
        feature_df = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=3),
                "feature_a": [1.0, 2.0, 3.0],
                "feature_b": [4.0, 5.0, 6.0],
            }
        )
        wrapper = SklearnModelWrapper(
            DummyClassifier(),
            ["feature_a", "feature_b"],
            prediction_horizon=5,
            target_return_threshold=0.0,
        )

        with patch("src.ml_model.build_features", return_value=feature_df):
            proba = wrapper.predict_proba(_sample_price_frame(60))
            pred = wrapper.predict(_sample_price_frame(60))

        self.assertEqual(proba.tolist(), [0.1, 0.5, 0.9])
        self.assertEqual(pred.tolist(), [1, 1, 1])

    def test_prepare_ticker_frame_uses_model_bundle_interface(self) -> None:
        frame = _prepare_ticker_frame(
            "AAPL",
            _sample_price_frame(),
            use_ai_score=True,
            ai_score_buy_threshold=0.0,
            ai_model_bundle=DummyModelBundle(),
        )

        self.assertGreater(frame["ai_score"].notna().sum(), 0)

    def test_load_price_data_batch_raises_when_ticker_is_missing(self) -> None:
        with patch("src.data_loader.yf.download", return_value=pd.DataFrame()):
            with self.assertRaisesRegex(ValueError, "Failed to load batch price data"):
                load_price_data_batch(["AAPL", "MSFT"], force_refresh=True)


if __name__ == "__main__":
    unittest.main()
