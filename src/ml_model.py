from abc import ABC, abstractmethod
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import TimeSeriesSplit

from src.features import FEATURE_COLUMNS, build_features

MODEL_PATH = Path("models/ai_score_model.joblib")

class BaseModel(ABC):
    """모든 모델의 공통 인터페이스"""
    @abstractmethod
    def predict_proba(self, df: pd.DataFrame) -> pd.Series:
        pass

    @abstractmethod
    def predict(self, df: pd.DataFrame) -> pd.Series:
        pass

class SklearnModelWrapper(BaseModel):
    """현재 Sklearn 모델을 위한 Wrapper"""
    def __init__(self, model, feature_columns: list[str], prediction_horizon: int, target_return_threshold: float):
        self.model = model
        self.feature_columns = feature_columns
        self.prediction_horizon = prediction_horizon
        self.target_return_threshold = target_return_threshold

    def _prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """입력 DataFrame으로부터 피처를 생성합니다."""
        return build_features(
            df, 
            prediction_horizon=self.prediction_horizon, 
            target_return_threshold=self.target_return_threshold
        )

    def predict_proba(self, df: pd.DataFrame) -> pd.Series:
        feature_df = self._prepare_features(df)
        X = feature_df[self.feature_columns]
        proba = self.model.predict_proba(X)
        return pd.Series(proba[:, 1], index=feature_df.index)

    def predict(self, df: pd.DataFrame) -> pd.Series:
        feature_df = self._prepare_features(df)
        X = feature_df[self.feature_columns]
        pred = self.model.predict(X)
        return pd.Series(pred, index=feature_df.index)

def train_ai_score_model(
    training_data: dict[str, pd.DataFrame],
    prediction_horizon: int = 5,
    target_return_threshold: float = 0.0,
) -> tuple[BaseModel, pd.DataFrame]:
    frames = []

    for ticker, df in training_data.items():
        feature_df = build_features(
            df,
            prediction_horizon=prediction_horizon,
            target_return_threshold=target_return_threshold,
        )
        feature_df["ticker"] = ticker
        frames.append(feature_df)

    dataset = pd.concat(frames, ignore_index=True)
    dataset = dataset.sort_values("date").reset_index(drop=True)

    X = dataset[FEATURE_COLUMNS]
    y = dataset["target"]

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=5,
        min_samples_leaf=20,
        random_state=42,
        class_weight="balanced",
        n_jobs=-1,
    )

    tscv = TimeSeriesSplit(n_splits=5)
    rows = []

    for fold, (train_idx, test_idx) in enumerate(tscv.split(X), start=1):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

        fold_model = RandomForestClassifier(
            n_estimators=300,
            max_depth=5,
            min_samples_leaf=20,
            random_state=42,
            class_weight="balanced",
            n_jobs=-1,
        )

        fold_model.fit(X_train, y_train)
        proba = fold_model.predict_proba(X_test)[:, 1]
        pred = (proba >= 0.5).astype(int)

        try:
            auc = roc_auc_score(y_test, proba)
        except ValueError:
            auc = float("nan")

        rows.append(
            {
                "fold": fold,
                "accuracy": accuracy_score(y_test, pred),
                "precision": precision_score(y_test, pred, zero_division=0),
                "recall": recall_score(y_test, pred, zero_division=0),
                "roc_auc": auc,
                "test_positive_rate": float(y_test.mean()),
                "prediction_positive_rate": float(pred.mean()),
                "train_size": len(train_idx),
                "test_size": len(test_idx),
            }
        )

    model.fit(X, y)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": model,
            "feature_columns": FEATURE_COLUMNS,
            "prediction_horizon": prediction_horizon,
            "target_return_threshold": target_return_threshold,
        },
        MODEL_PATH,
    )

    metrics_df = pd.DataFrame(rows)
    wrapper = SklearnModelWrapper(model, FEATURE_COLUMNS, prediction_horizon, target_return_threshold)
    return wrapper, metrics_df


def load_ai_score_model() -> BaseModel:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model not found: {MODEL_PATH}. Run python -m src.train_ai_model first."
        )
    
    bundle = joblib.load(MODEL_PATH)
    return SklearnModelWrapper(
        bundle["model"], 
        bundle["feature_columns"], 
        bundle["prediction_horizon"], 
        bundle["target_return_threshold"]
    )


def predict_ai_score_from_bundle(df: pd.DataFrame, model: BaseModel) -> float:
    """BaseModel 인터페이스를 사용하는 함수입니다."""
    proba_series = model.predict_proba(df)
    return float(proba_series.iloc[-1])


def predict_ai_score(df: pd.DataFrame) -> float:
    model = load_ai_score_model()
    return predict_ai_score_from_bundle(df, model)
