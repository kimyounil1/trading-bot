from pathlib import Path

import pandas as pd

from src.sleeve_performance_report import build_sleeve_performance_report


def test_sleeve_performance_report_writes_structure(tmp_path: Path) -> None:
    audit_path = tmp_path / "execution_audit.csv"
    audit_path.write_text(
        "timestamp,event_type,ticker,action,status,reason,sleeve_id\n"
        "2026-06-01T10:00:00,SKIP_BUY,AAA,BUY,SKIPPED,budget,core\n",
        encoding="utf-8",
    )
    report = build_sleeve_performance_report(
        account={"portfolio_value": 1000.0, "cash": 200.0, "buying_power": 200.0},
        positions=[],
        audit_path=audit_path,
    )
    assert "generated_at" in report
    assert "sleeves" in report


def test_sleeve_report_handles_empty_audit(tmp_path: Path, monkeypatch) -> None:
    from src.settings import StrategySettings

    monkeypatch.setattr(
        "src.sleeve_performance_report.load_settings",
        lambda: StrategySettings(portfolio_sleeves_enabled=False),
    )
    audit_path = tmp_path / "empty.csv"
    audit_path.write_text("timestamp,event_type\n", encoding="utf-8")
    report = build_sleeve_performance_report(audit_path=audit_path)
    assert report["portfolio_sleeves_enabled"] is False
