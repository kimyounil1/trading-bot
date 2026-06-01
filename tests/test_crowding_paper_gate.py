from pathlib import Path

import json

from src.crowding_paper_gate import (
    apply_crowding_paper_proposal_if_go,
    evaluate_crowding_paper_gate,
    load_guard_impact_summary,
    validate_crowding_gate_report,
)
from src.settings import load_settings

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "guard_impact" / "latest_summary.json"


def test_crowding_paper_gate_go():
    report = validate_crowding_gate_report(
        evaluate_crowding_paper_gate(load_guard_impact_summary(FIXTURE))
    )
    assert report["decision"] == "GO_PAPER"
    assert all(item["pass"] for item in report["checklist"])


def test_apply_crowding_proposal_on_go(tmp_path, monkeypatch):
    config_path = tmp_path / "strategy_config.json"
    proposal_path = tmp_path / "crowding_paper_proposal.json"
    config_path.write_text(
        json.dumps({"tickers": ["AAPL", "MSFT"], "crowding_guard_enabled": False}),
        encoding="utf-8",
    )
    proposal_path.write_text(
        json.dumps(
            {
                "crowding_guard_enabled": True,
                "crowding_lookback_days": 45,
                "crowding_max_positions": 3,
                "crowding_momentum_threshold": 0.12,
                "crowding_trend_gap_threshold": 0.04,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("UNIVERSE_PROFILE", "smoke")
    result = apply_crowding_paper_proposal_if_go(
        {"decision": "GO_PAPER"},
        config_path=config_path,
        proposal_path=proposal_path,
    )
    assert result["applied"] is True
    updated = json.loads(config_path.read_text(encoding="utf-8"))
    assert updated["tickers"] == ["AAPL", "MSFT"]
    assert updated["crowding_guard_enabled"] is True
    assert updated["crowding_lookback_days"] == 45


def test_apply_crowding_proposal_skipped_on_no_go(tmp_path):
    config_path = tmp_path / "strategy_config.json"
    proposal_path = tmp_path / "crowding_paper_proposal.json"
    config_path.write_text(json.dumps({"tickers": ["AAPL"], "crowding_guard_enabled": False}), encoding="utf-8")
    before = config_path.read_text(encoding="utf-8")
    proposal_path.write_text(json.dumps({"crowding_guard_enabled": True}), encoding="utf-8")
    result = apply_crowding_paper_proposal_if_go(
        {"decision": "NO_GO"},
        config_path=config_path,
        proposal_path=proposal_path,
    )
    assert result["applied"] is False
    assert config_path.read_text(encoding="utf-8") == before
