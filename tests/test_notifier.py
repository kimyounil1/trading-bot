import logging
from types import SimpleNamespace

from src import notifier


def test_send_telegram_logs_failure(monkeypatch, caplog):
    monkeypatch.setattr(notifier, "telegram_is_configured", lambda: True)
    def _raise_timeout(*args, **kwargs):
        raise notifier.requests.exceptions.ConnectionError("timeout")

    monkeypatch.setattr(notifier.requests, "post", _raise_timeout)

    with caplog.at_level(logging.WARNING, logger="src.notifier"):
        ok = notifier.send_telegram_message("hello")

    assert ok is False
    assert any("Telegram send failed" in record.message for record in caplog.records)


def test_send_telegram_logs_api_ok_false(monkeypatch, caplog):
    class _Resp:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"ok": False, "description": "blocked"}

    monkeypatch.setattr(notifier, "telegram_is_configured", lambda: True)
    monkeypatch.setattr(notifier.requests, "post", lambda *args, **kwargs: _Resp())

    with caplog.at_level(logging.WARNING, logger="src.notifier"):
        ok = notifier.send_telegram_message("hello")

    assert ok is False
    assert any("ok=false" in record.message for record in caplog.records)
