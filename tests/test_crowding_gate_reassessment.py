import json

from src.crowding_gate_reassessment import build_crowding_gate_reassessment


def test_crowding_reassessment_disable_when_no_evidence(tmp_path):
    go = tmp_path / "go.json"
    go.write_text(
        json.dumps(
            {
                "decision": "NO_GO",
                "metrics": {
                    "delta": {"sharpe_ratio": -0.7, "total_return_pct": -20.0},
                    "guarded": {"estimated_crowding_blocked_trades": 0},
                },
            }
        ),
        encoding="utf-8",
    )
    live = tmp_path / "live.json"
    live.write_text(
        json.dumps({"live": {"crowding_skip_count": 0, "crowding_skip_rate_of_skips": 0.0}}),
        encoding="utf-8",
    )
    report = build_crowding_gate_reassessment(go_no_go_path=go, live_impact_path=live)
    assert report["recommendation"] == "DISABLE_OR_KEEP_OFF"


def test_crowding_reassessment_tune_when_live_skips_present(tmp_path):
    go = tmp_path / "go.json"
    go.write_text(
        json.dumps(
            {
                "decision": "NO_GO",
                "metrics": {
                    "delta": {"sharpe_ratio": -0.2, "total_return_pct": -2.0},
                    "guarded": {"estimated_crowding_blocked_trades": 0},
                },
            }
        ),
        encoding="utf-8",
    )
    live = tmp_path / "live.json"
    live.write_text(
        json.dumps({"live": {"crowding_skip_count": 30, "crowding_skip_rate_of_skips": 0.08}}),
        encoding="utf-8",
    )
    report = build_crowding_gate_reassessment(go_no_go_path=go, live_impact_path=live)
    assert report["recommendation"] == "TUNE"
