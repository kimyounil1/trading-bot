"""CMS portfolio sleeve panel helpers (no Streamlit dependency)."""

from __future__ import annotations

__all__ = [
    "validate_sleeve_target_weights",
    "build_sleeve_control_panel_rows",
    "build_sleeves_config_dict",
    "merge_sleeve_settings_into_strategy",
    "save_sleeve_settings",
]


def validate_sleeve_target_weights(weights: dict[str, float]) -> list[str]:
    errors: list[str] = []
    if not weights:
        errors.append("sleeve weights must not be empty")
        return errors
    total = sum(max(0.0, float(value)) for value in weights.values())
    if total > 1.0 + 1e-9:
        errors.append(f"sleeve target weights sum to {total:.4f} (> 1.0)")
    cash_weight = float(weights.get("cash", 0.0))
    if cash_weight <= 0:
        errors.append("cash sleeve weight must be > 0")
    return errors


def build_sleeve_control_panel_rows(
    *,
    snapshot: object,
    tournament_summary: dict | None = None,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    sleeves = getattr(snapshot, "sleeves", {}) or {}
    tournament_summary = tournament_summary or {}
    tournament_block = tournament_summary.get("tournament_sleeve") or {}
    for sleeve_id, budget in sleeves.items():
        current_weight = (
            budget.current_notional / snapshot.portfolio_value
            if getattr(snapshot, "portfolio_value", 0) > 0
            else 0.0
        )
        rows.append(
            {
                "sleeve_id": sleeve_id,
                "target_weight": budget.target_weight,
                "current_weight": round(current_weight, 4),
                "drift": round(current_weight - budget.target_weight, 4),
                "order_budget": budget.order_budget,
                "available_cash": budget.available_cash,
                "return_21d": tournament_block.get("return_pct")
                if sleeve_id == "tournament"
                else None,
                "readiness": budget.risk_mode,
            }
        )
    return rows


def build_sleeves_config_dict(
    *,
    core_weight: float,
    tournament_weight: float,
    cash_weight: float,
    core_enabled: bool = True,
    tournament_enabled: bool = True,
    cash_enabled: bool = True,
) -> dict[str, dict[str, object]]:
    return {
        "core": {
            "enabled": core_enabled,
            "target_weight": round(float(core_weight), 4),
            "profile": "paper",
            "strategy": "current_core",
            "paper_only": False,
        },
        "tournament": {
            "enabled": tournament_enabled,
            "target_weight": round(float(tournament_weight), 4),
            "profile": "tournament_paper",
            "strategy": "alpha_tournament",
            "paper_only": False,
        },
        "cash": {
            "enabled": cash_enabled,
            "target_weight": round(float(cash_weight), 4),
            "strategy": "cash_reserve",
            "paper_only": False,
        },
    }


def merge_sleeve_settings_into_strategy(
    settings: object,
    *,
    portfolio_sleeves_enabled: bool,
    sleeves_config: dict[str, dict[str, object]],
) -> tuple[object | None, list[str]]:
    from dataclasses import asdict, fields

    from src.settings import (
        CONFIG_PATH,
        DEFAULT_SETTINGS,
        StrategySettings,
        _read_json_object,
        _validate_strategy_settings_payload,
        validate_settings,
    )

    settings_path = CONFIG_PATH.expanduser().resolve()
    merged = asdict(DEFAULT_SETTINGS)
    if settings_path.is_file():
        payload = _validate_strategy_settings_payload(
            _read_json_object(settings_path),
            settings_path,
        )
        merged.update(payload)
    elif hasattr(settings, "__dataclass_fields__"):
        merged.update(asdict(settings))  # type: ignore[arg-type]

    merged["portfolio_sleeves_enabled"] = bool(portfolio_sleeves_enabled)
    merged["sleeves"] = sleeves_config

    field_names = {item.name for item in fields(StrategySettings)}
    if "portfolio_sleeves_enabled" not in field_names:
        return (
            None,
            [
                "StrategySettings is missing portfolio_sleeves_enabled; "
                "restart Streamlit after updating the codebase"
            ],
        )

    filtered = {key: value for key, value in merged.items() if key in field_names}
    try:
        return validate_settings(StrategySettings(**filtered)), []
    except (TypeError, ValueError) as exc:
        return None, [str(exc)]


def save_sleeve_settings(
    settings: object,
    *,
    portfolio_sleeves_enabled: bool,
    core_weight: float,
    tournament_weight: float,
    cash_weight: float,
    core_enabled: bool = True,
    tournament_enabled: bool = True,
    cash_enabled: bool = True,
) -> list[str]:
    """Validate and persist sleeve fields to strategy_config.json."""

    weights = {
        "core": core_weight,
        "tournament": tournament_weight,
        "cash": cash_weight,
    }
    errors = validate_sleeve_target_weights(weights)
    if errors:
        return errors

    sleeves_config = build_sleeves_config_dict(
        core_weight=core_weight,
        tournament_weight=tournament_weight,
        cash_weight=cash_weight,
        core_enabled=core_enabled,
        tournament_enabled=tournament_enabled,
        cash_enabled=cash_enabled,
    )
    try:
        from src.settings import patch_strategy_config

        patch_strategy_config(
            {
                "portfolio_sleeves_enabled": bool(portfolio_sleeves_enabled),
                "sleeves": sleeves_config,
            }
        )
        return []
    except ValueError as exc:
        return [str(exc)]
