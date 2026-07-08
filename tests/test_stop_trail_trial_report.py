import json

import pandas as pd

from src.stop_trail_trial_report import (
    build_stop_trail_trial_report,
    close_trial,
    start_trial,
)


class _FakeSettings:
    stop_loss_pct = 0.05
    trailing_stop_pct = 0.10


def _write_state(tmp_path, started_at="2026-06-12", observation_days=14):
    state_path = tmp_path / "trial_state.json"
    state_path.write_text(
        json.dumps(
            {
                "trial": "stop5_trail10",
                "started_at": started_at,
                "observation_days": observation_days,
                "config": {"stop_loss_pct": 0.05, "trailing_stop_pct": 0.10},
                "baseline": {"stop_loss_pct": 0.05, "trailing_stop_pct": 0.20},
            }
        ),
        encoding="utf-8",
    )
    return state_path


def test_start_trial_records_config_and_refuses_overwrite(tmp_path):
    state_path = tmp_path / "trial_state.json"
    state = start_trial(state_path, settings=_FakeSettings())
    assert state["config"]["trailing_stop_pct"] == 0.10
    assert state["baseline"]["trailing_stop_pct"] == 0.20
    assert state["started_at"]

    again = start_trial(state_path, settings=_FakeSettings())
    assert again["started_at"] == state["started_at"]


def test_report_not_started(tmp_path):
    report = build_stop_trail_trial_report(
        state_path=tmp_path / "missing.json",
        audit_path=tmp_path / "missing.csv",
    )
    assert report["status"] == "NOT_STARTED"


def test_close_trial_freezes_report(tmp_path):
    state_path = _write_state(tmp_path)
    state = close_trial(state_path, reason="superseded by exit-sweep promotion")
    assert state["closed_at"]
    assert state["close_reason"] == "superseded by exit-sweep promotion"

    # idempotent — second close keeps the original date/reason
    again = close_trial(state_path, reason="different reason")
    assert again["closed_at"] == state["closed_at"]
    assert again["close_reason"] == "superseded by exit-sweep promotion"

    report = build_stop_trail_trial_report(
        state_path=state_path,
        audit_path=tmp_path / "missing.csv",
    )
    assert report["status"] == "CLOSED"
    assert report["close_reason"] == "superseded by exit-sweep promotion"
    assert "window_metrics" not in report


def test_report_window_metrics_and_exit_mix(tmp_path):
    state_path = _write_state(tmp_path, started_at="2026-06-12")
    audit_path = tmp_path / "execution_audit.csv"
    audit_path.write_text(
        "timestamp,event_type,ticker,action,status,reason\n"
        "2026-06-13T15:00:00Z,FULL_EXIT,AAA,SELL,filled,trailing stop triggered (10.2% drop from peak $50.00)\n"
        "2026-06-14T15:00:00Z,FULL_EXIT,BBB,SELL,filled,stop loss triggered\n"
        "2026-06-15T15:00:00Z,FULL_EXIT,CCC,SELL,filled,max holding period reached (30 days)\n"
        # Before trial start: ignored.
        "2026-06-01T15:00:00Z,FULL_EXIT,DDD,SELL,filled,trailing stop triggered (11% drop from peak $10.00)\n",
        encoding="utf-8",
    )
    equity = pd.DataFrame(
        {
            "date": pd.date_range("2026-06-10", periods=8, freq="D"),
            "equity": [100000, 100000, 101000, 99000, 98000, 99500, 100500, 101500],
        }
    )

    report = build_stop_trail_trial_report(
        state_path=state_path,
        audit_path=audit_path,
        equity_frame=equity,
        spy_return_fn=lambda start, end: 1.23,
        now=pd.Timestamp("2026-06-17"),
    )
    assert report["status"] == "OBSERVING"
    assert report["days_elapsed"] == 5
    # Window starts 06-12: equity 101000 -> 101500.
    assert report["window_metrics"]["return_pct"] == 0.5
    # Peak 101000 -> trough 98000.
    assert report["window_metrics"]["max_drawdown_pct"] == -2.97
    assert report["window_metrics"]["spy_return_pct"] == 1.23
    assert report["exit_mix_since_start"] == {
        "trailing_stop": 1,
        "stop_loss": 1,
        "max_holding": 1,
        "other": 0,
        "total": 3,
    }


def test_report_ready_to_evaluate_after_window(tmp_path):
    state_path = _write_state(tmp_path, started_at="2026-06-01", observation_days=14)
    report = build_stop_trail_trial_report(
        state_path=state_path,
        audit_path=tmp_path / "missing.csv",
        equity_frame=pd.DataFrame(columns=["date", "equity"]),
        spy_return_fn=lambda start, end: None,
        now=pd.Timestamp("2026-06-16"),
    )
    assert report["status"] == "READY_TO_EVALUATE"
    assert report["window_metrics"]["return_pct"] is None
