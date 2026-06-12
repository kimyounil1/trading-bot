"""Aggregate GO/NO_GO for live trading from ops reports and safety config."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.brokers import get_broker_adapter
from src.risk.live_safety import LiveSafetyGuard
from src.settings import load_settings
from src.trading_config_guard import (
    apply_environment_profile,
    resolve_trading_environment,
    validate_live_policies,
)
from src.portfolio_sleeves import load_sleeve_definitions

DEFAULT_OUTPUT = Path("logs/live_readiness/latest_summary.json")

PAPER_VALIDATION_PATH = Path("logs/paper_validation/latest_summary.json")
LLM_PRECISION_PATH = Path("logs/llm_advisory/precision.json")
MODEL_QUALITY_PATH = Path("logs/model_quality/latest_summary.json")
SCHEDULER_HEALTH_PATH = Path("logs/paper_ops/scheduler_health.json")
DATA_HEALTH_PATH = Path("logs/data_health/latest_summary.json")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _llm_precision_sample_n(report: dict[str, Any]) -> int:
    # events_used counts matured forward returns at the report's shortest horizon.
    events = report.get("events_used") or {}
    reject_n = events.get("llm_reject")
    accept_n = events.get("llm_accept")
    if isinstance(reject_n, int) and isinstance(accept_n, int):
        return reject_n + accept_n
    fwd = report.get("forward_return") or {}
    reject_fwd = int((fwd.get("llm_reject") or {}).get("n") or 0)
    accept_fwd = int((fwd.get("llm_accept") or {}).get("n") or 0)
    return reject_fwd + accept_fwd


def build_live_readiness_report(
    *,
    settings: Any | None = None,
    environment: str | None = None,
) -> dict[str, Any]:
    base_settings = settings or load_settings()
    env = environment or resolve_trading_environment(base_settings)
    profile_settings = apply_environment_profile(base_settings, env)
    broker = get_broker_adapter(profile_settings.broker_provider)

    reasons: list[str] = []
    warnings: list[str] = []

    policy_errors = validate_live_policies(profile_settings, env, broker)
    reasons.extend(policy_errors)

    guard = LiveSafetyGuard.from_settings(profile_settings)
    if guard.kill_switch_active():
        reasons.append("manual_kill_switch_active")

    paper = _read_json(PAPER_VALIDATION_PATH)
    rank = paper.get("rank_gate_paper_tracker") or {}
    rank_days = int(rank.get("calendar_days_with_rank_events") or 0)
    min_rank_days = int(rank.get("min_calendar_days_required") or 14)
    rank_ready = bool(rank.get("gate_ready"))
    if profile_settings.rank_ai_buy_gate_enabled:
        if not rank_ready:
            reasons.append(f"rank_gate_ready=false ({rank_days}/{min_rank_days} calendar days)")
    history_path = Path("logs/paper_validation/history.jsonl")
    history_days = 0
    if history_path.is_file():
        history_days = sum(1 for line in history_path.read_text(encoding="utf-8").splitlines() if line.strip())
    if history_days < min_rank_days:
        reasons.append(f"paper_validation_history_days={history_days} < {min_rank_days}")

    if not profile_settings.llm_advisory_only:
        precision = _read_json(LLM_PRECISION_PATH)
        min_n = int(getattr(profile_settings, "llm_precision_min_n", 5))
        sample_n = _llm_precision_sample_n(precision)
        if sample_n < min_n:
            reasons.append(f"llm_precision_n={sample_n} < required {min_n}")

    model_quality = _read_json(MODEL_QUALITY_PATH)
    if not model_quality:
        warnings.append("model_quality_report_missing")
    else:
        decision = str(model_quality.get("decision", ""))
        if decision.upper() == "PROMOTE":
            reasons.append("model_quality decision=PROMOTE (champion swap not allowed pre-live)")

    scheduler = _read_json(SCHEDULER_HEALTH_PATH)
    if not scheduler:
        warnings.append("scheduler_health_report_missing")
    elif str(scheduler.get("timer_active", "")).lower() not in {"active", "activating"}:
        warnings.append(f"scheduler_timer_active={scheduler.get('timer_active')}")

    data_health = _read_json(DATA_HEALTH_PATH)
    if not data_health:
        warnings.append("data_health_report_missing (Phase 34-D)")
    elif str(data_health.get("overall", "")).upper() == "NO_GO":
        reasons.append("data_health overall=NO_GO")

    if getattr(profile_settings, "portfolio_sleeves_enabled", False):
        definitions = load_sleeve_definitions(profile_settings)
        tournament = definitions.get("tournament")
        if tournament is not None and tournament.enabled:
            warnings.append("tournament sleeve enabled (paper-only track)")
        if env == "live":
            for sleeve_id, definition in definitions.items():
                if definition.enabled and definition.paper_only:
                    reasons.append(
                        f"tournament/live blocked: sleeve {sleeve_id} is paper_only"
                    )

    deploy = {
        "TRADING_ENV": __import__("os").environ.get("TRADING_ENV", ""),
        "ALLOW_LIVE_TRADING": __import__("os").environ.get("ALLOW_LIVE_TRADING", ""),
        "CONFIRM_LIVE_TRADING_set": bool(__import__("os").environ.get("CONFIRM_LIVE_TRADING")),
    }

    safe = len(reasons) == 0
    overall = "GO" if safe else "NO_GO"

    return {
        "generated_at": _utc_now_iso(),
        "overall": overall,
        "safe_to_execute_live": safe,
        "trading_environment": env,
        "reasons": reasons,
        "warnings": warnings,
        "checks": {
            "rank_gate_ready": rank_ready,
            "rank_calendar_days": rank_days,
            "paper_validation_history_days": history_days,
            "llm_precision_min_n": int(getattr(profile_settings, "llm_precision_min_n", 5)),
            "kill_switch_active": guard.kill_switch_active(),
            "broker_live_capable": broker.is_live_capable(),
            "live_safety_enabled": bool(profile_settings.live_safety_enabled),
            "live_readiness_passed_flag": bool(
                getattr(profile_settings, "live_readiness_passed", False)
            ),
        },
        "deploy_env": deploy,
        "sources": {
            "paper_validation": str(PAPER_VALIDATION_PATH),
            "llm_precision": str(LLM_PRECISION_PATH),
            "model_quality": str(MODEL_QUALITY_PATH),
            "scheduler_health": str(SCHEDULER_HEALTH_PATH),
            "data_health": str(DATA_HEALTH_PATH),
        },
    }


def write_live_readiness_report(
    output_path: str | Path = DEFAULT_OUTPUT,
    *,
    settings: Any | None = None,
) -> Path:
    report = build_live_readiness_report(settings=settings)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def assert_live_readiness_for_execute(
    *,
    settings: Any,
    environment: str,
    report_path: Path = DEFAULT_OUTPUT,
) -> None:
    if environment != "live":
        return
    report = build_live_readiness_report(settings=settings, environment=environment)
    write_live_readiness_report(report_path, settings=settings)
    if not report.get("safe_to_execute_live"):
        reasons = report.get("reasons") or []
        raise RuntimeError(
            "Live readiness NO_GO: " + "; ".join(str(r) for r in reasons[:8])
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build live readiness GO/NO_GO summary")
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Output JSON path",
    )
    args = parser.parse_args()
    path = write_live_readiness_report(args.output)
    report = json.loads(path.read_text(encoding="utf-8"))
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
