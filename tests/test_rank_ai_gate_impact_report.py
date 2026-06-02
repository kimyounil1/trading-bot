import json
from pathlib import Path

import pandas as pd

from src.rank_ai_gate_impact_report import build_rank_ai_gate_impact_report


def test_rank_gate_impact_report_from_audit_and_cache(tmp_path, monkeypatch):
    audit_path = tmp_path / "execution_audit.csv"
    audit_path.write_text(
        "timestamp,event_type,ticker,action,status,reason\n"
        "2026-06-01T10:00:00,SKIP_BUY,AAA,BUY,SKIPPED,rank ai gate blocked (pct=0.700)\n"
        "2026-06-01T10:01:00,BUY_SUBMITTED,BBB,BUY,accepted,rank ai gate passed (pct=0.900)\n",
        encoding="utf-8",
    )
    buy_path = tmp_path / "latest_buy.csv"
    pd.DataFrame(
        [
            {
                "ticker": "AAA",
                "signal": "BUY",
                "risk_allowed": False,
                "reason": "rank ai gate blocked (pct=0.700, cutoff=0.850)",
                "rank_ai_percentile": 0.7,
                "rank_ai_gate_enabled": True,
            },
            {
                "ticker": "BBB",
                "signal": "BUY",
                "risk_allowed": True,
                "reason": "ok",
                "rank_ai_percentile": 0.92,
                "rank_ai_gate_enabled": True,
            },
        ]
    ).to_csv(buy_path, index=False)

    from types import SimpleNamespace

    monkeypatch.setattr(
        "src.rank_ai_gate_impact_report.load_settings",
        lambda: SimpleNamespace(
            rank_ai_buy_gate_enabled=True,
            rank_ai_buy_gate_model_path="logs/ml/rank_label_experiment_h20_top15_q85/rank_models.joblib",
            rank_ai_buy_gate_prediction_horizon=20,
            rank_ai_buy_gate_top_bucket_pct=0.15,
            rank_ai_buy_gate_min_score_quantile=0.85,
            rank_ai_buy_gate_fail_closed=True,
        ),
    )

    report = build_rank_ai_gate_impact_report(
        audit_path=audit_path,
        candidate_buy_path=buy_path,
        lookback_days=90,
    )

    assert report["execution_audit"]["skip_buy_rank_blocked"] == 1
    assert report["execution_audit"]["buy_submitted"] == 1
    assert report["candidate_cache"]["rank_blocked_rows"] == 1
    assert report["candidate_cache"]["rank_passed_rows"] == 1


def test_candidate_cache_stats_without_risk_allowed_column(tmp_path, monkeypatch):
    buy_path = tmp_path / "legacy_buy.csv"
    pd.DataFrame(
        [
            {
                "ticker": "AAA",
                "signal": "BUY",
                "reason": "rank ai gate blocked",
                "rank_ai_gate_enabled": "False",
            }
        ]
    ).to_csv(buy_path, index=False)

    from types import SimpleNamespace

    monkeypatch.setattr(
        "src.rank_ai_gate_impact_report.load_settings",
        lambda: SimpleNamespace(rank_ai_buy_gate_min_score_quantile=0.85),
    )

    stats = __import__(
        "src.rank_ai_gate_impact_report", fromlist=["_candidate_cache_stats"]
    )._candidate_cache_stats(buy_path, min_score_quantile=0.85)

    assert stats["rank_ai_gate_enabled"] is False
    assert stats["risk_allowed_rows"] == 0


def _mock_gate_settings(monkeypatch, **overrides):
    from types import SimpleNamespace

    values = {
        "rank_ai_buy_gate_enabled": True,
        "rank_ai_buy_gate_model_path": "logs/ml/rank_label_experiment_h20_top15_q85/rank_models.joblib",
        "rank_ai_buy_gate_prediction_horizon": 20,
        "rank_ai_buy_gate_top_bucket_pct": 0.15,
        "rank_ai_buy_gate_min_score_quantile": 0.85,
        "rank_ai_buy_gate_fail_closed": True,
    }
    values.update(overrides)
    monkeypatch.setattr(
        "src.rank_ai_gate_impact_report.load_settings",
        lambda: SimpleNamespace(**values),
    )


def test_rank_gate_impact_empty_audit_and_cache_notes(tmp_path, monkeypatch):
    _mock_gate_settings(monkeypatch)
    audit_path = tmp_path / "missing_audit.csv"
    cache_path = tmp_path / "missing_buy.csv"

    report = build_rank_ai_gate_impact_report(
        audit_path=audit_path,
        candidate_buy_path=cache_path,
        lookback_days=30,
    )

    assert report["execution_audit"]["rows"] == 0
    assert report["candidate_cache"]["available"] is False
    notes = "\n".join(report["notes"])
    assert "No execution_audit rows" in notes
    assert "Candidate cache missing" in notes


def test_rank_gate_impact_audit_blocked_passed_missing_reasons(tmp_path, monkeypatch):
    _mock_gate_settings(monkeypatch)
    audit_path = tmp_path / "execution_audit.csv"
    audit_path.write_text(
        "timestamp,event_type,ticker,action,status,reason\n"
        "2026-06-01T10:00:00,SKIP_BUY,AAA,BUY,SKIPPED,rank ai gate blocked (pct=0.700)\n"
        "2026-06-01T10:01:00,SKIP_BUY,BBB,BUY,SKIPPED,rank ai gate missing score\n"
        "2026-06-01T10:02:00,BUY_SUBMITTED,CCC,BUY,accepted,rank ai gate passed (pct=0.900)\n",
        encoding="utf-8",
    )

    report = build_rank_ai_gate_impact_report(
        audit_path=audit_path,
        candidate_buy_path=tmp_path / "missing_buy.csv",
        lookback_days=90,
    )

    audit = report["execution_audit"]
    assert audit["skip_buy_rank_blocked"] == 1
    assert audit["skip_buy_rank_missing_score"] == 1
    assert audit["buy_submitted"] == 1
    assert audit["buy_submitted_with_rank_pass_reason"] == 1
    assert audit["top_blocked_tickers"] == {"AAA": 1}


def test_rank_gate_impact_cache_risk_allowed_and_percentile_cutoff(tmp_path, monkeypatch):
    _mock_gate_settings(monkeypatch, rank_ai_buy_gate_min_score_quantile=0.85)
    buy_path = tmp_path / "latest_buy.csv"
    pd.DataFrame(
        [
            {
                "ticker": "LOW",
                "signal": "BUY",
                "risk_allowed": True,
                "reason": "ok",
                "rank_ai_percentile": 0.80,
                "rank_ai_gate_enabled": True,
            },
            {
                "ticker": "HIGH",
                "signal": "BUY",
                "risk_allowed": True,
                "reason": "rank ai gate passed (pct=0.920)",
                "rank_ai_percentile": 0.92,
                "rank_ai_gate_enabled": True,
            },
            {
                "ticker": "BLOCK",
                "signal": "BUY",
                "risk_allowed": False,
                "reason": "rank ai gate blocked (pct=0.700, cutoff=0.850)",
                "rank_ai_percentile": 0.70,
                "rank_ai_gate_enabled": True,
            },
            {
                "ticker": "HIGH_NO_RISK",
                "signal": "BUY",
                "risk_allowed": False,
                "reason": "other block",
                "rank_ai_percentile": 0.95,
                "rank_ai_gate_enabled": True,
            },
        ]
    ).to_csv(buy_path, index=False)

    report = build_rank_ai_gate_impact_report(
        audit_path=tmp_path / "missing_audit.csv",
        candidate_buy_path=buy_path,
        lookback_days=30,
    )

    cache = report["candidate_cache"]
    assert cache["available"] is True
    assert cache["rank_blocked_rows"] == 1
    assert cache["rank_passed_rows"] == 1
    assert cache["top_blocked_tickers"] == {"BLOCK": 1}
    assert cache["top_passed_tickers"] == {"HIGH": 1}
