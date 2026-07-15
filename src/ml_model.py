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

from src.features import FEATURE_COLUMNS, build_features, build_inference_features
from src.market_regime import compute_daily_regime, get_current_regime
from src.ai_score_calibration import calibrate_ai_score
from src.settings import load_settings

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
        return build_inference_features(
            df,
            prediction_horizon=self.prediction_horizon,
            target_return_threshold=self.target_return_threshold,
            vix_df=vix_df,
            spy_df=spy_df,
            macro_df=macro_df,
        )

    def _feature_regimes(
        self,
        feature_df: pd.DataFrame,
        spy_df: pd.DataFrame | None,
        vix_df: pd.DataFrame | None,
    ) -> pd.Series:
        """Return the market regime known on each feature row's date."""
        if spy_df is None or vix_df is None:
            return pd.Series("NEUTRAL", index=feature_df.index, dtype="object")
        regimes = compute_daily_regime(spy_df, vix_df)
        if regimes.empty:
            return pd.Series("NEUTRAL", index=feature_df.index, dtype="object")
        regimes = regimes.copy()
        regimes.index = pd.to_datetime(regimes.index, errors="coerce")
        regimes = regimes[~regimes.index.isna()].sort_index()
        dates = pd.to_datetime(feature_df["date"], errors="coerce")
        aligned = regimes.reindex(pd.DatetimeIndex(dates), method="ffill")
        return pd.Series(aligned.fillna("NEUTRAL").to_numpy(), index=feature_df.index)

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
        available_cols = [c for c in self.feature_columns if c in feature_df.columns]
        X = feature_df[available_cols]
        regimes = self._feature_regimes(feature_df, spy_df, vix_df)
        output = pd.Series(0.5, index=feature_df.index, dtype=float)
        for regime, row_index in regimes.groupby(regimes).groups.items():
            model = self.models.get(str(regime), self.models.get("NEUTRAL"))
            if model is None or not hasattr(model, "predict_proba"):
                continue
            proba = model.predict_proba(X.loc[row_index])
            output.loc[row_index] = proba[:, 1]
        return output

    def predict(
        self,
        df: pd.DataFrame,
        vix_df: pd.DataFrame | None = None,
        spy_df: pd.DataFrame | None = None,
        macro_df: pd.DataFrame | None = None,
    ) -> pd.Series:
        feature_df = self._prepare_features(df, vix_df=vix_df, spy_df=spy_df, macro_df=macro_df)
        available_cols = [c for c in self.feature_columns if c in feature_df.columns]
        X = feature_df[available_cols]
        regimes = self._feature_regimes(feature_df, spy_df, vix_df)
        output = pd.Series(0, index=feature_df.index, dtype=int)
        for regime, row_index in regimes.groupby(regimes).groups.items():
            model = self.models.get(str(regime), self.models.get("NEUTRAL"))
            if model is None:
                continue
            output.loc[row_index] = model.predict(X.loc[row_index])
        return output


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


def bundle_to_model_wrapper(bundle: dict[str, Any]) -> RegimeAwareModelWrapper:
    return RegimeAwareModelWrapper(
        bundle["models"],
        bundle["feature_columns"],
        bundle["prediction_horizon"],
        bundle["target_return_threshold"],
    )


def _portfolio_oos_rank_key(snapshot: dict[str, Any]) -> tuple[float, float, float]:
    return (
        float(snapshot["sharpe_ratio"]),
        float(snapshot["total_return"]),
        -abs(float(snapshot["max_drawdown"])),
    )


def portfolio_oos_beats_champion(
    challenger: dict[str, Any],
    champion: dict[str, Any],
) -> bool:
    """True when challenger ranks higher on Sharpe, then return, then drawdown."""
    return _portfolio_oos_rank_key(challenger) > _portfolio_oos_rank_key(champion)


def build_promotion_report(
    challenger_metadata: dict[str, Any],
    champion_metadata: dict[str, Any] | None,
    *,
    challenger_portfolio: dict[str, Any] | None = None,
    champion_portfolio: dict[str, Any] | None = None,
    portfolio_thresholds: Any | None = None,
    require_portfolio_oos: bool = True,
    fold_stability_report: dict[str, Any] | None = None,
    calibration_report: dict[str, Any] | None = None,
    require_ml_quality: bool = True,
    ml_quality_criteria: Any | None = None,
) -> dict[str, Any]:
    from src.ml_quality_report import evaluate_ml_quality_promotion_gates
    from src.portfolio_backtest_validation import (
        PortfolioBacktestThresholds,
        check_portfolio_summary_thresholds,
    )

    thresholds = portfolio_thresholds or PortfolioBacktestThresholds()
    challenger_auc = float(challenger_metadata.get("oos_metrics", {}).get("avg_roc_auc", 0.0))
    champion_auc = (
        float(champion_metadata.get("oos_metrics", {}).get("avg_roc_auc", 0.0))
        if champion_metadata
        else None
    )
    auc_ok = champion_metadata is None or challenger_auc > champion_auc

    ml_quality_eval = evaluate_ml_quality_promotion_gates(
        challenger_metadata,
        fold_stability_report,
        calibration_report,
        criteria=ml_quality_criteria,
    )
    ml_quality_ok = ml_quality_eval["passed"] if require_ml_quality else True

    portfolio_gate = None
    portfolio_gate_ok = True
    portfolio_vs_ok = True

    if require_portfolio_oos:
        if challenger_portfolio is None:
            portfolio_gate_ok = False
            portfolio_vs_ok = False
        else:
            portfolio_gate = check_portfolio_summary_thresholds(
                challenger_portfolio, thresholds
            )
            portfolio_gate_ok = portfolio_gate.passed

            if champion_portfolio is None and champion_metadata is not None:
                stored = champion_metadata.get("portfolio_oos")
                if isinstance(stored, dict):
                    champion_portfolio = stored

            if champion_portfolio is not None:
                portfolio_vs_ok = portfolio_oos_beats_champion(
                    challenger_portfolio, champion_portfolio
                )

    promote = auc_ok and ml_quality_ok and portfolio_gate_ok and portfolio_vs_ok

    reasons: list[str] = []
    if champion_metadata is None:
        reasons.append("no existing champion metadata")
    elif not auc_ok:
        reasons.append(
            f"challenger_avg_roc_auc={challenger_auc:.4f} vs champion_avg_roc_auc={champion_auc:.4f}"
        )
    if require_ml_quality and not ml_quality_ok:
        reasons.append("training metrics gates failed: " + "; ".join(ml_quality_eval["failures"]))
    if require_portfolio_oos and challenger_portfolio is None:
        reasons.append("missing challenger portfolio OOS evaluation")
    elif require_portfolio_oos and portfolio_gate is not None and not portfolio_gate_ok:
        reasons.append("portfolio gates failed: " + "; ".join(portfolio_gate.failures))
    elif (
        require_portfolio_oos
        and champion_portfolio is not None
        and challenger_portfolio is not None
        and not portfolio_vs_ok
    ):
        c, h = challenger_portfolio, champion_portfolio
        reasons.append(
            "portfolio OOS did not beat champion "
            f"(sharpe {float(c['sharpe_ratio']):.4f} vs {float(h['sharpe_ratio']):.4f}, "
            f"return {float(c['total_return']):.4f} vs {float(h['total_return']):.4f})"
        )

    if promote:
        reason = (
            "no existing champion; challenger passes training metrics and portfolio OOS gates"
            if champion_metadata is None
            else "challenger passes AUC, training metrics, and portfolio OOS criteria"
        )
    else:
        reason = "; ".join(reasons) if reasons else "challenger retained"

    report: dict[str, Any] = {
        "generated_at": _utc_now_iso(),
        "champion_exists": champion_metadata is not None,
        "champion_avg_roc_auc": champion_auc,
        "challenger_avg_roc_auc": challenger_auc,
        "auc_gate_passed": auc_ok,
        "ml_quality_gate_passed": ml_quality_ok,
        "ml_quality_gate_failures": ml_quality_eval.get("failures", []),
        "portfolio_gate_passed": portfolio_gate_ok,
        "portfolio_vs_champion_passed": portfolio_vs_ok,
        "decision": "PROMOTE" if promote else "RETAIN_CHAMPION",
        "reason": reason,
    }
    if challenger_portfolio is not None:
        report["challenger_portfolio_oos"] = challenger_portfolio
    if champion_portfolio is not None:
        report["champion_portfolio_oos"] = champion_portfolio
    if portfolio_gate is not None:
        report["portfolio_gate_failures"] = portfolio_gate.failures
        report["portfolio_gate_warnings"] = portfolio_gate.warnings
    return report


def _build_regime_feature_dataset(
    training_data: Dict[str, pd.DataFrame],
    *,
    prediction_horizon: int,
    target_return_threshold: float,
    vix_df: pd.DataFrame | None,
    spy_df: pd.DataFrame | None,
    macro_df: pd.DataFrame | None,
) -> pd.DataFrame:
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

    if not frames:
        return pd.DataFrame()

    dataset = pd.concat(frames, ignore_index=True).sort_values("date").reset_index(drop=True)
    if spy_df is not None and vix_df is not None:
        regime_series = compute_daily_regime(spy_df, vix_df)
        dataset = dataset.merge(
            regime_series.rename("regime"), left_on="date", right_index=True, how="left"
        )
        dataset["regime"] = dataset["regime"].fillna("NEUTRAL")
    else:
        dataset["regime"] = "NEUTRAL"
    return dataset


def _collect_regime_cv_metrics(
    regime: str,
    regime_data: pd.DataFrame,
    *,
    feature_columns: list[str] | None = None,
    lgbm_params: dict[str, Any] | None = None,
    xgb_params: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Time-series CV metrics and per-row calibration data for one regime."""
    metrics: list[dict[str, Any]] = []
    calibration_rows: list[dict[str, Any]] = []
    cols = list(FEATURE_COLUMNS) if feature_columns is None else list(feature_columns)
    available_cols = [c for c in cols if c in regime_data.columns]
    if not available_cols:
        return metrics, calibration_rows

    X_regime = regime_data[available_cols]
    y_regime = regime_data["target"]
    tscv = TimeSeriesSplit(n_splits=3)
    lgbm_defaults: dict[str, Any] = {
        "n_estimators": 100,
        "random_state": 42,
        "verbose": -1,
    }
    xgb_defaults: dict[str, Any] = {
        "n_estimators": 100,
        "random_state": 42,
        "n_jobs": -1,
        "verbosity": 0,
    }
    if lgbm_params:
        lgbm_defaults.update(lgbm_params)
    if xgb_params:
        xgb_defaults.update(xgb_params)

    for fold, (train_idx, test_idx) in enumerate(tscv.split(X_regime), start=1):
        X_train, X_test = X_regime.iloc[train_idx], X_regime.iloc[test_idx]
        y_train, y_test = y_regime.iloc[train_idx], y_regime.iloc[test_idx]

        f_lgbm = LGBMClassifier(**lgbm_defaults)
        f_xgb = XGBClassifier(**xgb_defaults)
        f_lgbm.fit(X_train, y_train)
        f_xgb.fit(X_train, y_train)
        proba = (f_lgbm.predict_proba(X_test)[:, 1] + f_xgb.predict_proba(X_test)[:, 1]) / 2.0

        try:
            auc = float(roc_auc_score(y_test, proba))
        except ValueError:
            auc = 0.5
        brier = float(brier_score_loss(y_test, proba))
        metrics.append(
            {
                "regime": regime,
                "fold": fold,
                "roc_auc": auc,
                "brier_score": brier,
                "test_size": int(len(test_idx)),
            }
        )
        calibration_rows.extend(
            {
                "regime": regime,
                "fold": fold,
                "y_true": int(y_true),
                "y_prob": float(y_prob),
            }
            for y_true, y_prob in zip(y_test.tolist(), proba.tolist())
        )
    return metrics, calibration_rows


def collect_regime_cv_metrics_df(
    training_data: Dict[str, pd.DataFrame],
    prediction_horizon: int = 5,
    target_return_threshold: float = 0.0,
    vix_df: pd.DataFrame | None = None,
    spy_df: pd.DataFrame | None = None,
    macro_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """CV fold metrics + calibration rows without training champion models."""
    dataset = _build_regime_feature_dataset(
        training_data,
        prediction_horizon=prediction_horizon,
        target_return_threshold=target_return_threshold,
        vix_df=vix_df,
        spy_df=spy_df,
        macro_df=macro_df,
    )
    if dataset.empty:
        return pd.DataFrame()

    all_metrics: list[dict[str, Any]] = []
    calibration_rows: list[dict[str, Any]] = []
    for regime in ("BULL", "BEAR", "NEUTRAL"):
        regime_data = dataset[dataset["regime"] == regime]
        if len(regime_data) < 100:
            print(
                f"  WARNING: insufficient data for {regime} regime "
                f"(rows={len(regime_data)}), skipping CV..."
            )
            continue
        print(f"  Collecting CV metrics for {regime} (rows={len(regime_data)})...")
        metrics, rows = _collect_regime_cv_metrics(regime, regime_data)
        all_metrics.extend(metrics)
        calibration_rows.extend(rows)

    metrics_df = pd.DataFrame(all_metrics)
    metrics_df.attrs["calibration_rows"] = calibration_rows
    return metrics_df


def train_ai_score_model(
    training_data: Dict[str, pd.DataFrame],
    prediction_horizon: int = 5,
    target_return_threshold: float = 0.0,
    vix_df: pd.DataFrame | None = None,
    spy_df: pd.DataFrame | None = None,
    macro_df: pd.DataFrame | None = None,
) -> Tuple[BaseModel, pd.DataFrame]:
    dataset = _build_regime_feature_dataset(
        training_data,
        prediction_horizon=prediction_horizon,
        target_return_threshold=target_return_threshold,
        vix_df=vix_df,
        spy_df=spy_df,
        macro_df=macro_df,
    )
    if dataset.empty:
        raise ValueError("No training features could be built from input tickers.")

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

        fold_metrics, fold_rows = _collect_regime_cv_metrics(regime, regime_data)
        all_metrics.extend(fold_metrics)
        calibration_rows.extend(fold_rows)

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
    raw_score = float(proba_series.iloc[-1])
    try:
        settings = load_settings()
        if not bool(getattr(settings, "ai_score_calibration_enabled", False)):
            return raw_score
        regime = "NEUTRAL"
        if spy_df is not None and vix_df is not None:
            try:
                regime = str(get_current_regime(spy_df, vix_df))
            except Exception:
                regime = "NEUTRAL"
        calibrated = calibrate_ai_score(
            raw_score,
            regime=regime,
            bins_path=str(
                getattr(
                    settings,
                    "ai_score_calibration_bins_path",
                    "logs/ml/model_calibration_bins.csv",
                )
            ),
        )
        return float(calibrated) if calibrated is not None else raw_score
    except Exception:
        # Fail-open: score calibration is an overlay, never a hard dependency.
        return raw_score


def predict_ai_score(df: pd.DataFrame) -> float:
    model = load_ai_score_model()
    return predict_ai_score_from_bundle(df, model)
