"""Compare portfolio outcomes: daily-once vs hourly extended-hours execution.

Signals come from daily bars (same as live bot). Execution uses 1h OHLC:
- daily_once_rth: one run at 09:35 ET on weekdays (market fill)
- hourly_extended: every hour in enabled Alpaca sessions (limit in extended, market in RTH)
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import yfinance as yf

from src.portfolio_backtest_settings import portfolio_backtest_kwargs
from src.portfolio_backtester import _prepare_ticker_frame, build_ai_score_frames
from src.settings import load_settings
from src.data_loader import load_price_data_batch
from src.macro_loader import load_macro_data
from src.trading_session import orders_allowed_for_session, resolve_trading_session

ET = ZoneInfo("America/New_York")


@dataclass
class FrequencySimResult:
    policy: str
    initial_cash: float
    final_equity: float
    total_return: float
    max_drawdown: float
    sharpe_ratio: float
    trades: int
    run_count: int
    avg_invested_pct: float
    avg_cash_pct: float


def _download_hourly(ticker: str, period: str = "730d") -> pd.DataFrame:
    raw = yf.download(
        ticker,
        interval="1h",
        period=period,
        auto_adjust=True,
        progress=False,
        threads=False,
    )
    if raw.empty:
        raise ValueError(f"No hourly data for {ticker}")
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = [col[0] for col in raw.columns]
    df = raw.reset_index()
    df.columns = [str(col).lower().replace(" ", "_") for col in df.columns]
    ts_col = "datetime" if "datetime" in df.columns else "date"
    df["timestamp"] = pd.to_datetime(df[ts_col], utc=True).dt.tz_convert(ET)
    return df[["timestamp", "open", "high", "low", "close", "volume"]].sort_values("timestamp")


def _hourly_run_timestamps(start: pd.Timestamp, end: pd.Timestamp) -> list[datetime]:
    start_et = start.tz_convert(ET) if start.tzinfo else start.tz_localize(ET)
    end_et = end.tz_convert(ET) if end.tzinfo else end.tz_localize(ET)
    cursor = start_et.floor("h")
    stamps: list[datetime] = []
    while cursor <= end_et:
        stamps.append(cursor.to_pydatetime())
        cursor += timedelta(hours=1)
    return stamps


def _is_daily_once_run_hour(ts: datetime) -> bool:
    local = ts.astimezone(ET)
    return local.weekday() < 5 and local.hour == 10 and local.minute == 0


def _fix_signal_date(run_ts: datetime) -> pd.Timestamp:
    local = run_ts.astimezone(ET)
    session_date = pd.Timestamp(local.date())
    if local.hour < 9 or (local.hour == 9 and local.minute < 30):
        return (session_date - pd.offsets.BDay(1)).normalize()
    return session_date.normalize()


def _build_daily_signal_maps(
    ticker: str,
    daily_df: pd.DataFrame,
    settings,
    ai_score_frame: pd.DataFrame | None,
) -> pd.DataFrame:
    prepared = _prepare_ticker_frame(
        ticker,
        daily_df,
        ma_fast=settings.ma_fast,
        ma_slow=settings.ma_slow,
        rsi_buy_limit=settings.rsi_buy_limit,
        use_ai_score=settings.use_ai_score,
        ai_score_buy_threshold=settings.ai_score_buy_threshold,
        ai_score_frame=ai_score_frame,
        volume_filter_enabled=settings.volume_filter_enabled,
        volume_lookback_days=settings.volume_lookback_days,
        min_volume_ratio=settings.min_volume_ratio,
        volatility_filter_enabled=settings.volatility_filter_enabled,
        volatility_lookback_days=settings.volatility_lookback_days,
        max_volatility=settings.max_volatility,
    )
    prepared["date"] = pd.to_datetime(prepared["date"]).dt.normalize()
    return prepared.set_index("date")


def _price_at_or_before(hourly: pd.DataFrame, ts: datetime) -> float | None:
    subset = hourly[hourly["timestamp"] <= ts]
    if subset.empty:
        return None
    return float(subset.iloc[-1]["close"])


def _hour_bar(hourly: pd.DataFrame, ts: datetime) -> pd.Series | None:
    hour_start = pd.Timestamp(ts).tz_convert(ET).floor("h")
    hour_end = hour_start + timedelta(hours=1)
    mask = (hourly["timestamp"] >= hour_start) & (hourly["timestamp"] < hour_end)
    rows = hourly.loc[mask]
    if rows.empty:
        subset = hourly[hourly["timestamp"] <= hour_end]
        if subset.empty:
            return None
        row = subset.iloc[-1]
        return row
    return rows.iloc[-1]


def _simulate_policy(
    *,
    policy: str,
    tickers: list[str],
    daily_data: dict[str, pd.DataFrame],
    hourly_data: dict[str, pd.DataFrame],
    signal_maps: dict[str, pd.DataFrame],
    settings,
    initial_cash: float,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> FrequencySimResult:
    max_positions = int(settings.max_total_positions)
    max_order = float(settings.max_test_order_amount)
    max_orders_per_day = int(settings.max_orders_per_run)
    position_pct = float(settings.max_position_pct)
    extended_slippage = float(settings.extended_hours_limit_slippage_pct)
    rth_cost = 0.001
    ext_cost = 0.0015

    cash = initial_cash
    positions: dict[str, dict] = {}
    trades = 0
    runs = 0
    equity_samples: list[float] = []
    invested_samples: list[float] = []
    orders_today = 0
    current_day = None

    for run_ts in _hourly_run_timestamps(start, end):
        session_state = resolve_trading_session(run_ts, broker_provider="alpaca")
        allowed = orders_allowed_for_session(
            session_state,
            extended_hours_enabled=bool(settings.extended_hours_enabled),
            enabled_trading_sessions=list(settings.enabled_trading_sessions),
        )
        if policy == "daily_once_rth":
            if not _is_daily_once_run_hour(run_ts):
                continue
            if not session_state.is_regular_session:
                continue
        else:
            if not allowed:
                continue

        runs += 1
        local_day = run_ts.astimezone(ET).date()
        if current_day != local_day:
            current_day = local_day
            orders_today = 0

        signal_day = _fix_signal_date(run_ts)
        portfolio_value = cash + sum(
            pos["qty"] * (_price_at_or_before(hourly_data[t], run_ts) or pos["last_price"])
            for t, pos in positions.items()
            if t in hourly_data
        )

        # --- exits ---
        for ticker in list(positions.keys()):
            sig = signal_maps.get(ticker)
            if sig is None or signal_day not in sig.index:
                continue
            row = sig.loc[signal_day]
            if not bool(row.get("sell_signal", False)):
                continue
            bar = _hour_bar(hourly_data[ticker], run_ts)
            if bar is None:
                continue
            pos = positions[ticker]
            if session_state.is_regular_session:
                fill = float(bar["close"])
                cost = rth_cost
            else:
                limit = pos["last_price"] * (1 - extended_slippage)
                if float(bar["high"]) < limit:
                    continue
                fill = limit
                cost = ext_cost
            gross = pos["qty"] * fill
            cash += gross * (1 - cost)
            del positions[ticker]
            trades += 1

        portfolio_value = cash + sum(
            pos["qty"] * (_price_at_or_before(hourly_data[t], run_ts) or pos["last_price"])
            for t, pos in positions.items()
            if t in hourly_data
        )

        # --- entries ---
        if orders_today >= max_orders_per_day:
            pass
        else:
            candidates: list[tuple[float, str, float]] = []
            for ticker in tickers:
                if ticker in positions:
                    continue
                sig = signal_maps.get(ticker)
                if sig is None or signal_day not in sig.index:
                    continue
                row = sig.loc[signal_day]
                if not bool(row.get("buy_signal", False)):
                    continue
                ref = float(row["close"])
                score = float(pd.to_numeric(row.get("ai_score"), errors="coerce") or 0.0)
                candidates.append((score, ticker, ref))
            candidates.sort(reverse=True)

            slots = max_positions - len(positions)
            for _, ticker, ref in candidates[:slots]:
                if orders_today >= max_orders_per_day:
                    break
                target = min(max_order, portfolio_value * position_pct)
                if target <= 0 or cash < target * 0.5:
                    continue
                notional = min(target, cash)
                bar = _hour_bar(hourly_data[ticker], run_ts)
                if bar is None:
                    continue
                if session_state.is_regular_session:
                    fill = float(bar["close"])
                    cost = rth_cost
                else:
                    limit = ref * (1 + extended_slippage)
                    if float(bar["low"]) > limit:
                        continue
                    fill = limit
                    cost = ext_cost
                qty = notional / fill
                cash -= notional
                positions[ticker] = {
                    "qty": qty,
                    "entry_price": fill,
                    "last_price": fill,
                    "cost_basis": notional,
                }
                trades += 1
                orders_today += 1

        mark = cash
        for ticker, pos in positions.items():
            px = _price_at_or_before(hourly_data[ticker], run_ts) or pos["last_price"]
            pos["last_price"] = px
            mark += pos["qty"] * px
        equity_samples.append(mark)
        invested_samples.append(1 - (cash / mark if mark > 0 else 1))

    equity = pd.Series(equity_samples, dtype=float)
    if equity.empty:
        raise ValueError(f"No equity samples generated for policy={policy}")
    returns = equity.pct_change().fillna(0.0)
    sharpe = 0.0
    if returns.std() > 0:
        sharpe = float(returns.mean() / returns.std() * np.sqrt(252 * 6))
    drawdown = (equity / equity.cummax()) - 1.0
    return FrequencySimResult(
        policy=policy,
        initial_cash=initial_cash,
        final_equity=float(equity.iloc[-1]),
        total_return=float(equity.iloc[-1] / initial_cash - 1),
        max_drawdown=float(drawdown.min()),
        sharpe_ratio=sharpe,
        trades=trades,
        run_count=runs,
        avg_invested_pct=float(np.mean(invested_samples)),
        avg_cash_pct=float(1 - np.mean(invested_samples)),
    )


from src.portfolio_backtester import run_portfolio_backtest


def compare_run_frequencies(
    *,
    tickers: list[str] | None = None,
    initial_cash: float = 100_000.0,
    hourly_period: str = "730d",
    output_dir: Path | None = None,
) -> dict:
    settings = load_settings()
    universe = tickers or [
        "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "AVGO", "AMD", "TSM",
        "JPM", "UNH", "XOM", "LLY", "COST", "SPY",
    ]

    daily_data = load_price_data_batch(universe, period="2y")
    hourly_data: dict[str, pd.DataFrame] = {}
    for ticker in universe:
        try:
            hourly_data[ticker] = _download_hourly(ticker, period=hourly_period)
        except Exception as exc:
            print(f"skip hourly {ticker}: {exc}")

    usable = [t for t in universe if t in hourly_data and t in daily_data]
    if len(usable) < 5:
        raise ValueError("Not enough tickers with hourly+daily data")

    ai_frames = None
    if settings.use_ai_score:
        try:
            vix_df = load_price_data_batch(["^VIX"], period="2y").get("^VIX")
            macro_df = load_macro_data(period="2y")
            ai_frames = build_ai_score_frames(
                {t: daily_data[t] for t in usable},
                vix_df=vix_df,
                spy_df=daily_data.get("SPY"),
                macro_df=macro_df,
            )
        except Exception as exc:
            print(f"AI scores unavailable, continuing without: {exc}")
            ai_frames = {}

    signal_maps = {
        t: _build_daily_signal_maps(t, daily_data[t], settings, (ai_frames or {}).get(t))
        for t in usable
    }

    start = max(hourly_data[t]["timestamp"].min() for t in usable)
    end = min(hourly_data[t]["timestamp"].max() for t in usable)
    start = max(start, pd.Timestamp.now(tz=ET) - pd.Timedelta(days=365))

    daily_once = _simulate_policy(
        policy="daily_once_rth",
        tickers=usable,
        daily_data=daily_data,
        hourly_data=hourly_data,
        signal_maps=signal_maps,
        settings=settings,
        initial_cash=initial_cash,
        start=start,
        end=end,
    )
    hourly_ext = _simulate_policy(
        policy="hourly_extended",
        tickers=usable,
        daily_data=daily_data,
        hourly_data=hourly_data,
        signal_maps=signal_maps,
        settings=settings,
        initial_cash=initial_cash,
        start=start,
        end=end,
    )

    kwargs = portfolio_backtest_kwargs(
        settings,
        ticker_data={t: daily_data[t] for t in usable},
        benchmark_df=daily_data.get("SPY"),
        vix_df=load_price_data_batch(["^VIX"], period="2y").get("^VIX") if settings.use_ai_score else None,
        macro_df=load_macro_data(period="2y") if settings.use_ai_score else None,
        ai_score_frames=ai_frames,
        initial_cash=initial_cash,
        evaluation_start_date=start.tz_convert(None).normalize(),
        evaluation_end_date=end.tz_convert(None).normalize(),
    )
    baseline, _, _ = run_portfolio_backtest(**kwargs)

    payload = {
        "period_start": str(start.date()),
        "period_end": str(end.date()),
        "tickers": usable,
        "initial_cash": initial_cash,
        "results": {
            "daily_close_backtest": {
                "policy": "daily_close_backtest",
                "total_return": baseline.total_return,
                "max_drawdown": baseline.max_drawdown,
                "sharpe_ratio": baseline.sharpe_ratio,
                "trades": baseline.trades,
                "final_equity": baseline.final_equity,
            },
            "daily_once_rth": asdict(daily_once),
            "hourly_extended": asdict(hourly_ext),
        },
        "winner_return": max(
            [
                ("daily_once_rth", daily_once.total_return),
                ("hourly_extended", hourly_ext.total_return),
                ("daily_close_backtest", baseline.total_return),
            ],
            key=lambda item: item[1],
        )[0],
    }

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "run_frequency_comparison.json").write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare daily vs hourly run frequency")
    parser.add_argument("--output-dir", default="logs/run_frequency")
    args = parser.parse_args()
    payload = compare_run_frequencies(output_dir=Path(args.output_dir))
    results = payload["results"]
    print("=" * 72)
    print(f"Period: {payload['period_start']} -> {payload['period_end']}")
    print(f"Tickers: {len(payload['tickers'])}")
    print("-" * 72)
    for name, row in results.items():
        print(
            f"{name:22s}  return={row['total_return']*100:7.2f}%  "
            f"mdd={row['max_drawdown']*100:7.2f}%  "
            f"sharpe={row.get('sharpe_ratio', 0):5.2f}  "
            f"trades={row['trades']:4d}"
            + (
                f"  runs={row['run_count']:5d}  avg_cash={row['avg_cash_pct']*100:5.1f}%"
                if "run_count" in row
                else ""
            )
        )
    print("-" * 72)
    print(f"Best total return: {payload['winner_return']}")
    print(f"Saved: {Path(args.output_dir) / 'run_frequency_comparison.json'}")


if __name__ == "__main__":
    main()
