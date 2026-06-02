"""Smoke: rank AI gate impact report from tmp fixtures only."""

from pathlib import Path

import pandas as pd

from src.rank_ai_gate_impact_report import build_rank_ai_gate_impact_report


def test_rank_gate_report_smoke(tmp_path: Path) -> None:
    audit_path = tmp_path / "execution_audit.csv"
    audit_path.write_text(
        "timestamp,event_type,ticker,action,status,reason\n"
        "2026-06-01T10:00:00,SKIP_BUY,XYZ,BUY,SKIPPED,rank ai gate blocked (pct=0.500)\n",
        encoding="utf-8",
    )
    buy_path = tmp_path / "latest_buy.csv"
    pd.DataFrame(
        [
            {
                "ticker": "XYZ",
                "signal": "BUY",
                "risk_allowed": False,
                "reason": "rank ai gate blocked (pct=0.500)",
                "rank_ai_percentile": 0.5,
                "rank_ai_gate_enabled": True,
            }
        ]
    ).to_csv(buy_path, index=False)

    report = build_rank_ai_gate_impact_report(
        audit_path=audit_path,
        candidate_buy_path=buy_path,
        lookback_days=90,
    )

    assert report["execution_audit"]["skip_buy_rank_blocked"] >= 1
    assert report["candidate_cache"]["available"] is True
    assert "gate" in report
    assert isinstance(report["notes"], list)
