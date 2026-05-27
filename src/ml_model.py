from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, List, Dict, Tuple, Optional

import joblib
import pandas as pd
import numpy as np
from lightgbm import LGBMClassifier
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, brier_score_loss, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import TimeSeriesSplit

from src.features import FEATURE_COLUMNS, build_features
from src.market_regime import compute_daily_regime, get_current_regime

MODEL_PATH = Path("models/ai_score_model.joblib")
MODEL_METADATA_PATH = Path("models/ai_score_model_metadata.json")
CHALLENGER_DIR = Path("models/challengers")
CHAMPION_ARCHIVE_DIR = Path("models/champion_archive")


class BaseModel(ABC):
    @abstractmethod
    def predict_proba(
        self,
        df: pd.DataFrame,
        vix_df: pd.DataFrame | None = None,
        spy_df: pd.DataFrame | None = None,
        macro_df: pd.DataFrame | None = None,
    ) -> pd.Series:
        pass

    @abstractmethod
    def predict(
        self,
        df: pd.DataFrame,
        vix_df: pd.DataFrame | None = None,
        spy_df: pd.DataFrame | None = None,
        macro_df: pd.DataFrame | None = None,
    ) -> pd.Series:
        pass


class SoftVotingEnsemble:
    """LightGBM과 XGBoost 모델의 예측 확률을 평균하여 최종 결과를 도출한다."""
    def __init__(self, lgbm_model, xgb_model):
        self.lgbm_model = lgbm_model
        self.xgb_model = xgb_model

    def predict_proba(self, X):
        lgbm_proba = self.lgbm_model.predict_proba(X)[:, 1]
        xgb_proba = self.xgb_model.predict_proba(X)[:, 1]
        # Soft Voting: 두 모델의 확률 평균
        avg_proba = (lgbm_proba + xgb_proba) / 2.0
        # predict_proba 인터페이스 준수 ([prob_0, prob_1])
        return np.vstack([1.0 - avg_proba, avg_proba]).T

    def predict(self, X):
        proba = self.predict_proba(X)[:, 1]
        return (proba >= 0.5).astype(int)


class RegimeAwareModelWrapper(BaseModel):
    def __init__(
        self,
        models: Dict[str, any],
        feature_columns: List[str],
        prediction_horizon: int,
        target_return_threshold: float,
    ):
        self.models = models  # e.g., {"BULL": model_a, "BEAR": model_b, "NEUTRAL": model_c}
        self.feature_columns = feature_columns
        self.prediction_horizon = prediction_horizon
        self.target_return_threshold = target_return_threshold

    def _prepare_features(
        self,
        df: pd.DataFrame,
        vix_df: pd.DataFrame | None = None,
        spy_df: pd.DataFrame | None = None,
        macro_df: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        return build_features(
            df,
            prediction_horizon=self.prediction_horizon,
            target_return_threshold=self.target_return_threshold,
            vix_df=vix_df,
            spy_df=spy_df,
            macro_df=macro_df,
        )

    def _get_model_for_regime(self, spy_df, vix_df):
        regime = get_current_regime(spy_df, vix_df)
        # Fallback to NEUTRAL if specific regime model missing
        return self.models.get(regime, self.models.get("NEUTRAL"))

    def predict_proba(
        self,
        df: pd.DataFrame,
        vix_df: pd.DataFrame | None = None,
        spy_df: pd.DataFrame | None = None,
        macro_df: pd.DataFrame | None = None,
    ) -> pd.Series:
        feature_df = self._prepare_features(df, vix_df=vix_df, spy_df=spy_df, macro_df=macro_df)
        model = self._get_model_for_regime(spy_df, vix_df)
        
        available_cols = [c for c in self.feature_columns if c in feature_df.columns]
        X = feature_df[available_cols]
        
        # SoftVotingEnsemble 또는 일반 모델 호환성 유지
        if hasattr(model, "predict_proba"):
            proba = model.predict_proba(X)
            return pd.Series(proba[:, 1], index=feature_df.index)
        
        return pd.Series([0.5] * len(X), index=feature_df.index)

    def predict(
        self,
        df: pd.DataFrame,
        vix_df: pd.DataFrame | None = None,
        spy_df: pd.DataFrame | None = None,
        macro_df: pd.DataFrame | None = None,
    ) -> pd.Series:
        feature_df = self._prepare_features(df, vix_df=vix_df, spy_df=spy_df, macro_df=macro_df)
        model = self._get_model_for_regime(spy_df, vix_df)
        
        available_cols = [c for c in self.feature_columns if c in feature_df.columns]
        X = feature_df[available_cols]
        pred = model.predict(X)
        return pd.Series(pred, index=feature_df.index)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _summarize_metrics(metrics_df: pd.DataFrame) -> dict[str, Any]:
    if metrics_df is None or metrics_df.empty:
        return {"avg_roc_auc": 0.0, "regimes": {}}

    summary = {"avg_roc_auc": float(metrics_df["roc_auc"].mean()) if "roc_auc" in metrics_df.columns else 0.0, "regimes": {}}
    if "regime" in metrics_df.columns:
        for regime, regime_df in metrics_df.groupby("regime"):
            summary["regimes"][str(regime)] = {
                "avg_roc_auc": float(regime_df["roc_auc"].mean()) if "roc_auc" in regime_df.columns else 0.0,
                "folds": int(len(regime_df)),
            }
    return summary


def build_model_metadata(
    *,
    training_data: Dict[str, pd.DataFrame],
    trained_models: Dict[str, Any],
    metrics_df: pd.DataFrame,
    feature_columns: List[str],
    prediction_horizon: int,
    target_return_threshold: float,
) -> dict[str, Any]:
    date_bounds = []
    for df in training_data.values():
        if df is None or df.empty or "date" not in df.columns:
            continue
        series = pd.to_datetime(df["date"], errors="coerce").dropna()
        if not series.empty:
            date_bounds.append((series.min(), series.max()))

    training_start = min((start for start, _ in date_bounds), default=None)
    training_end = max((end for _, end in date_bounds), default=None)

    return {
        "saved_at": _utc_now_iso(),
        "training_window_start": training_start.strftime("%Y-%m-%d") if training_start is not None else None,
        "training_window_end": training_end.strftime("%Y-%m-%d") if training_end is not None else None,
        "ticker_count": int(len(training_data)),
        "feature_set_version": f"features_v{len(feature_columns)}",
        "feature_columns": list(feature_columns),
        "prediction_horizon": int(prediction_horizon),
        "target_return_threshold": float(target_return_threshold),
        "trained_regimes": sorted(trained_models.keys()),
        "oos_metrics": _summarize_metrics(metrics_df),
    }


def build_model_bundle(
    *,
    trained_models: Dict[str, Any],
    metrics_df: pd.DataFrame,
    training_data: Dict[str, pd.DataFrame],
    feature_columns: List[str],
    prediction_horizon: int,
    target_return_threshold: float,
) -> dict[str, Any]:
    return {
        "models": trained_models,
        "feature_columns": feature_columns,
        "prediction_horizon": prediction_horizon,
        "target_return_threshold": target_return_threshold,
        "metadata": build_model_metadata(
            training_data=training_data,
            trained_models=trained_models,
            metrics_df=metrics_df,
            feature_columns=feature_columns,
            prediction_horizon=prediction_horizon,
            target_return_threshold=target_return_threshold,
        ),
    }


def save_model_bundle(
    bundle: dict[str, Any],
    *,
    model_path: Path = MODEL_PATH,
    metadata_path: Path = MODEL_METADATA_PATH,
) -> tuple[Path, Path]:
    model_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, model_path)
    metadata = bundle.get("metadata", {})
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    return model_path, metadata_path


def load_model_metadata(metadata_path: Path = MODEL_METADATA_PATH) -> dict[str, Any] | None:
    if not metadata_path.exists():
        return None
    return json.loads(metadata_path.read_text(encoding="utf-8"))


def save_challenger_bundle(
    bundle: dict[str, Any],
    *,
    challenger_dir: Path = CHALLENGER_DIR,
) -> tuple[Path, Path]:
    challenger_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    model_path = challenger_dir / f"ai_score_model_{timestamp}.joblib"
    metadata_path = challenger_dir / f"ai_score_model_{timestamp}_metadata.json"
    return save_model_bundle(bundle, model_path=model_path, metadata_path=metadata_path)


def archive_current_champion(
    *,
    model_path: Path = MODEL_PATH,
    metadata_path: Path = MODEL_METADATA_PATH,
    archive_dir: Path = CHAMPION_ARCHIVE_DIR,
) -> tuple[Path, Path] | None:
    if not model_path.exists() or not metadata_path.exists():
        return None

    archive_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archived_model_path = archive_dir / f"ai_score_model_{timestamp}.joblib"
    archived_metadata_path = archive_dir / f"ai_score_model_{timestamp}_metadata.json"
    archived_model_path.write_bytes(model_path.read_bytes())
    archived_metadata_path.write_bytes(metadata_path.read_bytes())
    return archived_model_path, archived_metadata_path


def find_latest_archived_champion(
    archive_dir: Path = CHAMPION_ARCHIVE_DIR,
) -> tuple[Path, Path] | None:
    metadata_paths = sorted(archive_dir.glob("ai_score_model_*_metadata.json"))
    if not metadata_paths:
        return None

    latest_metadata_path = metadata_paths[-1]
    model_stem = latest_metadata_path.name.replace("_metadata.json", ".joblib")
    model_path = archive_dir / model_stem
    if not model_path.exists():
        return None
    return model_path, latest_metadata_path


def restore_archived_champion(
    archived_model_path: Path,
    archived_metadata_path: Path,
    *,
    model_path: Path = MODEL_PATH,
    metadata_path: Path = MODEL_METADATA_PATH,
) -> tuple[Path, Path]:
    model_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    model_path.write_bytes(archived_model_path.read_bytes())
    metadata_path.write_bytes(archived_metadata_path.read_bytes())
    return model_path, metadata_path


def build_promotion_report(
    challenger_metadata: dict[str, Any],
    champion_metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    challenger_auc = float(challenger_metadata.get("oos_metrics", {}).get("avg_roc_auc", 0.0))
    champion_auc = float(champion_metadata.get("oos_metrics", {}).get("avg_roc_auc", 0.0)) if champion_metadata else None
    promote = champion_metadata is None or challenger_auc > champion_auc
    return {
        "generated_at": _utc_now_iso(),
        "champion_exists": champion_metadata is not None,
        "champion_avg_roc_auc": champion_auc,
        "challenger_avg_roc_auc": challenger_auc,
        "decision": "PROMOTE" if promote else "RETAIN_CHAMPION",
        "reason": (
            "no existing champion metadata"
            if champion_metadata is None
            else f"challenger_avg_roc_auc={'{:.4f}'.format(challenger_auc)} vs champion_avg_roc_auc={'{:.4f}'.format(champion_auc)}"
        ),
    }


def train_ai_score_model(
    training_data: Dict[str, pd.DataFrame],
    prediction_horizon: int = 5,
    target_return_threshold: float = 0.0,
    vix_df: pd.DataFrame | None = None,
    spy_df: pd.DataFrame | None = None,
    macro_df: pd.DataFrame | None = None,
) -> Tuple[BaseModel, pd.DataFrame]:
    frames = []

    for ticker, df in training_data.items():
        try:
            feature_df = build_features(
                df,
                prediction_horizon=prediction_horizon,
                target_return_threshold=target_return_threshold,
                vix_df=vix_df,
                spy_df=spy_df,
                macro_df=macro_df,
            )
        except ValueError:
            continue
        feature_df["ticker"] = ticker
        frames.append(feature_df)

    dataset = pd.concat(frames, ignore_index=True)
    dataset = dataset.sort_values("date").reset_index(drop=True)

    # 시장 레짐 계산 및 병합
    if spy_df is not None and vix_df is not None:
        regime_series = compute_daily_regime(spy_df, vix_df)
        dataset = dataset.merge(
            regime_series.rename("regime"), left_on="date", right_index=True, how="left"
        )
        dataset["regime"] = dataset["regime"].fillna("NEUTRAL")
    else:
        dataset["regime"] = "NEUTRAL"

    regimes = ["BULL", "BEAR", "NEUTRAL"]
    trained_models = {}
    all_metrics = []
    calibration_rows = []

    for regime in regimes:
        regime_data = dataset[dataset["regime"] == regime]
        if len(regime_data) < 100:  # 최소 데이터 요구량
            print(f"  WARNING: insufficient data for {regime} regime (rows={len(regime_data)}), skipping...")
            continue
            
        print(f"  Training {regime} ensemble model (LightGBM + XGBoost, rows={len(regime_data)})...")
        X_regime = regime_data[FEATURE_COLUMNS]
        y_regime = regime_data["target"]

        lgbm = LGBMClassifier(
            n_estimators=500,
            learning_rate=0.05,
            max_depth=6,
            num_leaves=31,
            min_child_samples=20,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            class_weight="balanced" if regime != "BEAR" else None,
            n_jobs=-1,
            verbose=-1,
        )
        
        xgb = XGBClassifier(
            n_estimators=500,
            learning_rate=0.05,
            max_depth=6,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1,
            verbosity=0,
        )

        # 교차 검증 (단순화: 앙상블 효과 확인)
        tscv = TimeSeriesSplit(n_splits=3)
        for fold, (train_idx, test_idx) in enumerate(tscv.split(X_regime), start=1):
            X_train, X_test = X_regime.iloc[train_idx], X_regime.iloc[test_idx]
            y_train, y_test = y_regime.iloc[train_idx], y_regime.iloc[test_idx]
            
            # 검증을 위한 앙상블 확률
            f_lgbm = LGBMClassifier(n_estimators=100, random_state=42, verbose=-1)
            f_xgb = XGBClassifier(n_estimators=100, random_state=42, n_jobs=-1, verbosity=0)
            
            f_lgbm.fit(X_train, y_train)
            f_xgb.fit(X_train, y_train)
            
            proba = (f_lgbm.predict_proba(X_test)[:, 1] + f_xgb.predict_proba(X_test)[:, 1]) / 2.0
            
            try:
                auc = roc_auc_score(y_test, proba)
            except ValueError:
                auc = 0.5
            brier = brier_score_loss(y_test, proba)
            
            all_metrics.append({
                "regime": regime,
                "fold": fold,
                "roc_auc": auc,
                "brier_score": brier,
                "test_size": len(test_idx)
            })
            calibration_rows.extend(
                {
                    "regime": regime,
                    "fold": fold,
                    "y_true": int(y_true),
                    "y_prob": float(y_prob),
                }
                for y_true, y_prob in zip(y_test.tolist(), proba.tolist())
            )

        lgbm.fit(X_regime, y_regime)
        xgb.fit(X_regime, y_regime)
        trained_models[regime] = SoftVotingEnsemble(lgbm, xgb)

    # 만약 특정 레짐 모델이 하나도 없으면 (에러 방지)
    if not trained_models:
        raise ValueError("No models could be trained for any regime.")

    metrics_df = pd.DataFrame(all_metrics)
    metrics_df.attrs["calibration_rows"] = calibration_rows
    wrapper = RegimeAwareModelWrapper(trained_models, FEATURE_COLUMNS, prediction_horizon, target_return_threshold)
    return wrapper, metrics_df


def load_ai_score_model() -> BaseModel:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model not found: {MODEL_PATH}. Run python -m src.train_ai_model first."
        )

    bundle = joblib.load(MODEL_PATH)
    
    # 레거시 단일 모델 지원 (하위 호환성)
    if "model" in bundle:
        return RegimeAwareModelWrapper(
            {"NEUTRAL": bundle["model"]},
            bundle["feature_columns"],
            bundle["prediction_horizon"],
            bundle["target_return_threshold"],
        )
        
    return RegimeAwareModelWrapper(
        bundle["models"],
        bundle["feature_columns"],
        bundle["prediction_horizon"],
        bundle["target_return_threshold"],
    )


def predict_ai_score_from_bundle(
    df: pd.DataFrame,
    model: BaseModel,
    vix_df: pd.DataFrame | None = None,
    spy_df: pd.DataFrame | None = None,
    macro_df: pd.DataFrame | None = None,
) -> float:
    proba_series = model.predict_proba(df, vix_df=vix_df, spy_df=spy_df, macro_df=macro_df)
    return float(proba_series.iloc[-1])


def predict_ai_score(df: pd.DataFrame) -> float:
    model = load_ai_score_model()
    return predict_ai_score_from_bundle(df, model)
