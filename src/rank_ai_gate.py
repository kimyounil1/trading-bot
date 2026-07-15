"""Paper-only cross-sectional rank AI buy/add gate."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from src.features import FEATURE_COLUMNS, MAX_FEATURE_LOOKBACK, build_inference_features


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


def rank_ai_primary_selector_enabled(settings: Any) -> bool:
    """Return whether Rank AI replaces conventional entry direction filters."""
    return bool(
        _rank_gate_enabled(settings)
        and getattr(settings, "rank_ai_primary_selector_enabled", False)
    )


def rank_ai_entry_signal(signal: str, settings: Any) -> str:
    """Use BUY for risk sizing when the fail-closed Rank gate owns selection."""
    if rank_ai_primary_selector_enabled(settings):
        return "BUY"
    return str(signal).upper()


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
    features = build_inference_features(
        df,
        prediction_horizon=prediction_horizon,
        target_return_threshold=0.0,
        vix_df=vix_df,
        spy_df=spy_df,
        macro_df=macro_df,
    )
    return features.tail(1)


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


def build_rank_ai_gate_score_history(
    ticker_data: dict[str, pd.DataFrame],
    settings: Any,
    *,
    vix_df: pd.DataFrame | None = None,
    spy_df: pd.DataFrame | None = None,
    macro_df: pd.DataFrame | None = None,
    historical_universe_by_date: dict[Any, list[str]] | None = None,
    base_universe: set[str] | list[str] | None = None,
) -> dict[pd.Timestamp, dict[str, RankAIGateScore]]:
    """Precompute causal daily rank scores for point-in-time backtests.

    Every feature row uses only data available through that row's date. Ranking
    is then performed cross-sectionally within each date, matching repeated
    calls to :func:`build_rank_ai_gate_scores` without reloading the model and
    rebuilding the full feature history on every simulated trading day.
    """
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
    minimum_observations = MAX_FEATURE_LOOKBACK + horizon
    records: list[pd.DataFrame] = []

    for ticker, frame in ticker_data.items():
        symbol = str(ticker).upper()
        if symbol.startswith("^") or symbol == "SPY" or frame is None or frame.empty:
            continue
        try:
            ordered = frame.copy()
            ordered["date"] = pd.to_datetime(ordered["date"])
            ordered = ordered.sort_values("date").drop_duplicates("date", keep="last")
            if len(ordered) < minimum_observations:
                continue
            feature_frame = build_inference_features(
                ordered,
                prediction_horizon=horizon,
                target_return_threshold=0.0,
                vix_df=vix_df,
                spy_df=spy_df,
                macro_df=macro_df,
            )
            feature_frame = feature_frame[
                pd.to_datetime(feature_frame["date"])
                >= pd.Timestamp(ordered.iloc[minimum_observations - 1]["date"])
            ].copy()
            if feature_frame.empty:
                continue
            x = feature_frame[FEATURE_COLUMNS]
            clf_score = classifier.predict_proba(x)[:, 1]
            reg_score = pd.Series(regressor.predict(x), index=feature_frame.index).clip(0.0, 1.0)
            scored = feature_frame[["date"]].copy()
            scored["ticker"] = symbol
            scored["score"] = (clf_score + reg_score.to_numpy()) / 2.0
            records.append(scored)
        except Exception:
            continue

    if not records:
        if bool(getattr(settings, "rank_ai_buy_gate_fail_closed", True)):
            raise ValueError("rank AI gate produced no historical scores")
        return {}

    score_df = pd.concat(records, ignore_index=True)
    score_df["date"] = pd.to_datetime(score_df["date"])
    if historical_universe_by_date:
        snapshots = {
            pd.Timestamp(date).normalize(): {
                str(ticker).strip().upper()
                for ticker in tickers
                if str(ticker).strip()
            }
            for date, tickers in historical_universe_by_date.items()
        }
        fallback = (
            {str(ticker).strip().upper() for ticker in base_universe}
            if base_universe is not None
            else set(ticker_data)
        )
        snapshot_dates = sorted(snapshots)

        def active_symbols(current_date: pd.Timestamp) -> set[str]:
            eligible = [date for date in snapshot_dates if date <= current_date.normalize()]
            return snapshots[max(eligible)] if eligible else fallback

        score_df = pd.concat(
            [
                rows[rows["ticker"].isin(active_symbols(pd.Timestamp(current_date)))]
                for current_date, rows in score_df.groupby("date", sort=False)
            ],
            ignore_index=True,
        )
        if score_df.empty:
            raise ValueError("rank AI history is empty after point-in-time universe filter")
    score_df["percentile"] = score_df.groupby("date")["score"].rank(
        pct=True,
        method="average",
    )
    cutoff = rank_ai_gate_effective_cutoff(settings, config)
    history: dict[pd.Timestamp, dict[str, RankAIGateScore]] = {}
    for current_date, rows in score_df.groupby("date", sort=True):
        daily: dict[str, RankAIGateScore] = {}
        for row in rows.itertuples(index=False):
            percentile = float(row.percentile)
            score = float(row.score)
            allowed = percentile >= cutoff
            status = "passed" if allowed else "blocked"
            daily[str(row.ticker)] = RankAIGateScore(
                ticker=str(row.ticker),
                score=score,
                percentile=percentile,
                allowed=allowed,
                reason=(
                    f"rank ai gate {status} "
                    f"(pct={percentile:.3f}, cutoff={cutoff:.3f})"
                ),
            )
        history[pd.Timestamp(current_date)] = daily
    return history


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
