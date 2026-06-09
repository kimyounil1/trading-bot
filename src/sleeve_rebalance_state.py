"""Persistent flags for one-shot / drift-triggered sleeve allocation rebalance."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.portfolio_sleeves import PortfolioSleeveSnapshot

STATE_PATH = Path("data/sleeve_rebalance_state.json")

DEFAULT_AUTO_DRIFT_THRESHOLD = 0.05


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_rebalance_state(path: Path = STATE_PATH) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Warning: failed to load sleeve rebalance state {path}: {exc}")
        return {}
    return payload if isinstance(payload, dict) else {}


def save_rebalance_state(state: dict[str, Any], *, path: Path = STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(f"{path.suffix}.tmp")
    temp_path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    with temp_path.open("r+", encoding="utf-8") as handle:
        handle.flush()
        os.fsync(handle.fileno())
    temp_path.replace(path)


def max_abs_sleeve_drift(snapshot: PortfolioSleeveSnapshot) -> float:
    portfolio_value = float(snapshot.portfolio_value or 0.0)
    if portfolio_value <= 0:
        return 0.0
    max_drift = 0.0
    for budget in snapshot.sleeves.values():
        current_weight = budget.current_notional / portfolio_value
        if budget.sleeve_id == "cash":
            current_weight = float(snapshot.account_cash) / portfolio_value
        max_drift = max(max_drift, abs(current_weight - budget.target_weight))
    return max_drift


def allocation_rebalance_pending(*, path: Path = STATE_PATH) -> bool:
    return bool(load_rebalance_state(path).get("allocation_rebalance_pending"))


def request_allocation_rebalance(*, reason: str = "manual", path: Path = STATE_PATH) -> None:
    state = load_rebalance_state(path)
    state["allocation_rebalance_pending"] = True
    state["requested_at"] = _utc_now_iso()
    state["request_reason"] = reason
    save_rebalance_state(state, path=path)


def clear_allocation_rebalance_pending(*, path: Path = STATE_PATH) -> None:
    state = load_rebalance_state(path)
    state["allocation_rebalance_pending"] = False
    state["last_completed_at"] = _utc_now_iso()
    save_rebalance_state(state, path=path)


def should_run_allocation_rebalance(
    snapshot: PortfolioSleeveSnapshot,
    *,
    auto_drift_threshold: float = DEFAULT_AUTO_DRIFT_THRESHOLD,
    path: Path = STATE_PATH,
) -> tuple[bool, str]:
    if not snapshot.enabled:
        return False, "sleeves_disabled"
    if allocation_rebalance_pending(path=path):
        return True, "pending_request"
    drift = max_abs_sleeve_drift(snapshot)
    if drift >= auto_drift_threshold:
        return True, f"drift={drift:.4f}>={auto_drift_threshold:.4f}"
    return False, "within_tolerance"
