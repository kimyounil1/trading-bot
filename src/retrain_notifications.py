"""Telegram and log hooks for retrain success, partial success, and failure."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from src.notifier import notify_error, notify_info

AppendRetrainLogFn = Callable[[str, object, float], None]


def notify_champion_retained_if_needed(promotion_report: dict, report_path: Path) -> None:
    if promotion_report.get("decision") == "PROMOTE":
        return
    notify_info(
        "ℹ️ Retrain finished; champion retained",
        f"Decision: {promotion_report.get('decision')}\n"
        f"Promotion report: {report_path}",
    )


def notify_retrain_failure(
    exc: Exception,
    elapsed_sec: float,
    *,
    append_retrain_log: AppendRetrainLogFn,
) -> None:
    append_retrain_log("failure", None, elapsed_sec)
    notify_error("AI Retrain Failed", exc)


def run_retrain_cli(main_fn: Callable[[], None], append_retrain_log: AppendRetrainLogFn) -> None:
    import time

    started = time.time()
    try:
        main_fn()
    except Exception as exc:
        notify_retrain_failure(exc, time.time() - started, append_retrain_log=append_retrain_log)
        raise SystemExit(1) from exc
