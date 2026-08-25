from pathlib import Path

import pandas as pd

from src.portfolio_sleeves import TOURNAMENT_SLEEVE_ID, default_sleeves_config
from src.settings import StrategySettings
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
    monkeypatch.setattr(
        "src.sleeve_performance_report.load_settings",
        lambda: StrategySettings(portfolio_sleeves_enabled=False),
    )
    audit_path = tmp_path / "empty.csv"
    audit_path.write_text("timestamp,event_type\n", encoding="utf-8")
    report = build_sleeve_performance_report(audit_path=audit_path)
    assert report["portfolio_sleeves_enabled"] is False


def test_sleeve_report_nav_uses_position_sleeve_map(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "src.sleeve_performance_report.load_settings",
        lambda: StrategySettings(
            portfolio_sleeves_enabled=True,
            sleeves=default_sleeves_config(),
        ),
    )
    monkeypatch.setattr(
        "src.sleeve_performance_report.load_sleeve_position_map",
        lambda: {"NVDA": TOURNAMENT_SLEEVE_ID, "AAPL": "core"},
    )
    audit_path = tmp_path / "audit.csv"
    audit_path.write_text(
        "timestamp,event_type,ticker,sleeve_id,profile_name\n",
        encoding="utf-8",
    )
    report = build_sleeve_performance_report(
        account={
            "portfolio_value": 100_000.0,
            "cash": 20_000.0,
            "buying_power": 20_000.0,
        },
        positions=[
            {
                "symbol": "NVDA",
                "market_value": 30_000.0,
                "unrealized_pl": 100.0,
                "cost_basis": 29_900.0,
            },
            {
                "symbol": "AAPL",
                "market_value": 50_000.0,
                "unrealized_pl": -50.0,
                "cost_basis": 50_050.0,
            },
        ],
        audit_path=audit_path,
    )
    assert report["sleeves"]["tournament"]["nav"] == 30000.0
    assert report["sleeves"]["core"]["nav"] == 50000.0
    assert report["sleeves"]["tournament"]["open_positions"] == 1
    assert report["sleeves"]["core"]["open_positions"] == 1


def test_sleeve_report_recovers_untagged_open_position_from_audit(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(
        "src.sleeve_performance_report.load_settings",
        lambda: StrategySettings(
            portfolio_sleeves_enabled=True,
            sleeves=default_sleeves_config(),
        ),
    )
    monkeypatch.setattr(
        "src.sleeve_performance_report.load_sleeve_position_map",
        lambda: {},
    )
    audit_path = tmp_path / "audit.csv"
    pd.DataFrame(
        [
            {
                "timestamp": "2026-08-20T10:00:00",
                "event_type": "BUY_SUBMITTED",
                "ticker": "CIFU",
                "execution_ticker": "CIFU",
                "sleeve_id": "tournament",
                "profile_name": "AGGRESSIVE",
            }
        ]
    ).to_csv(audit_path, index=False)
    report = build_sleeve_performance_report(
        account={
            "portfolio_value": 100_000.0,
            "cash": 70_000.0,
            "buying_power": 70_000.0,
        },
        positions=[
            {
                "symbol": "CIFU",
                "market_value": 30_000.0,
                "unrealized_pl": 0.0,
                "cost_basis": 30_000.0,
            }
        ],
        audit_path=audit_path,
    )
    assert report["sleeves"]["tournament"]["nav"] == 30000.0
    assert report["sleeves"]["core"]["nav"] == 0.0
