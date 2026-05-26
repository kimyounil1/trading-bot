from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from src.config import ORDER_LOG_PATH
from src.settings import load_settings


@dataclass
class RiskDecision:
    allowed: bool
    reason: str
    target_amount: float = 0.0


@dataclass
class ExitDecision:
    should_exit: bool
    reason: str


def check_buy_allowed(
    signal: str,
    cash: float,
    current_positions_count: int,
) -> RiskDecision:
    settings = load_settings()

    if signal != "BUY":
        return RiskDecision(False, f"signal is {signal}")

    if current_positions_count >= settings.max_total_positions:
        return RiskDecision(False, "max total positions reached")

    if cash <= 0:
        return RiskDecision(False, "cash is zero or negative")

    target_amount = cash * settings.max_position_pct

    if target_amount <= 0:
        return RiskDecision(False, "target amount is zero or negative")

    return RiskDecision(True, "buy allowed", target_amount)


def check_additional_buy_allowed(
    signal: str,
    cash: float,
    portfolio_value: float,
    current_position_value: float,
) -> RiskDecision:
    settings = load_settings()

    if signal != "BUY":
        return RiskDecision(False, f"signal is {signal}")

    if cash <= 0:
        return RiskDecision(False, "cash is zero or negative")

    if portfolio_value <= 0:
        return RiskDecision(False, "portfolio value is zero or negative")

    target_position_value = portfolio_value * settings.max_position_pct
    remaining_to_target = target_position_value - max(current_position_value, 0.0)

    if remaining_to_target <= 0:
        return RiskDecision(False, "position target allocation reached")

    target_amount = min(cash, remaining_to_target)
    if target_amount <= 0:
        return RiskDecision(False, "target amount is zero or negative")

    return RiskDecision(True, "add to existing position allowed", target_amount)


def _load_order_log(path: str | Path = ORDER_LOG_PATH) -> pd.DataFrame:
    log_path = Path(path)
    if not log_path.exists():
        return pd.DataFrame()

    try:
        return pd.read_csv(log_path)
    except Exception:
        return pd.DataFrame()


def _buy_order_rows(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "side" not in df.columns:
        return pd.DataFrame()

    rows = df.copy()
    side = rows["side"].fillna("").astype(str).str.upper()
    rows = rows[side.str.contains("BUY")]

    if "event" in rows.columns:
        event = rows["event"].fillna("").astype(str)
        rows = rows[event != "STATUS_CHECK"]

    if "notional" in rows.columns:
        rows["notional"] = pd.to_numeric(rows["notional"], errors="coerce").fillna(0.0)
        rows = rows[rows["notional"] > 0]

    if "timestamp" in rows.columns:
        rows["timestamp"] = pd.to_datetime(rows["timestamp"], errors="coerce")
        rows = rows.dropna(subset=["timestamp"])

    return rows


def get_today_buy_notional(now: datetime | None = None) -> float:
    now = now or datetime.now()
    rows = _buy_order_rows(_load_order_log())

    if rows.empty or "timestamp" not in rows.columns or "notional" not in rows.columns:
        return 0.0

    today_rows = rows[rows["timestamp"].dt.date == now.date()]
    return float(today_rows["notional"].sum())


def get_recent_buy_symbols(
    cooldown_days: int,
    now: datetime | None = None,
) -> set[str]:
    if cooldown_days <= 0:
        return set()

    now = now or datetime.now()
    rows = _buy_order_rows(_load_order_log())

    if rows.empty or "timestamp" not in rows.columns or "ticker" not in rows.columns:
        return set()

    cutoff = now - timedelta(days=cooldown_days)
    recent_rows = rows[rows["timestamp"] >= cutoff]
    return set(recent_rows["ticker"].dropna().astype(str).str.upper())


def apply_buy_safety_limits(
    ticker: str,
    order_amount: float,
    submitted_notional_today: float,
    recent_buy_symbols: set[str],
) -> RiskDecision:
    settings = load_settings()

    cooldown_days = int(getattr(settings, "buy_cooldown_days", 0))
    if cooldown_days > 0 and ticker.upper() in recent_buy_symbols:
        return RiskDecision(
            False,
            f"buy cooldown active ({cooldown_days}d)",
            0.0,
        )

    daily_limit = float(getattr(settings, "max_daily_order_amount", 0.0))
    if daily_limit > 0:
        remaining = daily_limit - submitted_notional_today
        if remaining <= 0:
            return RiskDecision(False, "daily order amount limit reached", 0.0)

        if order_amount > remaining:
            return RiskDecision(
                False,
                f"daily order amount limit would be exceeded (remaining=${remaining:.2f})",
                0.0,
            )

    return RiskDecision(True, "buy safety limits passed", order_amount)


def check_exit_allowed(
    signal: str,
    unrealized_plpc: float,
) -> ExitDecision:
    settings = load_settings()

    if unrealized_plpc <= -settings.stop_loss_pct:
        return ExitDecision(True, "stop loss triggered")

    if unrealized_plpc >= settings.take_profit_pct:
        return ExitDecision(True, "take profit triggered")

    if signal == "SELL":
        return ExitDecision(True, "strategy sell signal")

    return ExitDecision(False, "hold position")
