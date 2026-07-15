#!/usr/bin/env python3
"""US crash-follow morning bounce exit vs hold — dollar PnL test.

Scenario A (미장 대응):
  - Prior day QQQ close-to-close <= -2%
  - If holding positions, sell 50% when price touches +0.5% vs prior close
    between 09:30-10:30 ET; remainder at day close.
  - Baseline: hold 100% from prior close to next day close.

Uses hourly bars + daily signals subset; compares on overlapping crash days.
"""

from __future__ import annotations

import json
from datetime import datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf

from src.data_loader import load_price_data_batch
from src.settings import load_settings

ET = ZoneInfo("America/New_York")
OUT = Path("logs/crash_bounce_exit_us")
INITIAL = 100_000.0
QQQ_DROP = -0.02
BOUNCE_SELL = 0.005
PARTIAL = 0.50
MAX_TICKERS = 25


def _hourly(ticker: str, period: str = "730d") -> pd.DataFrame:
    raw = yf.download(ticker, interval="1h", period=period, auto_adjust=True, progress=False, threads=False)
    if raw.empty:
        raise ValueError(ticker)
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = [c[0] for c in raw.columns]
    df = raw.reset_index()
    df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]
    ts_col = "datetime" if "datetime" in df.columns else "date"
    df["timestamp"] = pd.to_datetime(df[ts_col], utc=True).dt.tz_convert(ET)
    return df.sort_values("timestamp")


def _price_at(h: pd.DataFrame, day, hour: int, minute: int = 0) -> float | None:
    from datetime import datetime as dt

    target = dt.combine(day, time(hour, minute), tzinfo=ET)
    hs = pd.Timestamp(target).floor("h")
    he = hs + pd.Timedelta(hours=1)
    rows = h[(h["timestamp"] >= hs) & (h["timestamp"] < he)]
    if rows.empty:
        sub = h[h["timestamp"] <= he]
        return float(sub.iloc[-1]["close"]) if not sub.empty else None
    return float(rows.iloc[-1]["close"])


def _qqq_crash_days(qqq_daily: pd.DataFrame, drop_thresh: float) -> set:
    q = qqq_daily.copy()
    q["date"] = pd.to_datetime(q["date"]).dt.date
    q["ret"] = q["close"].astype(float).pct_change()
    crash = q[q["ret"] <= drop_thresh]["date"].tolist()
    return set(crash)


def _next_trading_day_after(crash_day, all_days: list) -> object | None:
    for d in all_days:
        if d > crash_day:
            return d
    return None


def simulate_ticker(
    ticker: str,
    hourly: pd.DataFrame,
    daily: pd.DataFrame,
    crash_days: set,
    notional_per_name: float,
) -> list[dict]:
    d = daily.copy()
    d["date"] = pd.to_datetime(d["date"]).dt.date
    closes = d.set_index("date")["close"].astype(float)
    days = sorted(closes.index)

    rows = []
    for crash_day in sorted(crash_days):
        trade_day = _next_trading_day_after(crash_day, days)
        if trade_day is None or trade_day not in closes.index:
            continue
        prev_close = float(closes[crash_day]) if crash_day in closes.index else None
        if prev_close is None or prev_close <= 0:
            # use day before trade
            idx = days.index(trade_day)
            if idx < 1:
                continue
            prev_close = float(closes[days[idx - 1]])
        day_close = float(closes[trade_day])

        bounce_prices = [
            p
            for p in (
                _price_at(hourly, trade_day, 9, 35),
                _price_at(hourly, trade_day, 10, 0),
                _price_at(hourly, trade_day, 10, 30),
            )
            if p is not None
        ]
        best_bounce = max(bounce_prices) if bounce_prices else None
        bounce_hit = best_bounce is not None and best_bounce / prev_close - 1 >= BOUNCE_SELL

        # Assume held 1 unit from prev_close (crash eve)
        qty = notional_per_name / prev_close
        pnl_hold = qty * (day_close - prev_close)

        if bounce_hit and best_bounce is not None:
            sell_qty = qty * PARTIAL
            keep_qty = qty * (1 - PARTIAL)
            pnl_a = sell_qty * (best_bounce - prev_close) + keep_qty * (day_close - prev_close)
            sell_px = best_bounce
        else:
            pnl_a = pnl_hold
            sell_px = None

        rows.append(
            {
                "ticker": ticker,
                "crash_day": str(crash_day),
                "trade_day": str(trade_day),
                "notional": round(notional_per_name, 2),
                "prev_close": round(prev_close, 4),
                "bounce_hit": bounce_hit,
                "bounce_pct": round((best_bounce / prev_close - 1) * 100, 2) if best_bounce else None,
                "sell_px": round(sell_px, 4) if sell_px else None,
                "day_close": round(day_close, 4),
                "pnl_hold_usd": round(pnl_hold, 2),
                "pnl_scenario_a_usd": round(pnl_a, 2),
                "edge_usd": round(pnl_a - pnl_hold, 2),
            }
        )
    return rows


def main() -> None:
    settings = load_settings()
    tickers = [str(t).upper() for t in settings.tickers[:MAX_TICKERS]]
    daily_all = load_price_data_batch(tickers + ["QQQ"], period="2y")
    qqq_daily = daily_all["QQQ"]
    crash_days = _qqq_crash_days(qqq_daily, QQQ_DROP)

    # Equal weight per name when "in portfolio" on crash follow day
    notional = INITIAL / max(len(tickers), 1)

    all_rows: list[dict] = []
    for t in tickers:
        if t not in daily_all:
            continue
        try:
            h = _hourly(t, period="730d")
        except Exception as exc:
            print(f"skip hourly {t}: {exc}")
            continue
        all_rows.extend(
            simulate_ticker(t, h, daily_all[t], crash_days, notional)
        )

    df = pd.DataFrame(all_rows)
    if df.empty:
        print("No crash-follow events")
        return

    total_hold = float(df["pnl_hold_usd"].sum())
    total_a = float(df["pnl_scenario_a_usd"].sum())
    edge = total_a - total_hold
    events = len(df)
    bounce_events = int(df["bounce_hit"].sum())
    wins = int((df["edge_usd"] > 0).sum())

    by_day = (
        df.groupby("trade_day")[["pnl_hold_usd", "pnl_scenario_a_usd", "edge_usd"]]
        .sum()
        .reset_index()
    )

    summary = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "initial_portfolio_usd": INITIAL,
        "tickers_simulated": len(tickers),
        "notional_per_ticker_usd": round(notional, 2),
        "qqq_drop_threshold_pct": QQQ_DROP * 100,
        "bounce_sell_threshold_pct": BOUNCE_SELL * 100,
        "partial_sell_fraction": PARTIAL,
        "crash_days_qqq": len(crash_days),
        "ticker_event_rows": events,
        "bounce_hit_rows": bounce_events,
        "total_pnl_hold_usd": round(total_hold, 2),
        "total_pnl_scenario_a_usd": round(total_a, 2),
        "total_edge_usd": round(edge, 2),
        "edge_pct_of_initial": round(edge / INITIAL * 100, 3),
        "scenario_a_beats_hold_pct": round(wins / events * 100, 1),
        "interpretation_ko": (
            f"QQQ 전일 -2% 다음날, 종목당 ${notional:,.0f} 보유 가정. "
            f"반등 +0.5% 시 50% 매도 vs 전량 종가 보유."
        ),
    }

    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / "events.csv", index=False)
    by_day.to_csv(OUT / "by_trade_day.csv", index=False)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print("=" * 72)
    print("미장 Crash-Bounce Exit 테스트 (QQQ 전일 -2% 다음날)")
    print("=" * 72)
    print(f"가정: 포트 ${INITIAL:,.0f} / {len(tickers)}종목 균등 → 종목당 ${notional:,.0f}")
    print(f"QQQ 폭락일 수 (2y): {len(crash_days)} | 시뮬 이벤트: {events} | 반등 터치: {bounce_events}")
    print("-" * 72)
    print(f"전량 보유 PnL 합계:     ${total_hold:+,.2f}")
    print(f"시나리오 A PnL 합계:    ${total_a:+,.2f}")
    print(f"차이 (A - 보유):       ${edge:+,.2f}  ({edge/INITIAL*100:+.2f}% of ${INITIAL:,.0f})")
    print(f"A가 나은 이벤트:       {wins}/{events} ({wins/events*100:.1f}%)")
    print("-" * 72)
    print("거래일별 합계 (상위 edge):")
    top = by_day.sort_values("edge_usd", ascending=False).head(8)
    for _, r in top.iterrows():
        print(
            f"  {r['trade_day']}  hold ${r['pnl_hold_usd']:+,.0f}  "
            f"A ${r['pnl_scenario_a_usd']:+,.0f}  edge ${r['edge_usd']:+,.0f}"
        )
    print(f"\nSaved: {OUT / 'summary.json'}")


if __name__ == "__main__":
    main()
