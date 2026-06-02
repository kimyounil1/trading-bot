"""Paper-only cross-sectional rank AI buy/add gate."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from src.features import FEATURE_COLUMNS, build_features


@dataclass(frozen=True)
class RankAIGateScore:
    ticker: str
    score: float
    percentile: float
    allowed: bool
    reason: str


@dataclass(frozen=True)
class RankAIGateDecision:
    risk_allowed: bool
    risk_reason: str
    target_amount: float
    score: float | None = None
    percentile: float | None = None


def _rank_gate_enabled(settings: Any) -> bool:
    return bool(getattr(settings, "rank_ai_buy_gate_enabled", False))


def rank_ai_gate_effective_cutoff(settings: Any, config: dict | None = None) -> float:
    """Match rank-label experiment: top bucket (1 - top_bucket_pct) and min score quantile."""
    cfg = config or {}
    score_cutoff = float(
        getattr(
            settings,
            "rank_ai_buy_gate_min_score_quantile",
            cfg.get("min_score_quantile", 0.85),
        )
    )
    top_bucket_pct = float(
        getattr(
            settings,
            "rank_ai_buy_gate_top_bucket_pct",
            cfg.get("top_bucket_pct", 0.15),
        )
    )
    bucket_cutoff = 1.0 - top_bucket_pct
    return max(score_cutoff, bucket_cutoff)


def _model_path(settings: Any) -> Path:
    return Path(
        str(
            getattr(
                settings,
                "rank_ai_buy_gate_model_path",
                "logs/ml/rank_label_experiment_h20_top15_q85/rank_models.joblib",
            )
        )
    )


def _build_latest_inference_features(
    df: pd.DataFrame,
    *,
    prediction_horizon: int,
    vix_df: pd.DataFrame | None,
    spy_df: pd.DataFrame | None,
    macro_df: pd.DataFrame | None,
) -> pd.DataFrame:
    """Build latest feature row without needing real future returns.

    ``build_features`` is training-oriented and drops the last horizon rows
    because labels are unknown. For inference, append synthetic future rows with
    unchanged prices so latest historical rows survive the label drop. The target
    is ignored; only FEATURE_COLUMNS are used for prediction.
    """

    if df.empty:
        raise ValueError("empty price frame")
    working = df.copy().sort_values("date").reset_index(drop=True)
    last = working.iloc[-1].copy()
    last_date = pd.to_datetime(last["date"])
    synthetic_rows = []
    for offset in range(1, prediction_horizon + 1):
        row = last.copy()
        row["date"] = last_date + pd.Timedelta(days=offset)
        synthetic_rows.append(row)
    if synthetic_rows:
        working = pd.concat([working, pd.DataFrame(synthetic_rows)], ignore_index=True)

    features = build_features(
        working,
        prediction_horizon=prediction_horizon,
        target_return_threshold=0.0,
        vix_df=vix_df,
        spy_df=spy_df,
        macro_df=macro_df,
    )
    original_last_date = pd.to_datetime(df["date"]).max()
    latest_features = features[pd.to_datetime(features["date"]) <= original_last_date]
    if latest_features.empty:
        raise ValueError("no current inference feature row")
    return latest_features.tail(1)


def build_rank_ai_gate_scores(
    ticker_data: dict[str, pd.DataFrame],
    settings: Any,
    *,
    vix_df: pd.DataFrame | None = None,
    spy_df: pd.DataFrame | None = None,
    macro_df: pd.DataFrame | None = None,
) -> dict[str, RankAIGateScore]:
    if not _rank_gate_enabled(settings):
        return {}

    path = _model_path(settings)
    if not path.is_file():
        if bool(getattr(settings, "rank_ai_buy_gate_fail_closed", True)):
            raise FileNotFoundError(f"rank AI gate model not found: {path}")
        return {}

    bundle = joblib.load(path)
    classifier = bundle["classifier"]
    regressor = bundle["regressor"]
    config = bundle.get("config") or {}
    horizon = int(
        getattr(
            settings,
            "rank_ai_buy_gate_prediction_horizon",
            config.get("prediction_horizon", 20),
        )
    )
    raw_scores: list[tuple[str, float]] = []
    for ticker, frame in ticker_data.items():
        symbol = str(ticker).upper()
        if symbol.startswith("^") or symbol == "SPY":
            continue
        try:
            feature_row = _build_latest_inference_features(
                frame,
                prediction_horizon=horizon,
                vix_df=vix_df,
                spy_df=spy_df,
                macro_df=macro_df,
            )
            x_latest = feature_row[FEATURE_COLUMNS]
            clf_score = float(classifier.predict_proba(x_latest)[:, 1][0])
            reg_score = float(regressor.predict(x_latest)[0])
            score = (clf_score + min(max(reg_score, 0.0), 1.0)) / 2.0
        except Exception:
            continue
        raw_scores.append((symbol, score))

    if not raw_scores:
        if bool(getattr(settings, "rank_ai_buy_gate_fail_closed", True)):
            raise ValueError("rank AI gate produced no scores")
        return {}

    score_df = pd.DataFrame(raw_scores, columns=["ticker", "score"])
    score_df["percentile"] = score_df["score"].rank(pct=True, method="average")
    cutoff = rank_ai_gate_effective_cutoff(settings, config)

    scores: dict[str, RankAIGateScore] = {}
    for _, row in score_df.iterrows():
        ticker = str(row["ticker"])
        percentile = float(row["percentile"])
        score = float(row["score"])
        allowed = percentile >= cutoff
        if allowed:
            reason = f"rank ai gate passed (pct={percentile:.3f}, cutoff={cutoff:.3f})"
        else:
            reason = f"rank ai gate blocked (pct={percentile:.3f}, cutoff={cutoff:.3f})"
        scores[ticker] = RankAIGateScore(
            ticker=ticker,
            score=score,
            percentile=percentile,
            allowed=allowed,
            reason=reason,
        )
    return scores


def apply_rank_ai_buy_gate(
    *,
    ticker: str,
    settings: Any,
    risk_allowed: bool,
    risk_reason: str,
    target_amount: float,
    scores: dict[str, RankAIGateScore],
) -> RankAIGateDecision:
    if not _rank_gate_enabled(settings) or not risk_allowed:
        return RankAIGateDecision(risk_allowed, risk_reason, target_amount)

    symbol = str(ticker).upper()
    score = scores.get(symbol)
    if score is None:
        if bool(getattr(settings, "rank_ai_buy_gate_fail_closed", True)):
            return RankAIGateDecision(
                False,
                f"rank ai gate missing score for {symbol}",
                0.0,
            )
        return RankAIGateDecision(risk_allowed, risk_reason, target_amount)

    if not score.allowed:
        return RankAIGateDecision(
            False,
            score.reason,
            0.0,
            score=score.score,
            percentile=score.percentile,
        )

    pass_reason = score.reason
    if risk_reason and risk_reason != pass_reason:
        pass_reason = f"{risk_reason} | {score.reason}"
    return RankAIGateDecision(
        True,
        pass_reason,
        target_amount,
        score=score.score,
        percentile=score.percentile,
    )
