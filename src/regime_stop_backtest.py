"""Backtest regime-adaptive stops vs fixed baselines across market windows."""

from __future__ import annotations

import copy
import json
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pandas as pd

from src.data_loader import load_price_data_batch
from src.guard_regime_study import REGIME_WINDOWS, warmup_start_for_report
from src.macro_loader import load_macro_data
from src.portfolio_backtest_settings import portfolio_backtest_kwargs
from src.portfolio_backtester import run_portfolio_backtest
from src.regime_stop_policy import (
    BEAR_ONLY_TIGHT_STOP_PROFILE,
    CONSERVATIVE_REGIME_STOP_PROFILE,
    STANDARD_REGIME_STOP_PROFILE,
    RegimeStopProfile,
)
from src.settings import StrategySettings, load_settings

DEFAULT_OUTPUT_DIR = Path("logs/regime_stop_backtest")
POLICY_PATH = Path("data/research/regime_stop_backtest_policy.json")
INITIAL_CASH = 100_000.0
WARMUP_CALENDAR_DAYS = 90

STOP_SCENARIOS: tuple[tuple[str, dict[str, Any]], ...] = (
    (
        "1_baseline_current",
        {
            "stop_loss_pct": 0.05,
            "trailing_stop_pct": 0.20,
        },
    ),
    (
        "2_no_stops",
        {"stop_loss_pct": 0.0, "trailing_stop_pct": 0.0},
    ),
    (
        "3_stop_only_5pct",
        {"stop_loss_pct": 0.05, "trailing_stop_pct": 0.0},
    ),
    (
        "4_trail_only_20pct",
        {"stop_loss_pct": 0.0, "trailing_stop_pct": 0.20},
    ),
    (
        "5_tight_fixed_3_10",
        {"stop_loss_pct": 0.03, "trailing_stop_pct": 0.10},
    ),
    (
        "6_wide_fixed_8_25",
        {"stop_loss_pct": 0.08, "trailing_stop_pct": 0.25},
    ),
    (
        "7_regime_adaptive_standard",
        {
            "regime_adaptive_stop_enabled": True,
            "regime_stop_profile": STANDARD_REGIME_STOP_PROFILE,
        },
    ),
    (
        "8_regime_adaptive_conservative",
        {
            "regime_adaptive_stop_enabled": True,
            "regime_stop_profile": CONSERVATIVE_REGIME_STOP_PROFILE,
        },
    ),
)

# Follow-up: lower trailing (10–12%) + bear-only SPY 20d<0 → 3% stop
FOLLOWUP_STOP_SCENARIOS: tuple[tuple[str, dict[str, Any]], ...] = (
    (
        "1_baseline_current",
        {"stop_loss_pct": 0.05, "trailing_stop_pct": 0.20},
    ),
    (
        "9_stop5_trail10",
        {"stop_loss_pct": 0.05, "trailing_stop_pct": 0.10},
    ),
    (
        "10_stop5_trail12",
        {"stop_loss_pct": 0.05, "trailing_stop_pct": 0.12},
    ),
    (
        "11_bear_only_spy20d_tight3",
        {
            "regime_adaptive_stop_enabled": True,
            "regime_stop_profile": BEAR_ONLY_TIGHT_STOP_PROFILE,
        },
    ),
)


@contextmanager
def _settings_patch(settings: StrategySettings):
    with patch("src.risk_manager.load_settings", return_value=settings):
        yield


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _spy_return(spy_df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> float | None:
    df = spy_df.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    col = "adj_close" if "adj_close" in df.columns else "close"
    w = df[(df["date"] >= start.normalize()) & (df["date"] <= end.normalize())]
    prices = pd.to_numeric(w[col], errors="coerce").dropna()
    if len(prices) < 2:
        return None
    return float(prices.iloc[-1] / prices.iloc[0] - 1.0)


def _window_metrics(
    equity_df: pd.DataFrame,
    report_start: pd.Timestamp | None,
    report_end: pd.Timestamp | None,
) -> dict[str, float]:
    eq = equity_df.copy()
    eq["date"] = pd.to_datetime(eq["date"])
    if report_start is not None and report_end is not None:
        eq = eq[(eq["date"] >= report_start) & (eq["date"] <= report_end)]
    if eq.empty or len(eq) < 2:
        return {
            "return_pct": 0.0,
            "mdd_pct": 0.0,
            "sharpe": 0.0,
            "trading_days": float(len(eq)),
        }
    ret = float(eq.iloc[-1]["equity"]) / float(eq.iloc[0]["equity"]) - 1.0
    eq["daily_return"] = eq["equity"].pct_change().fillna(0.0)
    eq["running_max"] = eq["equity"].cummax()
    eq["drawdown"] = eq["equity"] / eq["running_max"] - 1.0
    mdd = float(eq["drawdown"].min())
    std = float(eq["daily_return"].std())
    sharpe = float(eq["daily_return"].mean() / std * (252**0.5)) if std > 1e-10 else 0.0
    return {
        "return_pct": round(ret * 100, 3),
        "mdd_pct": round(mdd * 100, 3),
        "sharpe": round(sharpe, 3),
        "trading_days": float(len(eq)),
    }


def _exit_mix(trades_df: pd.DataFrame) -> dict[str, int]:
    if trades_df.empty or "exit_reason" not in trades_df.columns:
        return {}
    return trades_df["exit_reason"].value_counts().to_dict()


def _run_one(
    scenario_id: str,
    overrides: dict[str, Any],
    *,
    base_settings: StrategySettings,
    base_kwargs: dict[str, Any],
    report_start: pd.Timestamp | None,
    report_end: pd.Timestamp | None,
    spy_df: pd.DataFrame,
) -> dict[str, Any]:
    settings = copy.deepcopy(base_settings)
    kwargs = copy.copy(base_kwargs)
    kwargs["initial_cash"] = INITIAL_CASH
    kwargs["crowding_guard_enabled"] = bool(getattr(settings, "crowding_guard_enabled", False))
    kwargs["max_sector_positions"] = int(getattr(settings, "max_sector_positions", 2))
    kwargs.setdefault("stop_loss_pct", float(settings.stop_loss_pct))
    kwargs.setdefault("trailing_stop_pct", float(settings.trailing_stop_pct))
    kwargs["regime_adaptive_stop_enabled"] = False
    kwargs["regime_stop_spy_df"] = spy_df

    profile = overrides.pop("regime_stop_profile", None)
    if profile is not None:
        kwargs["regime_stop_profile"] = profile
    kwargs.update(overrides)

    with _settings_patch(settings):
        result, equity_df, trades_df = run_portfolio_backtest(**kwargs)

    wm = _window_metrics(equity_df, report_start, report_end)
    spy_ret = None
    if report_start is not None and report_end is not None:
        spy_ret = _spy_return(spy_df, report_start, report_end)

    full_wm = _window_metrics(equity_df, None, None)
    exits = _exit_mix(trades_df)

    return {
        "scenario_id": scenario_id,
        "return_pct": wm["return_pct"],
        "full_period_return_pct": full_wm["return_pct"],
        "spy_return_pct": round(spy_ret * 100, 3) if spy_ret is not None else None,
        "alpha_vs_spy_pp": round((wm["return_pct"] / 100 - spy_ret) * 100, 3)
        if spy_ret is not None
        else None,
        "mdd_pct": wm["mdd_pct"],
        "sharpe": wm["sharpe"],
        "trades": int(result.trades),
        "win_rate_pct": round(float(result.win_rate) * 100, 1),
        "stop_loss_exits": int(exits.get("STOP_LOSS", 0)),
        "trailing_stop_exits": int(exits.get("TRAILING_STOP", 0)),
        "sell_signal_exits": int(exits.get("SELL_SIGNAL", 0)),
        "regime_adaptive": bool(kwargs.get("regime_adaptive_stop_enabled", False)),
        "stop_loss_pct_cfg": kwargs.get("stop_loss_pct"),
        "trailing_stop_pct_cfg": kwargs.get("trailing_stop_pct"),
    }


def derive_stop_recommendations(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Pick best scenario per window by return then sharpe vs baseline."""
    by_window: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_window.setdefault(str(row["window_id"]), []).append(row)

    winners: dict[str, Any] = {}
    for window_id, window_rows in by_window.items():
        baseline = next(
            (r for r in window_rows if r["scenario_id"] == "1_baseline_current"),
            None,
        )
        ranked = sorted(
            window_rows,
            key=lambda r: (r["return_pct"], r["sharpe"]),
            reverse=True,
        )
        best = ranked[0]
        winners[window_id] = {
            "best_scenario": best["scenario_id"],
            "best_return_pct": best["return_pct"],
            "best_mdd_pct": best["mdd_pct"],
            "baseline_return_pct": baseline["return_pct"] if baseline else None,
            "delta_vs_baseline_pp": round(
                best["return_pct"] - (baseline["return_pct"] if baseline else 0.0),
                3,
            ),
            "regime_adaptive_wins": best["scenario_id"].startswith("7_")
            or best["scenario_id"].startswith("8_"),
        }

    adaptive_better_count = sum(
        1
        for w in winners.values()
        if str(w.get("best_scenario", "")).startswith(("7_", "8_"))
    )
    return {
        "window_winners": winners,
        "regime_adaptive_best_in_windows": adaptive_better_count,
        "total_windows": len(winners),
        "verdict_ko": (
            "레짐 유동 스탑이 일부 구간에서 유의미"
            if adaptive_better_count >= max(1, len(winners) // 2)
            else "현재 baseline(5%/20%) 또는 고정 스탑이 대체로 우수 — 레짐 스탑 효과 제한적"
        ),
    }


def build_regime_stop_backtest_report(
    base_settings: StrategySettings | None = None,
    *,
    scenarios: tuple[tuple[str, dict[str, Any]], ...] = STOP_SCENARIOS,
    report_label: str = "full",
) -> dict[str, Any]:
    settings = base_settings or load_settings()
    static = [str(t).upper() for t in settings.tickers]
    loaded = load_price_data_batch(list(dict.fromkeys([*static, "SPY", "^VIX"])), period="2y")
    ticker_data = {t: loaded[t] for t in static if t in loaded}
    spy_df = loaded["SPY"]
    vix_df = loaded.get("^VIX")
    macro_df = load_macro_data(period="2y") if settings.use_ai_score else None
    rs_bench = loaded.get(settings.relative_strength_benchmark_ticker)

    windows: list[tuple[str, str, pd.Timestamp | None, pd.Timestamp | None]] = [
        ("full_2y", "전체 2년", None, None),
    ]
    for w in REGIME_WINDOWS:
        rs = pd.Timestamp(w.report_start)
        re = pd.Timestamp(w.report_end)
        windows.append((w.regime_id, w.label_ko, rs, re))

    all_rows: list[dict[str, Any]] = []

    for window_id, window_label, report_start, report_end in windows:
        if report_start is None:
            eval_start = None
            eval_end = None
        else:
            eval_start = warmup_start_for_report(spy_df, report_start)
            eval_end = report_end

        base_kw = portfolio_backtest_kwargs(
            settings,
            ticker_data=ticker_data,
            benchmark_df=spy_df,
            relative_strength_benchmark_df=rs_bench,
            vix_df=vix_df,
            macro_df=macro_df,
            initial_cash=INITIAL_CASH,
        )
        if eval_start is not None:
            base_kw["evaluation_start_date"] = eval_start
            base_kw["evaluation_end_date"] = eval_end
        base_kw["regime_stop_spy_df"] = spy_df
        base_kw["ai_exit_enabled"] = False

        for scenario_id, overrides in scenarios:
            row = _run_one(
                scenario_id,
                dict(overrides),
                base_settings=settings,
                base_kwargs=base_kw,
                report_start=report_start,
                report_end=report_end,
                spy_df=spy_df,
            )
            row["window_id"] = window_id
            row["window_label"] = window_label
            all_rows.append(row)

    recommendations = derive_stop_recommendations(all_rows)
    return {
        "generated_at": _utc_now_iso(),
        "methodology": {
            "report_label": report_label,
            "initial_cash": INITIAL_CASH,
            "scenarios": [s[0] for s in scenarios],
            "windows": [w[0] for w in windows],
            "notes": [
                "Portfolio backtest daily bars; ai_exit disabled for stop isolation.",
                "Regime adaptive uses SPY 20d thresholds from RegimeStopProfile.",
                "Sub-windows use 90d warmup; metrics are report-window only.",
            ],
        },
        "results": all_rows,
        "recommendations": recommendations,
        "policy_path": str(POLICY_PATH),
    }


def write_regime_stop_backtest_artifacts(
    report: dict[str, Any],
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    policy_path: Path = POLICY_PATH,
    *,
    filename_prefix: str = "",
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / f"{filename_prefix}latest_summary.json"
    summary_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    pd.DataFrame(report["results"]).to_csv(
        output_dir / f"{filename_prefix}comparison.csv",
        index=False,
    )

    policy_path.parent.mkdir(parents=True, exist_ok=True)
    policy_path.write_text(
        json.dumps(
            {
                "version": 1,
                "generated_at": report.get("generated_at"),
                "source": str(summary_path),
                "recommendations": report.get("recommendations"),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return summary_path


def run_regime_stop_backtest() -> dict[str, Any]:
    report = build_regime_stop_backtest_report()
    write_regime_stop_backtest_artifacts(report)
    return report


def run_followup_regime_stop_backtest() -> dict[str, Any]:
    report = build_regime_stop_backtest_report(
        scenarios=FOLLOWUP_STOP_SCENARIOS,
        report_label="followup_trail10_12_bear_only",
    )
    recommendations = derive_stop_recommendations(report["results"])
    report["recommendations"] = recommendations
    write_regime_stop_backtest_artifacts(
        report,
        filename_prefix="followup_",
        policy_path=Path("data/research/regime_stop_followup_policy.json"),
    )
    return report


def _print_report_table(report: dict[str, Any], title: str) -> None:
    df = pd.DataFrame(report["results"])
    pd.set_option("display.width", 240)
    print(f"\n=== {title} ===")
    for window_id in df["window_id"].unique():
        sub = df[df["window_id"] == window_id][
            [
                "scenario_id",
                "return_pct",
                "mdd_pct",
                "sharpe",
                "trades",
                "stop_loss_exits",
                "trailing_stop_exits",
            ]
        ]
        print(f"\n--- {window_id} ---")
        print(sub.to_string(index=False))
    print("\nVerdict:", report["recommendations"]["verdict_ko"])


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Regime stop backtest")
    parser.add_argument(
        "--followup",
        action="store_true",
        help="Run follow-up: trail 10/12% + bear-only SPY20d<0 tight 3%%",
    )
    args = parser.parse_args()

    if args.followup:
        report = run_followup_regime_stop_backtest()
        _print_report_table(report, "Follow-up stop backtest (trail 10/12 + bear-only)")
        print(f"Saved: {DEFAULT_OUTPUT_DIR / 'followup_latest_summary.json'}")
    else:
        report = run_regime_stop_backtest()
        _print_report_table(report, "Regime stop backtest")
        print(f"Saved: {DEFAULT_OUTPUT_DIR / 'latest_summary.json'}")


if __name__ == "__main__":
    main()
