"""Trading environment profiles, schema checks, and live policy validation."""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.brokers.base import BrokerAdapter
from src.settings import StrategySettings, validate_settings

PROFILES_DIR = Path("config/profiles")
SCHEMA_PATH = Path("config/schema/trading_config.schema.json")
VALID_ENVIRONMENTS = frozenset({"paper", "live", "research"})


def resolve_trading_environment(settings: StrategySettings) -> str:
    env = os.environ.get("TRADING_ENV", "").strip().lower()
    if not env:
        env = str(getattr(settings, "trading_environment", "paper")).strip().lower()
    if env not in VALID_ENVIRONMENTS:
        raise ValueError(
            f"trading_environment must be one of {sorted(VALID_ENVIRONMENTS)}; got {env!r}"
        )
    return env


def load_profile_overlay(environment: str) -> dict[str, Any]:
    path = PROFILES_DIR / f"{environment}.json"
    if environment == "live":
        path = PROFILES_DIR / "live_safe.json"
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: profile must be a JSON object")
    return {k: v for k, v in payload.items() if k not in {"profile", "description"}}


def apply_environment_profile(
    settings: StrategySettings,
    environment: str,
) -> StrategySettings:
    overlay = load_profile_overlay(environment)
    if not overlay:
        merged = asdict(settings)
        merged["trading_environment"] = environment
        return validate_settings(StrategySettings(**merged))
    merged = asdict(settings)
    merged.update(overlay)
    merged["trading_environment"] = environment
    return validate_settings(StrategySettings(**merged))


def _load_schema() -> dict[str, Any]:
    if not SCHEMA_PATH.is_file():
        return {}
    data = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def validate_config_schema(payload: dict[str, Any]) -> list[str]:
    """Lightweight schema validation without external jsonschema dependency."""
    schema = _load_schema()
    props = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
    errors: list[str] = []

    for key in schema.get("required") or []:
        if key not in payload:
            errors.append(f"missing required field: {key}")

    for key, rule in props.items():
        if key not in payload:
            continue
        value = payload[key]
        expected = rule.get("type")
        if expected == "string" and not isinstance(value, str):
            errors.append(f"{key}: expected string")
        elif expected == "boolean" and not isinstance(value, bool):
            errors.append(f"{key}: expected boolean")
        elif expected == "integer" and not isinstance(value, int):
            errors.append(f"{key}: expected integer")
        elif expected == "number" and not isinstance(value, (int, float)):
            errors.append(f"{key}: expected number")
        elif expected == "array" and not isinstance(value, list):
            errors.append(f"{key}: expected array")
        enum = rule.get("enum")
        if enum and value not in enum:
            errors.append(f"{key}: must be one of {enum}")

    tickers = payload.get("tickers")
    if tickers is not None:
        if not isinstance(tickers, list) or not tickers:
            errors.append("tickers: must be a non-empty list")

    return errors


def _strategy_field_names() -> set[str]:
    from src.settings import StrategySettings
    from dataclasses import fields

    return {f.name for f in fields(StrategySettings)}


def validate_live_policies(
    settings: StrategySettings,
    environment: str,
    broker: BrokerAdapter,
) -> list[str]:
    """Return blocking reasons when configuration is unsafe for the environment."""
    reasons: list[str] = []

    if environment == "research" and os.environ.get("TRADING_ENV", "").lower() == "live":
        reasons.append("research profile cannot run with TRADING_ENV=live")

    if environment != "live":
        return reasons

    if not broker.is_live_capable():
        reasons.append(f"broker_provider={settings.broker_provider!r} is not live-capable")

    if settings.rank_ai_buy_gate_enabled and not getattr(settings, "live_readiness_passed", False):
        reasons.append(
            "rank_ai_buy_gate_enabled requires live_readiness_passed=true on live profile"
        )

    if not settings.llm_advisory_only:
        min_n = int(getattr(settings, "llm_precision_min_n", 0))
        if min_n <= 0:
            reasons.append("llm_advisory_only=false requires llm_precision_min_n > 0")

    if settings.ai_exit_enabled and not getattr(settings, "exit_model_gate_ready", False):
        reasons.append("ai_exit_enabled requires exit_model_gate_ready=true on live")

    if settings.live_safety_enabled:
        pct = float(getattr(settings, "live_safety_max_daily_loss_pct", 0.0))
        amount = float(getattr(settings, "live_safety_max_daily_loss_amount", 0.0))
        if pct <= 0 and amount <= 0:
            reasons.append(
                "live_safety_enabled requires live_safety_max_daily_loss_pct or "
                "live_safety_max_daily_loss_amount"
            )
    else:
        reasons.append("live environment requires live_safety_enabled=true")

    return reasons


def validate_trading_config(
    settings: StrategySettings,
    environment: str,
    broker: BrokerAdapter,
) -> None:
    payload = asdict(settings)
    schema_errors = validate_config_schema(payload)
    policy_errors = validate_live_policies(settings, environment, broker)
    errors = schema_errors + policy_errors
    if errors:
        joined = "; ".join(errors)
        raise ValueError(f"Trading config validation failed ({environment}): {joined}")
