from types import SimpleNamespace

from src.rank_ai_gate import (
    RankAIGateScore,
    apply_rank_ai_buy_gate,
    rank_ai_gate_effective_cutoff,
)


def _settings(**overrides):
    values = {
        "rank_ai_buy_gate_enabled": True,
        "rank_ai_buy_gate_min_score_quantile": 0.85,
        "rank_ai_buy_gate_fail_closed": True,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_rank_ai_gate_effective_cutoff_uses_top_bucket_and_score_quantile():
    settings = _settings(
        rank_ai_buy_gate_min_score_quantile=0.85,
        rank_ai_buy_gate_top_bucket_pct=0.10,
    )
    assert rank_ai_gate_effective_cutoff(settings) == 0.90

    settings_loose_bucket = _settings(
        rank_ai_buy_gate_min_score_quantile=0.85,
        rank_ai_buy_gate_top_bucket_pct=0.20,
    )
    assert rank_ai_gate_effective_cutoff(settings_loose_bucket) == 0.85


def test_apply_rank_ai_buy_gate_blocks_below_cutoff():
    decision = apply_rank_ai_buy_gate(
        ticker="AAPL",
        settings=_settings(),
        risk_allowed=True,
        risk_reason="ok",
        target_amount=1000.0,
        scores={
            "AAPL": RankAIGateScore(
                ticker="AAPL",
                score=0.61,
                percentile=0.80,
                allowed=False,
                reason="rank ai gate blocked (pct=0.800, cutoff=0.850)",
            )
        },
    )

    assert not decision.risk_allowed
    assert decision.target_amount == 0.0
    assert "rank ai gate blocked" in decision.risk_reason
    assert decision.percentile == 0.80


def test_apply_rank_ai_buy_gate_allows_above_cutoff():
    decision = apply_rank_ai_buy_gate(
        ticker="MSFT",
        settings=_settings(),
        risk_allowed=True,
        risk_reason="risk passed",
        target_amount=1200.0,
        scores={
            "MSFT": RankAIGateScore(
                ticker="MSFT",
                score=0.72,
                percentile=0.90,
                allowed=True,
                reason="rank ai gate passed (pct=0.900, cutoff=0.850)",
            )
        },
    )

    assert decision.risk_allowed
    assert "risk passed" in decision.risk_reason
    assert "rank ai gate passed" in decision.risk_reason
    assert decision.target_amount == 1200.0
    assert decision.score == 0.72


def test_apply_rank_ai_buy_gate_missing_score_fails_closed():
    decision = apply_rank_ai_buy_gate(
        ticker="NVDA",
        settings=_settings(),
        risk_allowed=True,
        risk_reason="risk passed",
        target_amount=1200.0,
        scores={},
    )

    assert not decision.risk_allowed
    assert decision.target_amount == 0.0
    assert "missing score" in decision.risk_reason
