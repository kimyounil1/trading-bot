"""Portfolio-percent order sizing with optional conviction scaling."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ConvictionAdjustments:
    position_mult: float = 1.0
    cash_buffer_mult: float = 1.0
    label: str = "neutral"


def conviction_adjustments(
    settings: Any,
    ai_score: float | None,
) -> ConvictionAdjustments:
    if not getattr(settings, "conviction_sizing_enabled", False):
        return ConvictionAdjustments()

    if ai_score is None or not getattr(settings, "use_ai_score", False):
        return ConvictionAdjustments()

    threshold = float(getattr(settings, "ai_score_buy_threshold", 0.55))
    if ai_score < threshold:
        return ConvictionAdjustments()

    strong = float(getattr(settings, "conviction_ai_score_strong", 0.65))
    span = max(strong - threshold, 1e-6)
    strength = min(1.0, max(0.0, (float(ai_score) - threshold) / span))

    pos_max = float(getattr(settings, "conviction_position_mult_max", 1.25))
    buffer_min = float(getattr(settings, "conviction_cash_buffer_mult_min", 0.4))

    position_mult = 1.0 + strength * (pos_max - 1.0)
    cash_buffer_mult = 1.0 - strength * (1.0 - buffer_min)
    return ConvictionAdjustments(
        position_mult=position_mult,
        cash_buffer_mult=cash_buffer_mult,
        label=f"conviction x{position_mult:.2f}, cash_buffer x{cash_buffer_mult:.2f}",
    )


def effective_min_cash_buffer_pct(settings: Any, cash_buffer_mult: float = 1.0) -> float:
    base = float(getattr(settings, "min_cash_buffer_pct", 0.05))
    mult = max(0.0, min(1.0, float(cash_buffer_mult)))
    return max(0.0, min(0.99, base * mult))


def max_deployable_cash(
    cash: float,
    portfolio_value: float,
    settings: Any,
    *,
    cash_buffer_mult: float = 1.0,
) -> float:
    if cash <= 0 or portfolio_value <= 0:
        return 0.0
    buffer = portfolio_value * effective_min_cash_buffer_pct(settings, cash_buffer_mult)
    return max(0.0, cash - buffer)


def daily_order_budget(portfolio_value: float, settings: Any) -> float:
    daily_pct = float(getattr(settings, "max_daily_order_pct", 0.0))
    if daily_pct > 0 and portfolio_value > 0:
        return portfolio_value * daily_pct
    return float(getattr(settings, "max_daily_order_amount", 0.0))


def cap_single_order_amount(
    order_amount: float,
    portfolio_value: float,
    settings: Any,
) -> float:
    if order_amount <= 0 or portfolio_value <= 0:
        return 0.0

    capped = order_amount
    single_pct = float(getattr(settings, "max_single_order_pct", 1.0))
    if 0 < single_pct < 1.0:
        capped = min(capped, portfolio_value * single_pct)

    legacy_cap = float(getattr(settings, "max_test_order_amount", 0.0))
    if legacy_cap > 0:
        capped = min(capped, legacy_cap)

    return max(0.0, capped)


def finalize_order_amount(
    target_amount: float,
    *,
    cash: float,
    portfolio_value: float,
    settings: Any,
    cash_buffer_mult: float = 1.0,
) -> float:
    deployable = max_deployable_cash(
        cash,
        portfolio_value,
        settings,
        cash_buffer_mult=cash_buffer_mult,
    )
    amount = min(max(0.0, target_amount), deployable)
    return cap_single_order_amount(amount, portfolio_value, settings)
