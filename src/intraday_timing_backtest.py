"""2-week intraday entry/exit timing study vs current 09:35 / 15:45 schedule.

Uses hourly bars + daily BUY/SELL signals. Tests open-spike fade and open-dip buy rules.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, time, timezone
from enum import Enum
from pathlib import Path
from typing import Callable
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf

from src.portfolio_backtester import _prepare_ticker_frame, build_ai_score_frames
from src.settings import load_settings
from src.data_loader import load_price_data_batch
from src.macro_loader import load_macro_data

ET = ZoneInfo("America/New_York")
DEFAULT_OUTPUT_DIR = Path("logs/intraday_timing_2w")
INITIAL_CASH = 100_000.0
CALENDAR_DAYS = 14
MAX_TICKERS = 35
RTH_COST = 0.001


class EntryMode(str, Enum):
    FIXED_HOUR = "fixed_hour"
    DIP_FROM_OPEN = "dip_from_open"
    FADE_OPEN_SPIKE = "fade_open_spike"
    COMBO_SMART = "combo_smart"


@dataclass(frozen=True)
class TimingPolicy:
    policy_id: str
    label_ko: str
    entry_mode: EntryMode
    entry_hour: int = 10
    entry_minute: int = 0
    dip_pct_from_open: float = 0.008
    spike_skip_pct: float = 0.01
    exit_hour: int = 15
    exit_minute: int = 45
    fallback_entry_hour: int = 11
    fallback_entry_minute: int = 0


TIMING_POLICIES: tuple[TimingPolicy, ...] = (
    TimingPolicy(
        policy_id="1_current_0935_1545",
        label_ko="현재 스케줄 (09:35 매수 · 15:45 청산)",
        entry_mode=EntryMode.FIXED_HOUR,
        entry_hour=9,
        entry_minute=35,
    ),
    TimingPolicy(
        policy_id="2_entry_1100",
        label_ko="11:00 매수 (장 초반 변동성 회피)",
        entry_mode=EntryMode.FIXED_HOUR,
        entry_hour=11,
        entry_minute=0,
    ),
    TimingPolicy(
        policy_id="3_entry_1400",
        label_ko="14:00 매수 (오후 진입)",
        entry_mode=EntryMode.FIXED_HOUR,
        entry_hour=14,
        entry_minute=0,
    ),
    TimingPolicy(
        policy_id="4_dip_buy_1030",
        label_ko="급락 후 매수 (시초 대비 -0.8% 이상 ↓ 시 10:30)",
        entry_mode=EntryMode.DIP_FROM_OPEN,
        entry_hour=10,
        entry_minute=30,
        dip_pct_from_open=0.008,
    ),
    TimingPolicy(
        policy_id="5_fade_spike",
        label_ko="급등 스킵 → 11:00 재진입 (09:35 +1%↑면 패스)",
        entry_mode=EntryMode.FADE_OPEN_SPIKE,
        entry_hour=9,
        entry_minute=35,
        spike_skip_pct=0.01,
        fallback_entry_hour=11,
        fallback_entry_minute=0,
    ),
    TimingPolicy(
        policy_id="6_combo_smart",
        label_ko="복합 (급등 스킵 + 급락 매수)",
        entry_mode=EntryMode.COMBO_SMART,
        dip_pct_from_open=0.008,
        spike_skip_pct=0.01,
    ),
)


@dataclass
class TimingSimResult:
    policy_id: str
    label_ko: str
    initial_cash: float
    final_equity: float
    total_return_pct: float
    alpha_vs_baseline_pp: float | None
    trades: int
    buy_events: int
    skipped_spike: int
    skipped_no_dip: int
    avg_entry_improvement_bps: float | None


def _download_hourly(ticker: str, period: str = "60d") -> pd.DataFrame:
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
    df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]
    ts_col = "datetime" if "datetime" in df.columns else "date"
    df["timestamp"] = pd.to_datetime(df[ts_col], utc=True).dt.tz_convert(ET)
    return df[["timestamp", "open", "high", "low", "close", "volume"]].sort_values("timestamp")


def _bar_at(hourly: pd.DataFrame, day: datetime.date, hour: int, minute: int) -> pd.Series | None:
    target = datetime.combine(day, time(hour, minute), tzinfo=ET)
    hour_start = pd.Timestamp(target).floor("h")
    hour_end = hour_start + pd.Timedelta(hours=1)
    mask = (hourly["timestamp"] >= hour_start) & (hourly["timestamp"] < hour_end)
    rows = hourly.loc[mask]
    if rows.empty:
        subset = hourly[hourly["timestamp"] <= hour_end]
        return subset.iloc[-1] if not subset.empty else None
    return rows.iloc[-1]


def _session_open_price(hourly: pd.DataFrame, day: datetime.date) -> float | None:
    bar = _bar_at(hourly, day, 9, 30)
    if bar is None:
        bar = _bar_at(hourly, day, 10, 0)
    if bar is None:
        return None
    return float(bar["open"])


def _prev_rth_close(hourly: pd.DataFrame, day: datetime.date) -> float | None:
    day_ts = pd.Timestamp(day, tz=ET)
    prior = hourly[hourly["timestamp"] < day_ts]
    if prior.empty:
        return None
    return float(prior.iloc[-1]["close"])


def _should_enter_combo(
    policy: TimingPolicy,
    hourly: pd.DataFrame,
    day: datetime.date,
) -> tuple[bool, float | None, str]:
    open_px = _session_open_price(hourly, day)
    px_935 = _bar_at(hourly, day, 9, 35)
    px_1030 = _bar_at(hourly, day, 10, 30)
    px_1100 = _bar_at(hourly, day, 11, 0)
    prev_close = _prev_rth_close(hourly, day)

    if open_px is None or px_935 is None:
        return False, None, "no_data"

    price_935 = float(px_935["close"])
    if prev_close and prev_close > 0:
        surge = price_935 / prev_close - 1.0
        if surge >= policy.spike_skip_pct:
            if px_1100 is not None and float(px_1100["close"]) < price_935:
                return True, float(px_1100["close"]), "fade_spike_1100"
            return False, None, "spike_no_recovery"

    if px_1030 is not None and open_px > 0:
        dip = float(px_1030["close"]) / open_px - 1.0
        if dip <= -policy.dip_pct_from_open:
            return True, float(px_1030["close"]), "dip_1030"

    bar = _bar_at(hourly, day, policy.entry_hour, policy.entry_minute)
    if bar is not None:
        return True, float(bar["close"]), "default_entry"
    return False, None, "no_entry_bar"


def _resolve_entry(
    policy: TimingPolicy,
    hourly: pd.DataFrame,
    day: datetime.date,
) -> tuple[bool, float | None, str]:
    if policy.entry_mode == EntryMode.FIXED_HOUR:
        bar = _bar_at(hourly, day, policy.entry_hour, policy.entry_minute)
        if bar is None:
            return False, None, "no_bar"
        return True, float(bar["close"]), "fixed"

    if policy.entry_mode == EntryMode.DIP_FROM_OPEN:
        open_px = _session_open_price(hourly, day)
        bar = _bar_at(hourly, day, policy.entry_hour, policy.entry_minute)
        if open_px is None or bar is None or open_px <= 0:
            return False, None, "no_data"
        dip = float(bar["close"]) / open_px - 1.0
        if dip <= -policy.dip_pct_from_open:
            return True, float(bar["close"]), "dip"
        return False, None, "no_dip"

    if policy.entry_mode == EntryMode.FADE_OPEN_SPIKE:
        prev_close = _prev_rth_close(hourly, day)
        bar_935 = _bar_at(hourly, day, 9, 35)
        if bar_935 is None:
            return False, None, "no_bar"
        price_935 = float(bar_935["close"])
        if prev_close and prev_close > 0 and price_935 / prev_close - 1.0 >= policy.spike_skip_pct:
            bar_fb = _bar_at(hourly, day, policy.fallback_entry_hour, policy.fallback_entry_minute)
            if bar_fb is None:
                return False, None, "spike_no_fallback"
            if float(bar_fb["close"]) < price_935:
                return True, float(bar_fb["close"]), "fade_fallback"
            return False, None, "spike_still_high"
        return True, price_935, "normal_935"

    if policy.entry_mode == EntryMode.COMBO_SMART:
        return _should_enter_combo(policy, hourly, day)

    return False, None, "unknown"


def _simulate_timing_policy(
    policy: TimingPolicy,
    *,
    tickers: list[str],
    hourly_data: dict[str, pd.DataFrame],
    signal_maps: dict[str, pd.DataFrame],
    settings,
    trading_days: list[datetime.date],
    baseline_entry_prices: dict[tuple[str, datetime.date], float] | None = None,
) -> TimingSimResult:
    max_positions = int(settings.max_total_positions)
    max_orders = int(settings.max_orders_per_run)
    position_pct = float(settings.max_position_pct)
    max_order = float(settings.max_test_order_amount) or 10_000.0

    cash = INITIAL_CASH
    positions: dict[str, dict] = {}
    trades = 0
    buy_events = 0
    skipped_spike = 0
    skipped_no_dip = 0
    entry_improvements: list[float] = []

    for day in trading_days:
        signal_day = pd.Timestamp(day).normalize()
        orders_today = 0

        # --- exits at policy exit time ---
        for ticker in list(positions.keys()):
            sig = signal_maps.get(ticker)
            if sig is None or signal_day not in sig.index:
                continue
            if not bool(sig.loc[signal_day].get("sell_signal", False)):
                continue
            bar = _bar_at(hourly_data[ticker], day, policy.exit_hour, policy.exit_minute)
            if bar is None:
                continue
            fill = float(bar["close"])
            pos = positions.pop(ticker)
            cash += pos["qty"] * fill * (1 - RTH_COST)
            trades += 1

        portfolio_value = cash + sum(
            p["qty"] * p["last_price"] for p in positions.values()
        )

        if orders_today >= max_orders:
            continue

        candidates: list[tuple[float, str]] = []
        for ticker in tickers:
            if ticker in positions:
                continue
            sig = signal_maps.get(ticker)
            if sig is None or signal_day not in sig.index:
                continue
            row = sig.loc[signal_day]
            if not bool(row.get("buy_signal", False)):
                continue
            score = float(pd.to_numeric(row.get("ai_score"), errors="coerce") or 0.0)
            candidates.append((score, ticker))
        candidates.sort(reverse=True)

        slots = max_positions - len(positions)
        for _, ticker in candidates[:slots]:
            if orders_today >= max_orders:
                break
            hourly = hourly_data.get(ticker)
            if hourly is None:
                continue
            ok, fill, reason = _resolve_entry(policy, hourly, day)
            if not ok or fill is None or fill <= 0:
                if reason in {"spike_no_fallback", "spike_still_high", "spike_no_recovery"}:
                    skipped_spike += 1
                if reason == "no_dip":
                    skipped_no_dip += 1
                continue

            if baseline_entry_prices is not None:
                base_px = baseline_entry_prices.get((ticker, day))
                if base_px and base_px > 0:
                    entry_improvements.append((base_px - fill) / base_px * 10_000)

            target = min(max_order, portfolio_value * position_pct, cash)
            if target <= 100:
                continue
            qty = (target * (1 - RTH_COST)) / fill
            cash -= target
            positions[ticker] = {
                "qty": qty,
                "entry_price": fill,
                "last_price": fill,
            }
            orders_today += 1
            buy_events += 1
            trades += 1

        for ticker, pos in positions.items():
            bar = _bar_at(hourly_data[ticker], day, 15, 45)
            if bar is not None:
                pos["last_price"] = float(bar["close"])

    final_equity = cash + sum(p["qty"] * p["last_price"] for p in positions.values())
    ret_pct = (final_equity / INITIAL_CASH - 1.0) * 100.0
    avg_bps = (
        float(sum(entry_improvements) / len(entry_improvements))
        if entry_improvements
        else None
    )
    return TimingSimResult(
        policy_id=policy.policy_id,
        label_ko=policy.label_ko,
        initial_cash=INITIAL_CASH,
        final_equity=round(final_equity, 2),
        total_return_pct=round(ret_pct, 3),
        alpha_vs_baseline_pp=None,
        trades=trades,
        buy_events=buy_events,
        skipped_spike=skipped_spike,
        skipped_no_dip=skipped_no_dip,
        avg_entry_improvement_bps=round(avg_bps, 2) if avg_bps is not None else None,
    )


def _build_signal_maps(
    usable: list[str],
    daily_data: dict[str, pd.DataFrame],
    settings,
    *,
    use_ai_score: bool,
) -> dict[str, pd.DataFrame]:
    ai_frames = None
    if use_ai_score and settings.use_ai_score:
        vix = load_price_data_batch(["^VIX"], period="2y").get("^VIX")
        macro = load_macro_data(period="2y")
        ai_frames = build_ai_score_frames(
            {t: daily_data[t] for t in usable},
            vix_df=vix,
            macro_df=macro,
        )
    return {
        t: _prepare_ticker_frame(
            t,
            daily_data[t],
            ma_fast=settings.ma_fast,
            ma_slow=settings.ma_slow,
            rsi_buy_limit=settings.rsi_buy_limit,
            use_ai_score=use_ai_score and settings.use_ai_score,
            ai_score_buy_threshold=settings.ai_score_buy_threshold,
            ai_score_frame=(ai_frames or {}).get(t) if ai_frames else None,
            volume_filter_enabled=settings.volume_filter_enabled,
            volume_lookback_days=settings.volume_lookback_days,
            min_volume_ratio=settings.min_volume_ratio,
            volatility_filter_enabled=settings.volatility_filter_enabled,
            volatility_lookback_days=settings.volatility_lookback_days,
            max_volatility=settings.max_volatility,
        )
        .assign(date=lambda df: pd.to_datetime(df["date"]).dt.normalize())
        .set_index("date")
        for t in usable
    }


def build_intraday_timing_report(
    calendar_days: int = CALENDAR_DAYS,
    max_tickers: int = MAX_TICKERS,
    *,
    use_technical_signals: bool = True,
) -> dict:
    settings = load_settings()
    tickers = [str(t).upper() for t in settings.tickers[:max_tickers]]

    daily_data = load_price_data_batch(tickers, period="2y")
    usable = [t for t in tickers if t in daily_data and not daily_data[t].empty]

    signal_maps = _build_signal_maps(
        usable,
        daily_data,
        settings,
        use_ai_score=not use_technical_signals,
    )
    live_signal_maps = None
    if use_technical_signals:
        live_signal_maps = _build_signal_maps(
            usable, daily_data, settings, use_ai_score=True
        )

    hourly_data: dict[str, pd.DataFrame] = {}
    for t in usable:
        try:
            hourly_data[t] = _download_hourly(t, period="60d")
        except Exception as exc:
            print(f"Warning: hourly skip {t}: {exc}")

    usable = [t for t in usable if t in hourly_data]
    if not usable:
        raise ValueError("No tickers with hourly data")

    end_ts = min(hourly_data[t]["timestamp"].max() for t in usable)
    start_ts = end_ts - pd.Timedelta(days=calendar_days)
    trading_days = sorted(
        {
            ts.astimezone(ET).date()
            for t in usable
            for ts in hourly_data[t]["timestamp"]
            if start_ts <= ts <= end_ts and ts.astimezone(ET).weekday() < 5
        }
    )

    baseline_policy = TIMING_POLICIES[0]
    baseline_entries: dict[tuple[str, datetime.date], float] = {}
    for day in trading_days:
        signal_day = pd.Timestamp(day).normalize()
        for ticker in usable:
            sig = signal_maps.get(ticker)
            if sig is None or signal_day not in sig.index:
                continue
            if not bool(sig.loc[signal_day].get("buy_signal", False)):
                continue
            ok, fill, _ = _resolve_entry(baseline_policy, hourly_data[ticker], day)
            if ok and fill:
                baseline_entries[(ticker, day)] = fill

    results: list[TimingSimResult] = []
    for policy in TIMING_POLICIES:
        print(f"Simulating {policy.policy_id}...")
        baseline_prices = baseline_entries if policy.policy_id != baseline_policy.policy_id else None
        res = _simulate_timing_policy(
            policy,
            tickers=usable,
            hourly_data=hourly_data,
            signal_maps=signal_maps,
            settings=settings,
            trading_days=trading_days,
            baseline_entry_prices=baseline_prices,
        )
        results.append(res)

    baseline_ret = results[0].total_return_pct
    for i, res in enumerate(results):
        results[i] = TimingSimResult(
            **{
                **asdict(res),
                "alpha_vs_baseline_pp": round(res.total_return_pct - baseline_ret, 3)
                if res.policy_id != baseline_policy.policy_id
                else 0.0,
            }
        )

    signal_day_stats = _signal_day_price_stats(
        usable, hourly_data, signal_maps, trading_days, baseline_entries
    )

    live_buy_days = 0
    if live_signal_maps:
        for day in trading_days:
            sd = pd.Timestamp(day).normalize()
            for t in usable:
                sig = live_signal_maps.get(t)
                if sig is not None and sd in sig.index and bool(sig.loc[sd].get("buy_signal", False)):
                    live_buy_days += 1

    signal_mode = (
        "technical_ma_rsi (AI filter off — timing edge only)"
        if use_technical_signals
        else "live_full (AI + filters)"
    )

    results_dicts = [asdict(r) for r in results]
    recommendations = derive_timing_recommendations(results_dicts)

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "period_days": calendar_days,
        "period_start": str(trading_days[0]) if trading_days else None,
        "period_end": str(trading_days[-1]) if trading_days else None,
        "tickers_used": len(usable),
        "trading_days": len(trading_days),
        "signal_mode": signal_mode,
        "live_ai_buy_signal_ticker_days": live_buy_days,
        "current_schedule": "Mon-Fri 09:35 buy / 15:45 exit (config/scheduler_config.json)",
        "results": results_dicts,
        "recommendations": recommendations,
        "signal_day_edge": signal_day_stats,
        "notes": [
            "Hourly bars (yfinance); simplified fills at bar close.",
            "Timing study uses technical BUY when use_technical_signals=True.",
            f"Live AI-filtered buy signals in window: {live_buy_days} ticker-days.",
            f"Subset of {max_tickers} tickers for hourly download speed.",
        ],
    }


def _signal_day_price_stats(
    tickers: list[str],
    hourly_data: dict[str, pd.DataFrame],
    signal_maps: dict[str, pd.DataFrame],
    trading_days: list[datetime.date],
    baseline_entries: dict[tuple[str, datetime.date], float],
) -> dict:
    """Average entry price improvement on signal days (buy at alt times vs 09:35)."""
    rows: list[dict] = []
    for day in trading_days:
        signal_day = pd.Timestamp(day).normalize()
        for ticker in tickers:
            if (ticker, day) not in baseline_entries:
                continue
            h = hourly_data[ticker]
            p935 = baseline_entries[(ticker, day)]
            p1100_bar = _bar_at(h, day, 11, 0)
            p1400_bar = _bar_at(h, day, 14, 0)
            if p1100_bar is None or p1400_bar is None:
                continue
            p1100 = float(p1100_bar["close"])
            p1400 = float(p1400_bar["close"])
            rows.append(
                {
                    "ticker": ticker,
                    "day": str(day),
                    "vs_1100_bps": (p935 - p1100) / p935 * 10_000,
                    "vs_1400_bps": (p935 - p1400) / p935 * 10_000,
                }
            )
    if not rows:
        return {}
    df = pd.DataFrame(rows)
    return {
        "signal_buy_days": len(df),
        "mean_bps_0935_vs_1100": round(float(df["vs_1100_bps"].mean()), 2),
        "mean_bps_0935_vs_1400": round(float(df["vs_1400_bps"].mean()), 2),
        "pct_1100_cheaper": round(float((df["vs_1100_bps"] > 0).mean()) * 100, 1),
        "pct_1400_cheaper": round(float((df["vs_1400_bps"] > 0).mean()) * 100, 1),
        "interpretation_ko": (
            "양수 bps = 09:35보다 해당 시각이 더 싸서 매수 유리"
        ),
    }


def derive_timing_recommendations(results: list[dict]) -> dict:
    """Pick best policy vs current 09:35/15:45 baseline."""
    baseline_id = "1_current_0935_1545"
    baseline = next((r for r in results if r["policy_id"] == baseline_id), None)
    if not baseline:
        return {"verdict_ko": "baseline 정책 없음", "recommended_policy": None}

    ranked = sorted(results, key=lambda r: r["total_return_pct"], reverse=True)
    best = ranked[0]
    delta_pp = round(best["total_return_pct"] - baseline["total_return_pct"], 3)
    min_adopt_pp = 0.5

    if best["policy_id"] == baseline_id:
        verdict = "현재 09:35/15:45 스케줄 유지 — 대안 정책이 수익 우위 없음"
    elif delta_pp < min_adopt_pp:
        verdict = (
            f"현재 스케줄 유지 — 최선 대안({best['policy_id']}) 개선 {delta_pp:+.2f}pp "
            f"< 채택 기준 {min_adopt_pp}pp"
        )
    else:
        verdict = f"paper trial 검토: {best['policy_id']} ({best['label_ko']}) +{delta_pp:.2f}pp"

    return {
        "baseline_policy": baseline_id,
        "baseline_return_pct": baseline["total_return_pct"],
        "best_policy": best["policy_id"],
        "best_return_pct": best["total_return_pct"],
        "delta_vs_baseline_pp": delta_pp,
        "min_adopt_pp": min_adopt_pp,
        "recommended_policy": best["policy_id"] if delta_pp >= min_adopt_pp else baseline_id,
        "verdict_ko": verdict,
    }


def write_intraday_timing_artifacts(
    report: dict,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "latest_summary.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    pd.DataFrame(report["results"]).to_csv(output_dir / "comparison.csv", index=False)
    return path


def run_intraday_timing_2w() -> dict:
    report = build_intraday_timing_report()
    write_intraday_timing_artifacts(report)
    return report


def main() -> None:
    report = run_intraday_timing_2w()
    df = pd.DataFrame(report["results"])
    pd.set_option("display.width", 240)
    print("\n=== Intraday timing 2-week study ===")
    print(f"Period: {report['period_start']} → {report['period_end']} ({report['trading_days']} days)")
    print(f"Signal mode: {report.get('signal_mode')}")
    print(f"Live AI buy signal ticker-days in window: {report.get('live_ai_buy_signal_ticker_days')}")
    print(
        df[
            [
                "policy_id",
                "total_return_pct",
                "alpha_vs_baseline_pp",
                "trades",
                "buy_events",
                "skipped_spike",
                "skipped_no_dip",
                "avg_entry_improvement_bps",
            ]
        ].to_string(index=False)
    )
    edge = report.get("signal_day_edge") or {}
    if edge:
        print("\nSignal-day entry edge (vs 09:35):")
        print(f"  buy signal days: {edge.get('signal_buy_days')}")
        print(f"  11:00 cheaper: {edge.get('pct_1100_cheaper')}% avg {edge.get('mean_bps_0935_vs_1100')} bps")
        print(f"  14:00 cheaper: {edge.get('pct_1400_cheaper')}% avg {edge.get('mean_bps_0935_vs_1400')} bps")
    rec = report.get("recommendations") or {}
    print("\nVerdict:", rec.get("verdict_ko", "—"))
    print(f"\nSaved: {DEFAULT_OUTPUT_DIR / 'latest_summary.json'}")


if __name__ == "__main__":
    main()
