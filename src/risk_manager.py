from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import ORDER_LOG_PATH
from src.settings import load_settings


@dataclass
class RiskDecision:
    allowed: bool
    reason: str
    target_amount: float = 0.0


def _margin_borrowing_enabled(settings: Any) -> bool:
    return bool(getattr(settings, "margin_leverage_paper_enabled", False)) and float(
        getattr(settings, "leverage_factor", 1.0)
    ) > 1.0


@dataclass
class ExitDecision:
    should_exit: bool
    reason: str


def check_buy_allowed(
    signal: str,
    cash: float,
    current_positions_count: int,
    *,
    portfolio_value: float | None = None,
    ticker: str | None = None,
    position_mult: float = 1.0,
    cash_buffer_mult: float = 1.0,
    settings: Any | None = None,
) -> RiskDecision:
    if settings is None:
        settings = load_settings()

    if signal != "BUY":
        return RiskDecision(False, f"signal is {signal}")

    if current_positions_count >= settings.max_total_positions:
        return RiskDecision(False, "max total positions reached")

    if cash <= 0 and not _margin_borrowing_enabled(settings):
        return RiskDecision(False, "cash is zero or negative")

    equity_base = portfolio_value if portfolio_value is not None and portfolio_value > 0 else cash
    if equity_base <= 0:
        return RiskDecision(False, "portfolio value is zero or negative")

    position_pct = float(settings.max_position_pct) * max(1.0, float(position_mult))
    if ticker:
        from src.instrument_meta import adjust_position_cap_for_instrument

        position_pct = adjust_position_cap_for_instrument(position_pct, ticker)

    from src.position_sizing import max_deployable_cash

    target_amount = equity_base * position_pct
    if _margin_borrowing_enabled(settings):
        deployable = target_amount
    else:
        deployable = max_deployable_cash(
            cash,
            equity_base,
            settings,
            cash_buffer_mult=cash_buffer_mult,
        )
    target_amount = min(target_amount, deployable)

    if target_amount <= 0:
        return RiskDecision(False, "target amount is zero or negative")

    return RiskDecision(True, "buy allowed", target_amount)


def check_additional_buy_allowed(
    signal: str,
    cash: float,
    portfolio_value: float,
    current_position_value: float,
    *,
    ticker: str | None = None,
    position_mult: float = 1.0,
    cash_buffer_mult: float = 1.0,
    settings: Any | None = None,
) -> RiskDecision:
    if settings is None:
        settings = load_settings()

    if signal != "BUY":
        return RiskDecision(False, f"signal is {signal}")

    if cash <= 0 and not _margin_borrowing_enabled(settings):
        return RiskDecision(False, "cash is zero or negative")

    if portfolio_value <= 0:
        return RiskDecision(False, "portfolio value is zero or negative")

    position_pct = float(settings.max_position_pct) * max(1.0, float(position_mult))
    if ticker:
        from src.instrument_meta import adjust_position_cap_for_instrument

        position_pct = adjust_position_cap_for_instrument(position_pct, ticker)
    target_position_value = portfolio_value * position_pct
    remaining_to_target = target_position_value - max(current_position_value, 0.0)

    if remaining_to_target <= 0:
        return RiskDecision(False, "position target allocation reached")

    from src.position_sizing import max_deployable_cash

    if _margin_borrowing_enabled(settings):
        deployable = remaining_to_target
    else:
        deployable = max_deployable_cash(
            cash,
            portfolio_value,
            settings,
            cash_buffer_mult=cash_buffer_mult,
        )
    target_amount = min(deployable, remaining_to_target)
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
    *,
    portfolio_value: float | None = None,
    settings: Any | None = None,
) -> RiskDecision:
    if settings is None:
        settings = load_settings()

    cooldown_days = int(getattr(settings, "buy_cooldown_days", 0))
    if cooldown_days > 0 and ticker.upper() in recent_buy_symbols:
        return RiskDecision(
            False,
            f"buy cooldown active ({cooldown_days}d)",
            0.0,
        )

    from src.position_sizing import daily_order_budget

    daily_limit = daily_order_budget(
        float(portfolio_value or 0.0),
        settings,
    )
    if daily_limit > 0:
        remaining = daily_limit - submitted_notional_today
        if remaining <= 0:
            return RiskDecision(False, "daily order amount limit reached", 0.0)

        if order_amount > remaining:
            return RiskDecision(
                True,
                f"daily order amount capped (remaining=${remaining:.2f})",
                remaining,
            )

    return RiskDecision(True, "buy safety limits passed", order_amount)


def apply_portfolio_exposure_limits(
    ticker: str,
    order_amount: float,
    cash: float,
    portfolio_value: float,
    buying_power: float,
    current_gross_exposure: float,
    current_position_value: float = 0.0,
    *,
    cash_buffer_mult: float = 1.0,
    settings: Any | None = None,
) -> RiskDecision:
    if settings is None:
        settings = load_settings()

    if order_amount <= 0:
        return RiskDecision(False, "target amount is zero or negative", 0.0)

    if portfolio_value <= 0:
        return RiskDecision(False, "portfolio value is zero or negative", 0.0)

    if buying_power < order_amount:
        return RiskDecision(
            False,
            f"buying power exceeded (required=${order_amount:.2f}, available=${buying_power:.2f})",
            0.0,
        )

    max_gross_exposure = portfolio_value * float(getattr(settings, "max_gross_exposure_pct", 1.0))
    projected_gross_exposure = current_gross_exposure + order_amount
    if projected_gross_exposure > max_gross_exposure:
        return RiskDecision(
            False,
            f"gross exposure limit exceeded (projected=${projected_gross_exposure:.2f}, max=${max_gross_exposure:.2f})",
            0.0,
        )

    from src.position_sizing import effective_min_cash_buffer_pct

    if not _margin_borrowing_enabled(settings):
        min_cash_buffer = portfolio_value * effective_min_cash_buffer_pct(
            settings, cash_buffer_mult
        )
        projected_cash = cash - order_amount
        if projected_cash < min_cash_buffer:
            allowed_amount = max(0.0, cash - min_cash_buffer)
            if allowed_amount <= 0:
                return RiskDecision(
                    False,
                    f"cash buffer breached (projected=${projected_cash:.2f}, min=${min_cash_buffer:.2f})",
                    0.0,
                )
            return RiskDecision(
                True,
                f"cash buffer capped order (min=${min_cash_buffer:.2f})",
                allowed_amount,
            )

    max_single_name_loss = portfolio_value * float(getattr(settings, "max_single_name_loss_pct", 0.02))
    stop_loss_pct = float(getattr(settings, "stop_loss_pct", 0.0))
    projected_position_value = max(current_position_value, 0.0) + order_amount
    projected_single_name_loss = projected_position_value * stop_loss_pct
    if projected_single_name_loss > max_single_name_loss:
        if stop_loss_pct <= 0:
            return RiskDecision(
                False,
                f"single-name max loss exceeded for {ticker}",
                0.0,
            )
        max_position_value = max_single_name_loss / stop_loss_pct
        allowed_amount = max(
            0.0,
            max_position_value - max(current_position_value, 0.0),
        )
        if allowed_amount > 0:
            return RiskDecision(
                True,
                (
                    f"single-name max loss capped order for {ticker} "
                    f"(max_position=${max_position_value:.2f})"
                ),
                min(order_amount, allowed_amount),
            )
        return RiskDecision(
            False,
            f"single-name max loss exceeded for {ticker} (projected=${projected_single_name_loss:.2f}, max=${max_single_name_loss:.2f})",
            0.0,
        )

    return RiskDecision(True, "portfolio exposure limits passed", order_amount)


def apply_effective_leverage_exposure_limits(
    ticker: str,
    order_amount: float,
    portfolio_value: float,
    positions_by_symbol: dict[str, dict],
    *,
    settings: Any | None = None,
) -> RiskDecision:
    """Cap sum(market_value * |leverage_multiple|) including the proposed buy."""
    if settings is None:
        settings = load_settings()

    if order_amount <= 0:
        return RiskDecision(False, "target amount is zero or negative", 0.0)

    if portfolio_value <= 0:
        return RiskDecision(False, "portfolio value is zero or negative", 0.0)

    from src.instrument_meta import current_effective_leverage_exposure, get_instrument

    current_effective = current_effective_leverage_exposure(positions_by_symbol)
    multiple = get_instrument(ticker).abs_multiple
    projected = current_effective + (order_amount * multiple)
    max_effective = portfolio_value * float(
        getattr(settings, "max_effective_leverage_exposure_pct", 1.25)
    )
    if projected > max_effective:
        return RiskDecision(
            False,
            (
                "effective leverage exposure limit exceeded "
                f"(projected=${projected:.2f}, max=${max_effective:.2f}, "
                f"multiple={multiple:.1f})"
            ),
            0.0,
        )

    return RiskDecision(True, "effective leverage exposure ok", order_amount)


def _build_crowding_snapshot(
    df: pd.DataFrame,
    lookback_days: int,
    ma_slow: int,
) -> dict[str, float] | None:
    if df is None or df.empty:
        return None

    close_col = "adj_close" if "adj_close" in df.columns else "close"
    if close_col not in df.columns:
        return None

    close_series = pd.to_numeric(df[close_col], errors="coerce").dropna()
    required_rows = max(lookback_days + 1, ma_slow)
    if len(close_series) < required_rows:
        return None

    momentum_return = close_series.pct_change(lookback_days).iloc[-1]
    ma_slow_value = close_series.rolling(ma_slow).mean().iloc[-1]
    close_value = close_series.iloc[-1]
    if pd.isna(momentum_return) or pd.isna(ma_slow_value) or ma_slow_value <= 0:
        return None

    trend_gap = (close_value / ma_slow_value) - 1.0
    return {
        "momentum_return": float(momentum_return),
        "trend_gap": float(trend_gap),
    }


def apply_factor_crowding_limits(
    ticker: str,
    open_symbols: set[str],
    ticker_data: dict[str, pd.DataFrame],
) -> RiskDecision:
    settings = load_settings()

    if not open_symbols:
        return RiskDecision(True, "no open positions to compare")

    lookback_days = int(getattr(settings, "crowding_lookback_days", 60))
    max_crowded_positions = int(getattr(settings, "crowding_max_positions", 2))
    momentum_threshold = float(getattr(settings, "crowding_momentum_threshold", 0.15))
    trend_gap_threshold = float(getattr(settings, "crowding_trend_gap_threshold", 0.05))
    ma_slow = int(getattr(settings, "ma_slow", 50))

    candidate_snapshot = _build_crowding_snapshot(
        ticker_data.get(ticker),
        lookback_days=lookback_days,
        ma_slow=ma_slow,
    )
    if candidate_snapshot is None:
        return RiskDecision(True, f"insufficient data for {ticker} (skipped crowding check)")

    candidate_has_momentum = candidate_snapshot["momentum_return"] >= momentum_threshold
    candidate_has_trend = candidate_snapshot["trend_gap"] >= trend_gap_threshold
    if not candidate_has_momentum and not candidate_has_trend:
        return RiskDecision(True, "candidate not crowding-sensitive")

    momentum_peers = 0
    trend_peers = 0
    for symbol in open_symbols:
        peer_snapshot = _build_crowding_snapshot(
            ticker_data.get(symbol),
            lookback_days=lookback_days,
            ma_slow=ma_slow,
        )
        if peer_snapshot is None:
            continue

        if candidate_has_momentum and peer_snapshot["momentum_return"] >= momentum_threshold:
            momentum_peers += 1
        if candidate_has_trend and peer_snapshot["trend_gap"] >= trend_gap_threshold:
            trend_peers += 1

    if candidate_has_momentum and momentum_peers >= max_crowded_positions:
        return RiskDecision(
            False,
            (
                f"momentum crowding limit reached "
                f"(peers={momentum_peers}, max={max_crowded_positions}, "
                f"candidate_return={candidate_snapshot['momentum_return']:.2%})"
            ),
            0.0,
        )

    if candidate_has_trend and trend_peers >= max_crowded_positions:
        return RiskDecision(
            False,
            (
                f"trend crowding limit reached "
                f"(peers={trend_peers}, max={max_crowded_positions}, "
                f"candidate_gap={candidate_snapshot['trend_gap']:.2%})"
            ),
            0.0,
        )

    return RiskDecision(
        True,
        (
            f"crowding check passed "
            f"(momentum_peers={momentum_peers}, trend_peers={trend_peers})"
        ),
    )


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
