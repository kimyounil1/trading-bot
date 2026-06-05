"""Pre-live safety limits and manual kill switch."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional


@dataclass(frozen=True)
class SafetyCheckResult:
    allowed: bool
    reason: str = ""


@dataclass(frozen=True)
class LiveSafetyConfig:
    enabled: bool = False
    kill_switch_path: Path = Path("data/runtime/KILL_SWITCH")
    state_path: Path = Path("data/runtime/live_safety_state.json")
    max_daily_loss_pct: float = 0.0
    max_daily_loss_amount: float = 0.0
    max_position_notional: float = 0.0
    max_total_exposure: float = 0.0
    max_orders_per_day: int = 0
    max_consecutive_order_failures: int = 0


class LiveSafetyGuard:
    """Blocks new buys when limits or kill switch are tripped."""

    def __init__(
        self,
        config: LiveSafetyConfig,
        *,
        trading_day: Optional[date] = None,
        account: Optional[dict[str, Any]] = None,
        positions: Optional[list[dict[str, Any]]] = None,
    ) -> None:
        self.config = config
        self.trading_day = trading_day or datetime.now(timezone.utc).date()
        self.account = account or {}
        self.positions = positions or []
        self._state = self._load_state()

    @classmethod
    def from_settings(
        cls,
        settings: Any,
        *,
        account: Optional[dict[str, Any]] = None,
        positions: Optional[list[dict[str, Any]]] = None,
    ) -> LiveSafetyGuard:
        config = LiveSafetyConfig(
            enabled=bool(getattr(settings, "live_safety_enabled", False)),
            kill_switch_path=Path(
                getattr(settings, "live_safety_kill_switch_path", "data/runtime/KILL_SWITCH")
            ),
            state_path=Path(
                getattr(settings, "live_safety_state_path", "data/runtime/live_safety_state.json")
            ),
            max_daily_loss_pct=float(getattr(settings, "live_safety_max_daily_loss_pct", 0.0)),
            max_daily_loss_amount=float(
                getattr(settings, "live_safety_max_daily_loss_amount", 0.0)
            ),
            max_position_notional=float(
                getattr(settings, "live_safety_max_position_notional", 0.0)
            ),
            max_total_exposure=float(getattr(settings, "live_safety_max_total_exposure", 0.0)),
            max_orders_per_day=int(getattr(settings, "live_safety_max_orders_per_day", 0)),
            max_consecutive_order_failures=int(
                getattr(settings, "live_safety_max_consecutive_order_failures", 0)
            ),
        )
        return cls(config, account=account, positions=positions)

    def kill_switch_active(self) -> bool:
        return self.config.kill_switch_path.is_file()

    def check_new_buy(self, *, notional: float, open_positions_count: int) -> SafetyCheckResult:
        if self.kill_switch_active():
            return SafetyCheckResult(
                allowed=False,
                reason=f"manual kill switch: {self.config.kill_switch_path}",
            )

        if self.config.max_consecutive_order_failures > 0:
            failures = int(self._day_state().get("consecutive_failures", 0))
            if failures >= self.config.max_consecutive_order_failures:
                return SafetyCheckResult(
                    allowed=False,
                    reason=(
                        f"consecutive order failures {failures} >= "
                        f"{self.config.max_consecutive_order_failures}"
                    ),
                )

        if not self.config.enabled:
            return SafetyCheckResult(allowed=True)

        if self.config.max_orders_per_day > 0:
            submitted = int(self._day_state().get("orders_submitted", 0))
            if submitted >= self.config.max_orders_per_day:
                return SafetyCheckResult(
                    allowed=False,
                    reason=(
                        f"daily order cap {submitted} >= {self.config.max_orders_per_day}"
                    ),
                )

        if notional <= 0:
            return SafetyCheckResult(allowed=False, reason="notional must be positive")

        if self.config.max_position_notional > 0 and notional > self.config.max_position_notional:
            return SafetyCheckResult(
                allowed=False,
                reason=(
                    f"order notional ${notional:.2f} exceeds max_position_notional "
                    f"${self.config.max_position_notional:.2f}"
                ),
            )

        portfolio_value = float(self.account.get("portfolio_value") or 0.0)
        last_equity = float(self.account.get("last_equity") or portfolio_value or 0.0)

        if self.config.max_total_exposure > 0 and portfolio_value > 0:
            exposure = self._position_market_value() + notional
            ratio = exposure / portfolio_value
            if ratio > self.config.max_total_exposure:
                return SafetyCheckResult(
                    allowed=False,
                    reason=(
                        f"total exposure {ratio:.2%} would exceed "
                        f"max_total_exposure {self.config.max_total_exposure:.2%}"
                    ),
                )

        if last_equity > 0:
            if self.config.max_daily_loss_pct > 0:
                floor = last_equity * (1.0 - self.config.max_daily_loss_pct)
                if portfolio_value <= floor:
                    return SafetyCheckResult(
                        allowed=False,
                        reason=(
                            f"daily loss pct: portfolio ${portfolio_value:.2f} <= "
                            f"floor ${floor:.2f} ({self.config.max_daily_loss_pct:.2%} of last_equity)"
                        ),
                    )
            if self.config.max_daily_loss_amount > 0:
                loss = last_equity - portfolio_value
                if loss >= self.config.max_daily_loss_amount:
                    return SafetyCheckResult(
                        allowed=False,
                        reason=(
                            f"daily loss amount ${loss:.2f} >= "
                            f"${self.config.max_daily_loss_amount:.2f}"
                        ),
                    )

        if (
            self.config.max_total_exposure > 0
            and open_positions_count >= 1
            and portfolio_value <= 0
        ):
            return SafetyCheckResult(allowed=False, reason="portfolio_value unavailable")

        return SafetyCheckResult(allowed=True)

    def record_order_success(self) -> None:
        day = self._day_state()
        day["orders_submitted"] = int(day.get("orders_submitted", 0)) + 1
        day["consecutive_failures"] = 0
        self._save_state()

    def record_order_failure(self) -> None:
        day = self._day_state()
        day["consecutive_failures"] = int(day.get("consecutive_failures", 0)) + 1
        self._save_state()

    def summary(self) -> dict[str, Any]:
        day = self._day_state()
        return {
            "trading_day": self.trading_day.isoformat(),
            "kill_switch_active": self.kill_switch_active(),
            "live_safety_enabled": self.config.enabled,
            "orders_submitted_today": int(day.get("orders_submitted", 0)),
            "consecutive_failures": int(day.get("consecutive_failures", 0)),
            "config": {
                "max_daily_loss_pct": self.config.max_daily_loss_pct,
                "max_daily_loss_amount": self.config.max_daily_loss_amount,
                "max_position_notional": self.config.max_position_notional,
                "max_total_exposure": self.config.max_total_exposure,
                "max_orders_per_day": self.config.max_orders_per_day,
                "max_consecutive_order_failures": self.config.max_consecutive_order_failures,
            },
        }

    def _position_market_value(self) -> float:
        total = 0.0
        for position in self.positions:
            total += float(position.get("market_value") or 0.0)
        return total

    def _load_state(self) -> dict[str, Any]:
        path = self.config.state_path
        if not path.is_file():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def _day_state(self) -> dict[str, Any]:
        key = self.trading_day.isoformat()
        days = self._state.setdefault("days", {})
        if not isinstance(days, dict):
            days = {}
            self._state["days"] = days
        day = days.get(key)
        if not isinstance(day, dict):
            day = {}
            days[key] = day
        return day

    def _save_state(self) -> None:
        path = self.config.state_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self._state, indent=2), encoding="utf-8")
