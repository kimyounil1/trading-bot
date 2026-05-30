"""Retrain failure and partial-success Telegram paths ([AGY])."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src import retrain_notifications as retrain


def test_notify_champion_retained_sends_info(monkeypatch):
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(
        retrain,
        "notify_info",
        lambda title, body: calls.append((title, body)) or True,
    )
    retrain.notify_champion_retained_if_needed(
        {"decision": "RETAIN_CHAMPION"},
        Path("logs/ml/model_promotion_report.json"),
    )
    assert len(calls) == 1
    assert "champion retained" in calls[0][0].lower()


def test_notify_champion_retained_skips_on_promote(monkeypatch):
    monkeypatch.setattr(retrain, "notify_info", MagicMock())
    retrain.notify_champion_retained_if_needed(
        {"decision": "PROMOTE"},
        Path("logs/ml/model_promotion_report.json"),
    )
    retrain.notify_info.assert_not_called()


def test_notify_retrain_failure_logs_and_errors(monkeypatch):
    log_calls: list[str] = []
    error_calls: list[tuple[str, str]] = []
    monkeypatch.setattr(
        retrain,
        "notify_error",
        lambda title, err: error_calls.append((title, str(err))) or True,
    )

    def _append(status, metrics_df, elapsed):
        log_calls.append(status)

    retrain.notify_retrain_failure(
        RuntimeError("data load failed"),
        12.5,
        append_retrain_log=_append,
    )
    assert log_calls == ["failure"]
    assert error_calls[0][0] == "AI Retrain Failed"
    assert "data load failed" in error_calls[0][1]


def test_run_retrain_cli_exits_on_main_failure(monkeypatch):
    monkeypatch.setattr(retrain, "notify_retrain_failure", MagicMock())
    with pytest.raises(SystemExit) as exc:
        retrain.run_retrain_cli(
            lambda: (_ for _ in ()).throw(ValueError("train crash")),
            lambda *a, **k: None,
        )
    assert exc.value.code == 1
    retrain.notify_retrain_failure.assert_called_once()
