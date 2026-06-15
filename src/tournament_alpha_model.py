"""Tournament sleeve alpha adapter — reuses rank output for concentrated picks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional

from src.rank_ai_gate import rank_ai_gate_effective_cutoff


@dataclass(frozen=True)
class TournamentAlphaSignal:
    alpha_score: float
    confidence: float
    target_holding_days: int
    max_position_pct: float
    stop_policy: str
    reason: str


def _rank_gate_fields(
    ticker: str,
    rank_scores: Mapping[str, Any],
) -> tuple[Optional[float], Optional[float]]:
    """Return (cross-sectional percentile, raw model score) for a ticker."""
    payload = rank_scores.get(str(ticker).upper())
    if payload is None:
        return None, None

    percentile: Optional[float] = None
    raw_score: Optional[float] = None

    if hasattr(payload, "percentile") and hasattr(payload, "score"):
        try:
            percentile = float(payload.percentile)
            raw_score = float(payload.score)
        except (TypeError, ValueError):
            return None, None
        return percentile, raw_score

    if isinstance(payload, dict):
        for key in ("percentile", "rank_ai_percentile"):
            raw = payload.get(key)
            if raw is not None:
                try:
                    percentile = float(raw)
                    break
                except (TypeError, ValueError):
                    continue
        for key in ("score", "rank_ai_score"):
            raw = payload.get(key)
            if raw is not None:
                try:
                    raw_score = float(raw)
                    break
                except (TypeError, ValueError):
                    continue
        return percentile, raw_score

    try:
        return None, float(payload)
    except (TypeError, ValueError):
        return None, None


def score_tournament_candidate(
    ticker: str,
    *,
    rank_scores: Mapping[str, Any],
    ai_score: Optional[float] = None,
    settings: Any | None = None,
) -> Optional[TournamentAlphaSignal]:
    percentile, raw_score = _rank_gate_fields(ticker, rank_scores)
    if percentile is None and raw_score is None:
        return None

    cutoff = rank_ai_gate_effective_cutoff(settings) if settings is not None else 0.85
    if percentile is not None:
        confidence = min(1.0, max(0.0, percentile))
        if confidence < cutoff:
            return None
    else:
        # Legacy callers may pass only a 0–1 "score" without cross-sectional ranks.
        confidence = min(1.0, max(0.0, float(raw_score)))
        if confidence < cutoff:
            return None

    rank_value = raw_score if raw_score is not None else confidence
    ai_component = float(ai_score) if ai_score is not None else 0.5
    alpha_score = round(0.65 * confidence + 0.35 * ai_component, 4)
    max_positions = int(getattr(settings, "max_total_positions", 5))
    max_position_pct = min(
        0.35,
        float(getattr(settings, "max_position_pct", 0.35)),
    )
    holding_days = min(int(getattr(settings, "max_holding_days", 14)), 14)

    return TournamentAlphaSignal(
        alpha_score=alpha_score,
        confidence=confidence,
        target_holding_days=holding_days,
        max_position_pct=max_position_pct,
        stop_policy="tight_trailing",
        reason=(
            f"tournament alpha pct={confidence:.3f} rank={rank_value:.3f} ai={ai_component:.3f} "
            f"max_positions={max_positions}"
        ),
    )


def select_tournament_candidates(
    tickers: list[str],
    *,
    rank_scores: Mapping[str, Any],
    ai_scores: Mapping[str, Optional[float]] | None = None,
    settings: Any | None = None,
    max_picks: int = 5,
) -> dict[str, TournamentAlphaSignal]:
    ai_scores = ai_scores or {}
    scored: list[tuple[str, TournamentAlphaSignal]] = []
    for ticker in tickers:
        signal = score_tournament_candidate(
            ticker,
            rank_scores=rank_scores,
            ai_score=ai_scores.get(str(ticker).upper()),
            settings=settings,
        )
        if signal is not None:
            scored.append((str(ticker).upper(), signal))
    scored.sort(key=lambda item: item[1].alpha_score, reverse=True)
    return dict(scored[: max(1, max_picks)])
