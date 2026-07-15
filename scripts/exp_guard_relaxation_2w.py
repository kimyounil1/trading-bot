"""2-week guard-relaxation scenario comparison (sector / crowding / universe).

Runs portfolio backtest with ~90d warmup, then reports metrics for the last
14 calendar days only. Also replays audit sector/crowding skips for forward returns.

Usage:
  PYTHONPATH=. .venv/bin/python scripts/exp_guard_relaxation_2w.py

Outputs: logs/guard_scenario_2w/summary.csv + summary.json + audit_counterfactual.csv
"""

from __future__ import annotations

import copy
import json
import re
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pandas as pd

from src.data_loader import load_price_data_batch
from src.macro_loader import load_macro_data
from src.portfolio_backtest_settings import portfolio_backtest_kwargs
from src.portfolio_backtester import run_portfolio_backtest
from src.settings import StrategySettings, load_settings

OUTPUT_DIR = Path("logs/guard_scenario_2w")
CALENDAR_DAYS = 14
WARMUP_CALENDAR_DAYS = 90
INITIAL_CASH = 100_000.0
AUDIT_PATH = Path("logs/execution_audit.csv")

DIVERSIFY_TICKERS = [
    "UNP",
    "NEE",
    "CAT",
    "XOM",
    "LIN",
    "UPS",
    "SO",
    "DE",
    "FCX",
    "RTX",
]


@contextmanager
def _settings_patch(settings: StrategySettings):
    with patch("src.risk_manager.load_settings", return_value=settings):
        yield


def _report_window_from_spy(
    ticker_data: dict[str, pd.DataFrame],
) -> tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp]:
    spy = ticker_data.get("SPY")
    if spy is None or spy.empty:
        raise ValueError("SPY data required")
    dates = pd.to_datetime(spy["date"]).sort_values()
    report_end = pd.Timestamp(dates.iloc[-1])
    report_start = report_end - pd.Timedelta(days=CALENDAR_DAYS)
    trading = dates[dates >= report_start]
    if trading.empty:
        raise ValueError("No trading dates in report window")
    report_start = pd.Timestamp(trading.iloc[0])
    warmup_start = report_start - pd.Timedelta(days=WARMUP_CALENDAR_DAYS)
    warmup_trading = dates[dates >= warmup_start]
    if warmup_trading.empty:
        raise ValueError("No trading dates in warmup window")
    return pd.Timestamp(warmup_trading.iloc[0]), report_start, report_end


def _spy_return(ticker_data: dict[str, pd.DataFrame], start: pd.Timestamp, end: pd.Timestamp) -> float:
    spy = ticker_data["SPY"].copy()
    spy["date"] = pd.to_datetime(spy["date"])
    window = spy[(spy["date"] >= start) & (spy["date"] <= end)]
    if len(window) < 2:
        return float("nan")
    col = "adj_close" if "adj_close" in window.columns else "close"
    return float(window.iloc[-1][col]) / float(window.iloc[0][col]) - 1.0


def _window_metrics(equity_df: pd.DataFrame, report_start: pd.Timestamp, report_end: pd.Timestamp) -> dict[str, float]:
    eq = equity_df.copy()
    eq["date"] = pd.to_datetime(eq["date"])
    window = eq[(eq["date"] >= report_start) & (eq["date"] <= report_end)].copy()
    if window.empty or len(window) < 2:
        return {
            "return_pct": 0.0,
            "mdd_pct": 0.0,
            "sharpe": 0.0,
            "avg_invested_pct": 0.0,
            "avg_cash_pct": 100.0,
            "trading_days": float(len(window)),
        }
    start_eq = float(window.iloc[0]["equity"])
    end_eq = float(window.iloc[-1]["equity"])
    ret = end_eq / start_eq - 1.0 if start_eq > 0 else 0.0
    window["daily_return"] = window["equity"].pct_change().fillna(0.0)
    window["running_max"] = window["equity"].cummax()
    window["drawdown"] = window["equity"] / window["running_max"] - 1.0
    mdd = float(window["drawdown"].min())
    std = float(window["daily_return"].std())
    sharpe = float(window["daily_return"].mean() / std * (252 ** 0.5)) if std > 1e-10 else 0.0
    avg_inv = float((window["positions_value"] / window["equity"]).mean())
    avg_cash = float((window["cash"] / window["equity"]).mean())
    return {
        "return_pct": round(ret * 100, 3),
        "mdd_pct": round(mdd * 100, 3),
        "sharpe": round(sharpe, 3),
        "avg_invested_pct": round(avg_inv * 100, 1),
        "avg_cash_pct": round(avg_cash * 100, 1),
        "trading_days": float(len(window)),
    }


def _run_scenario(
    label: str,
    *,
    base_settings: StrategySettings,
    base_kwargs: dict[str, Any],
    report_start: pd.Timestamp,
    report_end: pd.Timestamp,
    settings_overrides: dict[str, Any] | None = None,
    kw_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    settings = copy.deepcopy(base_settings)
    if settings_overrides:
        for key, value in settings_overrides.items():
            setattr(settings, key, value)

    kwargs = copy.copy(base_kwargs)
    kwargs["initial_cash"] = INITIAL_CASH
    kwargs["crowding_guard_enabled"] = bool(getattr(settings, "crowding_guard_enabled", False))
    kwargs["max_sector_positions"] = int(getattr(settings, "max_sector_positions", 2))
    if kw_overrides:
        kwargs.update(kw_overrides)

    with _settings_patch(settings):
        result, equity_df, trades_df = run_portfolio_backtest(**kwargs)

    wm = _window_metrics(equity_df, report_start, report_end)
    spy_ret = _spy_return(kwargs["ticker_data"], report_start, report_end)

    # Trades with exit in report window
    if not trades_df.empty:
        tdf = trades_df.copy()
        tdf["exit_date"] = pd.to_datetime(tdf["exit_date"])
        window_trades = tdf[
            (tdf["exit_date"] >= report_start) & (tdf["exit_date"] <= report_end)
        ]
        trades_n = int(len(window_trades))
        win_rate = float((window_trades["return_pct"] > 0).mean()) if trades_n else 0.0
    else:
        trades_n = 0
        win_rate = 0.0

    return {
        "scenario": label,
        "report_start": str(report_start.date()),
        "report_end": str(report_end.date()),
        "trading_days": int(wm["trading_days"]),
        "return_pct": wm["return_pct"],
        "spy_return_pct": round(spy_ret * 100, 3) if spy_ret == spy_ret else None,
        "alpha_vs_spy_pp": round((wm["return_pct"] / 100 - spy_ret) * 100, 3) if spy_ret == spy_ret else None,
        "mdd_pct": wm["mdd_pct"],
        "sharpe": wm["sharpe"],
        "trades_in_window": trades_n,
        "win_rate_pct": round(win_rate * 100, 1),
        "avg_invested_pct": wm["avg_invested_pct"],
        "avg_cash_pct": wm["avg_cash_pct"],
        "full_period_return_pct": round(result.total_return * 100, 3),
        "full_period_trades": int(result.trades),
        "max_sector_positions": int(getattr(settings, "max_sector_positions", 2)),
        "crowding_max_positions": int(getattr(settings, "crowding_max_positions", 2)),
        "universe_size": len(kwargs["ticker_data"]),
    }


def _forward_return(price_df: pd.DataFrame, event_date: pd.Timestamp, hold_days: int) -> float | None:
    df = price_df.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    event_date = pd.Timestamp(event_date).normalize()
    idx = df.index[df["date"] == event_date]
    if idx.empty:
        past = df[df["date"] <= event_date]
        if past.empty:
            return None
        start_i = int(past.index[-1])
    else:
        start_i = int(idx[0])
    end_i = start_i + hold_days
    if end_i >= len(df):
        return None
    col = "adj_close" if "adj_close" in df.columns else "close"
    p0 = float(df.iloc[start_i][col])
    p1 = float(df.iloc[end_i][col])
    if p0 <= 0:
        return None
    return p1 / p0 - 1.0


def _audit_counterfactual(
    report_start: pd.Timestamp,
    report_end: pd.Timestamp,
    ticker_data: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    if not AUDIT_PATH.is_file():
        return pd.DataFrame()

    audit = pd.read_csv(AUDIT_PATH)
    audit["timestamp"] = pd.to_datetime(audit["timestamp"], errors="coerce")
    audit = audit[
        (audit["timestamp"] >= report_start)
        & (audit["timestamp"] <= report_end + pd.Timedelta(days=1))
        & audit["event_type"].astype(str).str.contains("SKIP", na=False)
    ].copy()
    if audit.empty:
        return pd.DataFrame()

    def _block_type(reason: str) -> str | None:
        r = str(reason).lower()
        if "sector concentration" in r:
            return "sector"
        if "crowding" in r:
            return "crowding"
        if "rank ai gate blocked" in r:
            return "rank_gate"
        if r.startswith("signal is"):
            return "signal"
        return "other"

    audit["block_type"] = audit["reason"].map(_block_type)
    audit["event_date"] = audit["timestamp"].dt.normalize()
    audit["ticker"] = audit["ticker"].astype(str).str.upper()

    # One row per ticker-day-block_type (dedupe repeated runs)
    deduped = audit.drop_duplicates(subset=["event_date", "ticker", "block_type"])

    rows: list[dict[str, Any]] = []
    for hold in (5, 10):
        for _, row in deduped.iterrows():
            ticker = row["ticker"]
            if ticker not in ticker_data:
                continue
            fwd = _forward_return(ticker_data[ticker], row["event_date"], hold)
            if fwd is None:
                continue
            rows.append(
                {
                    "event_date": str(row["event_date"].date()),
                    "ticker": ticker,
                    "block_type": row["block_type"],
                    "hold_days": hold,
                    "forward_return_pct": round(fwd * 100, 3),
                    "reason_snippet": str(row.get("reason", ""))[:120],
                }
            )

    cf = pd.DataFrame(rows)
    if cf.empty:
        return cf

    summary = (
        cf.groupby(["block_type", "hold_days"])["forward_return_pct"]
        .agg(["count", "mean", "median", "std"])
        .reset_index()
    )
    summary.columns = [
        "block_type",
        "hold_days",
        "events",
        "mean_return_pct",
        "median_return_pct",
        "std_return_pct",
    ]
    return summary


def main() -> None:
    base_settings = load_settings()
    static = [str(t).upper() for t in base_settings.tickers]
    diversified = list(dict.fromkeys([*static, *DIVERSIFY_TICKERS]))

    print(f"Loading price data for {len(diversified)} tickers (incl. diversify adds)...")
    tickers_to_load = list(dict.fromkeys([*diversified, "SPY", "^VIX"]))
    loaded = load_price_data_batch(tickers_to_load, period="2y")
    vix_df = loaded.get("^VIX")
    macro_df = load_macro_data(period="2y") if base_settings.use_ai_score else None
    rs_bench = loaded.get(base_settings.relative_strength_benchmark_ticker)

    full_data = {t: loaded[t] for t in static if t in loaded}
    diversified_data = {t: loaded[t] for t in diversified if t in loaded}

    warmup_start, report_start, report_end = _report_window_from_spy(loaded)
    print(
        f"Warmup from {warmup_start.date()} | "
        f"Report window {report_start.date()} → {report_end.date()}"
    )

    def base_kw(ticker_data: dict[str, pd.DataFrame]) -> dict[str, Any]:
        kw = portfolio_backtest_kwargs(
            base_settings,
            ticker_data=ticker_data,
            benchmark_df=loaded.get("SPY"),
            relative_strength_benchmark_df=rs_bench,
            vix_df=vix_df,
            macro_df=macro_df,
            initial_cash=INITIAL_CASH,
        )
        kw["evaluation_start_date"] = warmup_start
        kw["evaluation_end_date"] = report_end
        kw["crowding_guard_enabled"] = bool(getattr(base_settings, "crowding_guard_enabled", False))
        kw["max_sector_positions"] = int(getattr(base_settings, "max_sector_positions", 2))
        return kw

    scenarios = [
        ("1_baseline", {}, {}, full_data),
        ("2_sector_max_3", {"max_sector_positions": 3}, {}, full_data),
        ("3_crowding_max_3", {"crowding_max_positions": 3}, {}, full_data),
        ("4_sector3_crowding3", {"max_sector_positions": 3, "crowding_max_positions": 3}, {}, full_data),
        ("5_diversified_universe", {}, {}, diversified_data),
        ("6_sector3_diversified", {"max_sector_positions": 3}, {}, diversified_data),
        ("7_sector3_crowding3_diversified", {"max_sector_positions": 3, "crowding_max_positions": 3}, {}, diversified_data),
    ]

    rows: list[dict[str, Any]] = []
    for label, settings_ov, kw_ov, tdata in scenarios:
        print(f"Running {label}...")
        kw = base_kw(tdata)
        if kw_ov:
            kw.update(kw_ov)
        row = _run_scenario(
            label,
            base_settings=base_settings,
            base_kwargs=kw,
            report_start=report_start,
            report_end=report_end,
            settings_overrides=settings_ov or None,
            kw_overrides=kw_ov or None,
        )
        rows.append(row)
        print(
            f"  2w ret={row['return_pct']:+.2f}%  MDD={row['mdd_pct']:.2f}%  "
            f"trades={row['trades_in_window']}  invested={row['avg_invested_pct']:.0f}%  "
            f"(warmup trades total={row['full_period_trades']})"
        )

    df = pd.DataFrame(rows)
    cf = _audit_counterfactual(report_start, report_end, loaded)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUTPUT_DIR / "summary.csv"
    json_path = OUTPUT_DIR / "summary.json"
    cf_path = OUTPUT_DIR / "audit_counterfactual.csv"
    df.to_csv(csv_path, index=False)
    if not cf.empty:
        cf.to_csv(cf_path, index=False)

    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "report_calendar_days": CALENDAR_DAYS,
        "warmup_calendar_days": WARMUP_CALENDAR_DAYS,
        "initial_cash": INITIAL_CASH,
        "notes": [
            "Report metrics are for the last 14 calendar days only.",
            "Backtest includes 90d warmup so positions can exist entering the report window.",
            "Does NOT replay rank_ai_buy_gate percentile or LLM blocking.",
            "audit_counterfactual: hypothetical forward returns for blocked tickers (not portfolio PnL).",
        ],
        "scenarios": rows,
        "audit_counterfactual": cf.to_dict(orient="records") if not cf.empty else [],
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    pd.set_option("display.width", 240)
    print("\n=== 2-week report window (after 90d warmup) ===")
    print(
        df[
            [
                "scenario",
                "return_pct",
                "spy_return_pct",
                "alpha_vs_spy_pp",
                "mdd_pct",
                "sharpe",
                "trades_in_window",
                "avg_invested_pct",
                "full_period_trades",
            ]
        ].to_string(index=False)
    )
    if not cf.empty:
        print("\n=== Audit counterfactual (blocked tickers forward return) ===")
        print(cf.to_string(index=False))
    print(f"\nSaved: {csv_path}")
    if not cf.empty:
        print(f"Saved: {cf_path}")
    print(f"Saved: {json_path}")


if __name__ == "__main__":
    main()
