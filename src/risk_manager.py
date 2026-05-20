from dataclasses import dataclass

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
