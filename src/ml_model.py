from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import TimeSeriesSplit

from src.features import FEATURE_COLUMNS, build_features


MODEL_PATH = Path("models/ai_score_model.joblib")


def train_ai_score_model(
    training_data: dict[str, pd.DataFrame],
    prediction_horizon: int = 5,
    target_return_threshold: float = 0.0,
) -> tuple[RandomForestClassifier, pd.DataFrame]:
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
    return model, metrics_df


def load_ai_score_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model not found: {MODEL_PATH}. Run python -m src.train_ai_model first."
        )

    return joblib.load(MODEL_PATH)


def predict_ai_score(df: pd.DataFrame) -> float:
    bundle = load_ai_score_model()
    model = bundle["model"]
    feature_columns = bundle["feature_columns"]
    prediction_horizon = bundle["prediction_horizon"]
    target_return_threshold = bundle["target_return_threshold"]

    feature_df = build_features(
        df,
        prediction_horizon=prediction_horizon,
        target_return_threshold=target_return_threshold,
    )

    latest = feature_df.iloc[-1]
    X_latest = latest[feature_columns].to_frame().T

    return float(model.predict_proba(X_latest)[0, 1])
