"""Live paper account P&L snapshot — Toss-style period returns and trade history."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import ORDER_LOG_PATH


@dataclass(frozen=True)
class PeriodPnl:
    label: str
    pnl_usd: float
    pnl_pct: float
    start_equity: float
    end_equity: float


@dataclass
class RealizedPnlSummary:
    total_usd: float
    today_usd: float
    week_usd: float
    month_usd: float
    by_ticker: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PortfolioPnlSnapshot:
    generated_at: str
    broker_provider: str
    currency: str
    total_equity: float
    cash: float
    invested_value: float
    buying_power: float
    today: PeriodPnl
    week: PeriodPnl
    month: PeriodPnl
    all_time: PeriodPnl
    unrealized_total_usd: float
    unrealized_total_pct: float
    realized: RealizedPnlSummary = field(default_factory=lambda: RealizedPnlSummary(0, 0, 0, 0))
    positions: list[dict[str, Any]] = field(default_factory=list)
    trades: list[dict[str, Any]] = field(default_factory=list)
    equity_curve: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for key in ("today", "week", "month", "all_time"):
            payload[key] = asdict(getattr(self, key))
        payload["realized"] = self.realized.to_dict()
        return payload


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _safe_pct(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _period_pnl(label: str, start_equity: float, end_equity: float) -> PeriodPnl:
    pnl_usd = end_equity - start_equity
    return PeriodPnl(
        label=label,
        pnl_usd=round(pnl_usd, 2),
        pnl_pct=round(_safe_pct(pnl_usd, start_equity) * 100.0, 2),
        start_equity=round(start_equity, 2),
        end_equity=round(end_equity, 2),
    )


def portfolio_history_to_frame(history: Any) -> pd.DataFrame:
    timestamps = list(getattr(history, "timestamp", None) or [])
    equity = list(getattr(history, "equity", None) or [])
    if not timestamps or not equity:
        return pd.DataFrame(columns=["date", "equity", "profit_loss", "profit_loss_pct"])

    frame = pd.DataFrame(
        {
            "date": pd.to_datetime(timestamps, unit="s", utc=True),
            "equity": pd.to_numeric(equity, errors="coerce"),
            "profit_loss": pd.to_numeric(
                list(getattr(history, "profit_loss", None) or [None] * len(timestamps)),
                errors="coerce",
            ),
            "profit_loss_pct": pd.to_numeric(
                list(getattr(history, "profit_loss_pct", None) or [None] * len(timestamps)),
                errors="coerce",
            ),
        }
    )
    return frame.dropna(subset=["equity"]).sort_values("date").reset_index(drop=True)


def _equity_at_or_before(frame: pd.DataFrame, cutoff: datetime) -> float | None:
    if frame.empty:
        return None
    ts = pd.Timestamp(cutoff)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")
    eligible = frame[(frame["date"] <= ts) & (frame["equity"] > 0)]
    if eligible.empty:
        positive = frame[frame["equity"] > 0]
        if positive.empty:
            return None
        return float(positive["equity"].iloc[0])
    return float(eligible["equity"].iloc[-1])


def _first_meaningful_equity(frame: pd.DataFrame, *, min_equity: float = 1.0) -> float | None:
    positive = frame[frame["equity"] >= min_equity]
    if positive.empty:
        return None
    return float(positive["equity"].iloc[0])


def _resolve_start_equity(*candidates: float | None, fallback: float) -> float:
    for value in candidates:
        if value is not None and value > 0:
            return float(value)
    return float(fallback)


def compute_period_pnls(
    *,
    current_equity: float,
    last_equity: float,
    history_1w: pd.DataFrame,
    history_1m: pd.DataFrame,
    history_all: pd.DataFrame,
    now: datetime | None = None,
) -> tuple[PeriodPnl, PeriodPnl, PeriodPnl, PeriodPnl]:
    now = now or datetime.now(timezone.utc)

    today = _period_pnl("오늘", float(last_equity), float(current_equity))

    week_start = _resolve_start_equity(
        _equity_at_or_before(history_1w, now - timedelta(days=7)),
        _first_meaningful_equity(history_1w),
        fallback=float(last_equity),
    )
    week = _period_pnl("1주", week_start, float(current_equity))

    month_start = _resolve_start_equity(
        _equity_at_or_before(history_1m, now - timedelta(days=30)),
        _first_meaningful_equity(history_1m),
        fallback=week_start,
    )
    month = _period_pnl("1개월", month_start, float(current_equity))

    all_start = _resolve_start_equity(
        _first_meaningful_equity(history_all),
        fallback=month_start,
    )
    all_time = _period_pnl("전체", all_start, float(current_equity))

    return today, week, month, all_time


def _normalize_side(side: str) -> str:
    text = str(side or "").upper()
    if "BUY" in text:
        return "BUY"
    if "SELL" in text:
        return "SELL"
    return text


def _trade_row_from_alpaca(order: dict[str, Any]) -> dict[str, Any]:
    qty = float(order.get("filled_qty") or 0.0)
    price = float(order.get("filled_avg_price") or 0.0)
    notional = round(qty * price, 2) if qty > 0 and price > 0 else 0.0
    ts = order.get("filled_at") or order.get("submitted_at") or ""
    side = _normalize_side(order.get("side", ""))
    return {
        "timestamp": str(ts),
        "ticker": str(order.get("symbol", "")).upper(),
        "side": side,
        "side_ko": "매수" if side == "BUY" else "매도",
        "qty": round(qty, 4),
        "price": round(price, 4),
        "notional": notional,
        "order_id": str(order.get("id", "")),
        "status": str(order.get("status_simple") or order.get("status", "")),
        "reason": "",
        "source": "alpaca",
    }


def load_filled_trades_from_csv(
    path: str | Path | None = None,
    *,
    limit: int | None = 200,
) -> list[dict[str, Any]]:
    path = Path(path or ORDER_LOG_PATH)
    if not path.is_file():
        return []

    try:
        frame = pd.read_csv(path)
    except (OSError, pd.errors.EmptyDataError, ValueError):
        return []

    if frame.empty:
        return []

    if "event" in frame.columns:
        filled = frame[frame["event"].astype(str).str.upper() == "STATUS_CHECK"].copy()
    else:
        filled = frame[frame.get("status", pd.Series(dtype=str)).astype(str).str.upper() == "FILLED"].copy()

    if filled.empty:
        return []

    rows: list[dict[str, Any]] = []
    iterable = filled if limit is None else filled.tail(limit)
    for _, row in iterable.iterrows():
        qty = pd.to_numeric(row.get("filled_qty"), errors="coerce")
        price = pd.to_numeric(row.get("filled_avg_price"), errors="coerce")
        if pd.isna(qty) or pd.isna(price) or float(qty) <= 0:
            continue
        side = _normalize_side(row.get("side", ""))
        notional = round(float(qty) * float(price), 2)
        rows.append(
            {
                "timestamp": str(row.get("timestamp", "")),
                "ticker": str(row.get("ticker", "")).upper(),
                "side": side,
                "side_ko": "매수" if side == "BUY" else "매도",
                "qty": round(float(qty), 4),
                "price": round(float(price), 4),
                "notional": notional,
                "order_id": str(row.get("order_id", "")),
                "status": "FILLED",
                "reason": str(row.get("reason", "") or ""),
                "source": "orders_csv",
            }
        )
    rows.sort(key=lambda item: str(item.get("timestamp", "")))
    return rows


def merge_trade_history(
    alpaca_trades: list[dict[str, Any]],
    csv_trades: list[dict[str, Any]],
    *,
    limit: int | None = 100,
) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for row in csv_trades + alpaca_trades:
        key = row.get("order_id") or f"{row.get('timestamp')}_{row.get('ticker')}_{row.get('side')}"
        if not key:
            continue
        existing = merged.get(str(key))
        if existing is None or str(row.get("timestamp", "")) >= str(existing.get("timestamp", "")):
            merged[str(key)] = row

    rows = list(merged.values())
    rows.sort(key=lambda item: str(item.get("timestamp", "")), reverse=True)
    if limit is not None:
        rows = rows[:limit]
    return rows


def _parse_trade_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = pd.to_datetime(value, utc=True)
        if pd.isna(parsed):
            return None
        return parsed.to_pydatetime()
    except (TypeError, ValueError):
        return None


def compute_fifo_realized_pnl(
    trades: list[dict[str, Any]],
    *,
    now: datetime | None = None,
) -> RealizedPnlSummary:
    """FIFO lot matching on merged fill history."""
    now = now or datetime.now(timezone.utc)
    ordered = sorted(trades, key=lambda item: str(item.get("timestamp", "")))
    lots: dict[str, list[list[float]]] = {}
    events: list[dict[str, Any]] = []
    realized_by_ticker: dict[str, float] = {}
    sell_counts: dict[str, int] = {}

    for trade in ordered:
        ticker = str(trade.get("ticker", "")).upper()
        side = _normalize_side(trade.get("side", ""))
        qty = float(trade.get("qty") or 0.0)
        price = float(trade.get("price") or 0.0)
        if not ticker or qty <= 0 or price <= 0 or side not in {"BUY", "SELL"}:
            continue

        if side == "BUY":
            lots.setdefault(ticker, []).append([qty, price])
            continue

        remaining = qty
        sell_counts[ticker] = sell_counts.get(ticker, 0) + 1
        while remaining > 1e-8:
            queue = lots.get(ticker) or []
            if not queue:
                break
            lot_qty, lot_price = queue[0]
            matched = min(remaining, lot_qty)
            realized = (price - lot_price) * matched
            ts = _parse_trade_timestamp(str(trade.get("timestamp", "")))
            events.append(
                {
                    "timestamp": str(trade.get("timestamp", "")),
                    "ticker": ticker,
                    "qty": round(matched, 4),
                    "sell_price": round(price, 4),
                    "cost_basis": round(lot_price, 4),
                    "realized_pl": round(realized, 2),
                    "return_pct": round(_safe_pct(price - lot_price, lot_price) * 100.0, 2),
                    "order_id": str(trade.get("order_id", "")),
                    "reason": str(trade.get("reason", "") or ""),
                }
            )
            realized_by_ticker[ticker] = realized_by_ticker.get(ticker, 0.0) + realized
            lot_qty -= matched
            remaining -= matched
            if lot_qty <= 1e-8:
                queue.pop(0)
            else:
                queue[0][0] = lot_qty

    def _sum_since(cutoff: datetime) -> float:
        total = 0.0
        for event in events:
            ts = _parse_trade_timestamp(str(event.get("timestamp", "")))
            if ts is not None and ts >= cutoff:
                total += float(event.get("realized_pl") or 0.0)
        return round(total, 2)

    day_start = now.astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    total = round(sum(float(event.get("realized_pl") or 0.0) for event in events), 2)
    by_ticker = [
        {
            "ticker": ticker,
            "realized_pl": round(amount, 2),
            "closed_trades": int(sell_counts.get(ticker, 0)),
        }
        for ticker, amount in sorted(
            realized_by_ticker.items(),
            key=lambda item: abs(item[1]),
            reverse=True,
        )
    ]
    recent_events = sorted(
        events,
        key=lambda item: str(item.get("timestamp", "")),
        reverse=True,
    )[:100]

    return RealizedPnlSummary(
        total_usd=total,
        today_usd=_sum_since(day_start),
        week_usd=_sum_since(now - timedelta(days=7)),
        month_usd=_sum_since(now - timedelta(days=30)),
        by_ticker=by_ticker,
        events=recent_events,
    )


def build_trade_history_for_fifo(
    *,
    broker_provider: str = "alpaca",
    closed_order_limit: int = 500,
) -> list[dict[str, Any]]:
    csv_trades = load_filled_trades_from_csv(limit=None)
    if str(broker_provider).lower() != "alpaca":
        return merge_trade_history([], csv_trades, limit=None)

    from src.alpaca_client import get_recent_closed_orders

    alpaca_orders = [
        _trade_row_from_alpaca(order)
        for order in get_recent_closed_orders(limit=closed_order_limit)
        if _normalize_side(order.get("side", "")) in {"BUY", "SELL"}
        and float(order.get("filled_qty") or 0.0) > 0
    ]
    return merge_trade_history(alpaca_orders, csv_trades, limit=None)


def format_positions(positions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    formatted: list[dict[str, Any]] = []
    for position in positions:
        symbol = str(position.get("symbol", "")).upper()
        qty = float(position.get("qty") or 0.0)
        market_value = float(position.get("market_value") or 0.0)
        cost_basis = float(position.get("cost_basis") or 0.0)
        unrealized = float(position.get("unrealized_pl") or 0.0)
        unrealized_pct = float(position.get("unrealized_plpc") or 0.0) * 100.0
        current_price = float(position.get("current_price") or 0.0)
        avg_cost = (cost_basis / qty) if qty > 0 else 0.0
        formatted.append(
            {
                "ticker": symbol,
                "qty": round(qty, 4),
                "current_price": round(current_price, 2),
                "avg_cost": round(avg_cost, 2),
                "market_value": round(market_value, 2),
                "cost_basis": round(cost_basis, 2),
                "unrealized_pl": round(unrealized, 2),
                "unrealized_plpc": round(unrealized_pct, 2),
            }
        )
    formatted.sort(key=lambda row: abs(row["market_value"]), reverse=True)
    return formatted


def fetch_alpaca_portfolio_histories() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    from alpaca.trading.requests import GetPortfolioHistoryRequest

    from src.alpaca_client import get_trading_client

    client = get_trading_client()
    h1w = portfolio_history_to_frame(
        client.get_portfolio_history(
            GetPortfolioHistoryRequest(period="1W", timeframe="1D", extended_hours=True)
        )
    )
    h1m = portfolio_history_to_frame(
        client.get_portfolio_history(
            GetPortfolioHistoryRequest(period="1M", timeframe="1D", extended_hours=True)
        )
    )
    hall = portfolio_history_to_frame(
        client.get_portfolio_history(
            GetPortfolioHistoryRequest(period="all", timeframe="1D", extended_hours=True)
        )
    )
    return h1w, h1m, hall


def build_portfolio_pnl_snapshot(
    *,
    broker_provider: str = "alpaca",
    closed_order_limit: int = 100,
    fifo_order_limit: int = 500,
) -> PortfolioPnlSnapshot:
    from src.alpaca_client import get_account_summary, get_positions_summary
    from src.brokers import broker_account_snapshot

    fifo_trades = build_trade_history_for_fifo(
        broker_provider=broker_provider,
        closed_order_limit=fifo_order_limit,
    )
    realized = compute_fifo_realized_pnl(fifo_trades)
    display_trades = sorted(
        fifo_trades,
        key=lambda item: str(item.get("timestamp", "")),
        reverse=True,
    )[:closed_order_limit]

    if str(broker_provider).lower() != "alpaca":
        account, positions = broker_account_snapshot(broker_provider)
        current_equity = float(account.get("portfolio_value") or 0.0)
        last_equity = float(account.get("last_equity") or current_equity)
        today, week, month, all_time = compute_period_pnls(
            current_equity=current_equity,
            last_equity=last_equity,
            history_1w=pd.DataFrame(),
            history_1m=pd.DataFrame(),
            history_all=pd.DataFrame(),
        )
        formatted_positions = format_positions(positions)
        unrealized_total = sum(row["unrealized_pl"] for row in formatted_positions)
        cost_total = sum(row["cost_basis"] for row in formatted_positions)
        return PortfolioPnlSnapshot(
            generated_at=_utc_now_iso(),
            broker_provider=broker_provider,
            currency=str(account.get("currency") or "USD"),
            total_equity=current_equity,
            cash=float(account.get("cash") or 0.0),
            invested_value=sum(row["market_value"] for row in formatted_positions),
            buying_power=float(account.get("buying_power") or 0.0),
            today=today,
            week=week,
            month=month,
            all_time=all_time,
            unrealized_total_usd=round(unrealized_total, 2),
            unrealized_total_pct=round(_safe_pct(unrealized_total, cost_total) * 100.0, 2),
            realized=realized,
            positions=formatted_positions,
            trades=display_trades,
            equity_curve=[],
        )

    account = get_account_summary()
    positions = get_positions_summary()
    h1w, h1m, hall = fetch_alpaca_portfolio_histories()

    current_equity = float(account.get("portfolio_value") or 0.0)
    last_equity = float(account.get("last_equity") or current_equity)
    today, week, month, all_time = compute_period_pnls(
        current_equity=current_equity,
        last_equity=last_equity,
        history_1w=h1w,
        history_1m=h1m,
        history_all=hall,
    )

    formatted_positions = format_positions(positions)
    unrealized_total = sum(row["unrealized_pl"] for row in formatted_positions)
    cost_total = sum(row["cost_basis"] for row in formatted_positions)

    curve_source = h1m if not h1m.empty else hall
    equity_curve = [
        {
            "date": row["date"].strftime("%Y-%m-%d"),
            "equity": round(float(row["equity"]), 2),
        }
        for _, row in curve_source.iterrows()
    ]

    return PortfolioPnlSnapshot(
        generated_at=_utc_now_iso(),
        broker_provider=broker_provider,
        currency=str(account.get("currency") or "USD"),
        total_equity=round(current_equity, 2),
        cash=round(float(account.get("cash") or 0.0), 2),
        invested_value=round(sum(row["market_value"] for row in formatted_positions), 2),
        buying_power=round(float(account.get("buying_power") or 0.0), 2),
        today=today,
        week=week,
        month=month,
        all_time=all_time,
        unrealized_total_usd=round(unrealized_total, 2),
        unrealized_total_pct=round(_safe_pct(unrealized_total, cost_total) * 100.0, 2),
        realized=realized,
        positions=formatted_positions,
        trades=display_trades,
        equity_curve=equity_curve,
    )


def write_portfolio_pnl_artifacts(
    snapshot: PortfolioPnlSnapshot,
    output_dir: str | Path = "logs/portfolio_pnl",
) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    latest = output_dir / "latest_summary.json"
    latest.write_text(
        json.dumps(snapshot.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    if snapshot.trades:
        pd.DataFrame(snapshot.trades).to_csv(output_dir / "recent_trades.csv", index=False)
    if snapshot.positions:
        pd.DataFrame(snapshot.positions).to_csv(output_dir / "open_positions.csv", index=False)
    if snapshot.equity_curve:
        pd.DataFrame(snapshot.equity_curve).to_csv(output_dir / "equity_curve.csv", index=False)
    if snapshot.realized.by_ticker:
        pd.DataFrame(snapshot.realized.by_ticker).to_csv(
            output_dir / "realized_by_ticker.csv",
            index=False,
        )
    if snapshot.realized.events:
        pd.DataFrame(snapshot.realized.events).to_csv(
            output_dir / "realized_events.csv",
            index=False,
        )
    return latest
