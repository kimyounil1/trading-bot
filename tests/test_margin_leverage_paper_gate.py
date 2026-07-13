"""Margin leverage paper gate ([AGY])."""

from datetime import datetime, timezone
from pathlib import Path

from src.margin_leverage_paper_gate import (
    evaluate_margin_leverage_buy_block,
    evaluate_conditional_margin_validation,
    evaluate_margin_leverage_paper_gate,
    MarginLeverageGateConfig,
    load_stress_summary,
    validate_margin_leverage_gate_report,
)

PASS_FIXTURE = (
    Path(__file__).resolve().parent / "fixtures" / "leverage_stress" / "pass_latest_summary.json"
)


def test_margin_leverage_gate_go():
    stress = load_stress_summary(PASS_FIXTURE)
    report = validate_margin_leverage_gate_report(
        evaluate_margin_leverage_paper_gate(stress, configured_leverage_factor=1.25)
    )
    assert report["decision"] == "GO_MARGIN_PAPER"


def test_margin_leverage_gate_no_go_when_stress_fails():
    stress = load_stress_summary(PASS_FIXTURE)
    stress = {**stress, "alerts": {**stress["alerts"], "passed": False}}
    report = evaluate_margin_leverage_paper_gate(stress, configured_leverage_factor=1.25)
    assert report["decision"] == "NO_GO"


def test_buy_block_when_leverage_flat():
    block, reason = evaluate_margin_leverage_buy_block(1.0)
    assert block is False
    assert reason == ""


def test_buy_block_when_stress_missing(tmp_path, monkeypatch):
    missing = tmp_path / "missing.json"
    block, reason = evaluate_margin_leverage_buy_block(
        1.25,
        stress_summary_path=missing,
    )
    assert block is True
    assert "missing" in reason.lower()


def test_buy_unblocked_when_gate_passes(monkeypatch):
    monkeypatch.setattr(
        "src.margin_leverage_paper_gate.load_margin_leverage_paper_config",
        lambda: type(
            "Cfg",
            (),
            {
                "stress_summary_path": PASS_FIXTURE,
                "max_allowed_leverage_factor": 1.5,
                "stress_leverage": 2.0,
                "require_stress_alerts_passed": True,
                "proposal_path": Path("config/margin_leverage_paper_proposal.json"),
            },
        )(),
    )
    block, _ = evaluate_margin_leverage_buy_block(1.25)
    assert block is False


def test_conditional_gate_accepts_validated_2x_policy(tmp_path):
    summary = tmp_path / "conditional.csv"
    end = datetime.now(timezone.utc).date().isoformat()
    summary.write_text(
        "mode,window,policy,total_return,max_drawdown,sharpe_ratio,max_gross_exposure,end\n"
        f"operational,1y,always_1x,1.30,-0.14,3.25,1.0,{end}\n"
        f"operational,1y,spy_bull_vix22_2x_else_1x,3.60,-0.21,3.42,2.0,{end}\n",
        encoding="utf-8",
    )
    config = MarginLeverageGateConfig(
        max_allowed_leverage_factor=2.0,
        conditional_summary_path=summary,
    )

    gate = evaluate_conditional_margin_validation(2.0, config=config)

    assert gate["decision"] == "GO_MARGIN_PAPER"


def test_conditional_buy_gate_fails_closed_when_validation_missing(tmp_path, monkeypatch):
    config = MarginLeverageGateConfig(
        max_allowed_leverage_factor=2.0,
        conditional_summary_path=tmp_path / "missing.csv",
    )
    monkeypatch.setattr(
        "src.margin_leverage_paper_gate.load_margin_leverage_paper_config",
        lambda: config,
    )

    block, reason = evaluate_margin_leverage_buy_block(
        2.0,
        margin_leverage_paper_enabled=True,
        conditional_margin_leverage_enabled=True,
    )

    assert block is True
    assert "missing" in reason.lower()
