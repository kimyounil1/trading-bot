"""Report-only strategy parameter sweeps (§5-A entry signals, §5-B sizing/exit).

Train/OOS: in-sample window ends at portfolio holdout start; OOS gate on holdout only.
Adoption gate: OOS gap >= 0pp, Sharpe >= 1.0, beats baseline OOS gap by +0.5pp.
Does not modify paper config — use 5-adopt [Cursor] after explicit promotion review.
"""

from __future__ import annotations

import argparse
import itertools
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.portfolio_backtest_settings import portfolio_backtest_kwargs
from src.portfolio_backtester import run_portfolio_backtest
from src.promotion_thresholds import promotion_portfolio_thresholds
from src.retrain_holdout import portfolio_holdout_window

DEFAULT_OUTPUT_DIR = Path("logs/strategy_parameter_sweep")
MIN_ADOPT_PP = 0.5

ENTRY_MA_FAST = [5, 10, 15, 20, 25, 30]
ENTRY_MA_SLOW = [30, 50, 70, 100]
ENTRY_RSI = [45, 55, 65, 75]

SIZING_POSITION_PCT = [0.10, 0.11, 0.13, 0.15]
SIZING_TAKE_PROFIT = [0.10, 0.15, 0.20, 0.25]
SIZING_MAX_HOLDING = [20, 30, 45, 60]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class BacktestWindow:
    label: str
    start: pd.Timestamp | None
    end: pd.Timestamp | None


def _metrics_from_result(result) -> dict[str, Any]:
    gap_pp = (float(result.total_return) - float(result.benchmark_return)) * 100.0
    return {
        "total_return_pct": round(float(result.total_return) * 100.0, 4),
        "benchmark_return_pct": round(float(result.benchmark_return) * 100.0, 4),
        "gap_pp": round(gap_pp, 4),
        "max_drawdown_pct": round(float(result.max_drawdown) * 100.0, 4),
        "sharpe_ratio": round(float(result.sharpe_ratio), 4),
        "trades": int(result.trades),
        "win_rate": round(float(result.win_rate), 4),
    }


def _passes_oos_gate(metrics: dict[str, Any], *, baseline_gap_pp: float) -> bool:
    thresholds = promotion_portfolio_thresholds()
    gap = float(metrics["gap_pp"])
    sharpe = float(metrics["sharpe_ratio"])
    mdd = float(metrics["max_drawdown_pct"]) / 100.0
    if gap < float(thresholds.min_return_vs_benchmark or 0.0) * 100.0:
        return False
    if thresholds.min_sharpe is not None and sharpe < float(thresholds.min_sharpe):
        return False
    if mdd < float(thresholds.max_drawdown_floor):
        return False
    if gap < baseline_gap_pp + MIN_ADOPT_PP:
        return False
    return True


def load_sweep_backtest_context(*, period: str = "2y"):
    from src.data_loader import load_price_data_batch
    from src.macro_loader import load_macro_data
    from src.portfolio_backtester import build_ai_score_frames
    from src.settings import load_settings

    settings = load_settings()
    tickers = list(dict.fromkeys(list(settings.tickers) + ["^VIX", "SPY"]))
    loaded = load_price_data_batch(tickers, period=period)
    ticker_data = {t: loaded[t] for t in settings.tickers if t in loaded}
    vix_df = loaded.get("^VIX")
    macro_df = load_macro_data(period=period) if settings.use_ai_score else None
    if macro_df is not None and macro_df.empty:
        macro_df = None
    rs_bench = loaded.get(settings.relative_strength_benchmark_ticker)
    ai_frames = build_ai_score_frames(ticker_data) if settings.use_ai_score else None
    holdout_start, holdout_end = portfolio_holdout_window(ticker_data)
    base_kwargs = portfolio_backtest_kwargs(
        settings,
        ticker_data=ticker_data,
        relative_strength_benchmark_df=rs_bench,
        vix_df=vix_df,
        macro_df=macro_df,
        ai_score_frames=ai_frames,
    )
    windows = {
        "train": BacktestWindow("train", None, holdout_start - pd.Timedelta(days=1)),
        "oos": BacktestWindow("oos", holdout_start, holdout_end),
    }
    return settings, base_kwargs, windows


def _run_window(base_kwargs: dict[str, Any], window: BacktestWindow, overrides: dict[str, Any]):
    kw = dict(base_kwargs)
    kw.update(overrides)
    kw["evaluation_start_date"] = window.start
    kw["evaluation_end_date"] = window.end
    result, _, _ = run_portfolio_backtest(**kw)
    return _metrics_from_result(result)


def _evaluate_combo(
    base_kwargs: dict[str, Any],
    windows: dict[str, BacktestWindow],
    overrides: dict[str, Any],
    *,
    baseline_oos_gap: float,
) -> dict[str, Any]:
    train = _run_window(base_kwargs, windows["train"], overrides)
    oos = _run_window(base_kwargs, windows["oos"], overrides)
    return {
        **overrides,
        "train": train,
        "oos": oos,
        "gate_passed": _passes_oos_gate(oos, baseline_gap_pp=baseline_oos_gap),
    }


def build_entry_signal_sweep_report(*, period: str = "2y") -> dict[str, Any]:
    _settings, base_kwargs, windows = load_sweep_backtest_context(period=period)
    baseline = _evaluate_combo(base_kwargs, windows, {}, baseline_oos_gap=-999.0)
    baseline_oos_gap = float(baseline["oos"]["gap_pp"])

    rows: list[dict[str, Any]] = []
    for ma_fast, ma_slow, rsi in itertools.product(ENTRY_MA_FAST, ENTRY_MA_SLOW, ENTRY_RSI):
        if ma_fast >= ma_slow:
            continue
        overrides = {"ma_fast": ma_fast, "ma_slow": ma_slow, "rsi_buy_limit": float(rsi)}
        rows.append(
            _evaluate_combo(
                base_kwargs,
                windows,
                overrides,
                baseline_oos_gap=baseline_oos_gap,
            )
        )

    passed = [r for r in rows if r["gate_passed"]]
    best = max(rows, key=lambda r: float(r["oos"]["gap_pp"])) if rows else None
    return {
        "generated_at": _utc_now_iso(),
        "sweep": "entry_signal",
        "period": period,
        "min_adopt_pp": MIN_ADOPT_PP,
        "baseline": baseline,
        "combinations_tested": len(rows),
        "combinations_passed": len(passed),
        "best_oos": best,
        "passed": sorted(passed, key=lambda r: float(r["oos"]["gap_pp"]), reverse=True)[:10],
        "recommendation": (
            f"Adopt candidate ma_fast={best['ma_fast']} ma_slow={best['ma_slow']} "
            f"rsi={best['rsi_buy_limit']} via promotion gate (OOS gap {best['oos']['gap_pp']:.2f}pp)."
            if passed and best is not None
            else "No entry-signal combo cleared OOS promotion gate; keep current config."
        ),
    }


def build_sizing_exit_sweep_report(*, period: str = "2y") -> dict[str, Any]:
    _settings, base_kwargs, windows = load_sweep_backtest_context(period=period)
    baseline = _evaluate_combo(base_kwargs, windows, {}, baseline_oos_gap=-999.0)
    baseline_oos_gap = float(baseline["oos"]["gap_pp"])

    rows: list[dict[str, Any]] = []
    for pos_pct, take_profit, max_hold in itertools.product(
        SIZING_POSITION_PCT,
        SIZING_TAKE_PROFIT,
        SIZING_MAX_HOLDING,
    ):
        overrides = {
            "target_position_pct": float(pos_pct),
            "take_profit_pct": float(take_profit),
            "max_holding_days": int(max_hold),
        }
        rows.append(
            _evaluate_combo(
                base_kwargs,
                windows,
                overrides,
                baseline_oos_gap=baseline_oos_gap,
            )
        )

    passed = [r for r in rows if r["gate_passed"]]
    best = max(rows, key=lambda r: float(r["oos"]["gap_pp"])) if rows else None
    return {
        "generated_at": _utc_now_iso(),
        "sweep": "sizing_exit",
        "period": period,
        "min_adopt_pp": MIN_ADOPT_PP,
        "baseline": baseline,
        "note": (
            "Backtester sweeps target_position_pct, take_profit_pct, max_holding_days. "
            "conviction_position_mult_max / partial_exit_ratio require live path only."
        ),
        "combinations_tested": len(rows),
        "combinations_passed": len(passed),
        "best_oos": best,
        "passed": sorted(passed, key=lambda r: float(r["oos"]["gap_pp"]), reverse=True)[:10],
        "recommendation": (
            f"Adopt sizing candidate pos={best['target_position_pct']} tp={best['take_profit_pct']} "
            f"hold={best['max_holding_days']}d via promotion gate."
            if passed and best is not None
            else "No sizing/exit combo cleared OOS promotion gate; keep current config."
        ),
    }


def write_sweep_report(report: dict[str, Any], output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    name = f"{report['sweep']}_sweep_report.json"
    path = output_dir / name
    path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Strategy parameter sweeps (report-only)")
    parser.add_argument(
        "--sweep",
        choices=("entry", "sizing", "all"),
        default="all",
    )
    parser.add_argument("--period", default="2y")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    if args.sweep in ("entry", "all"):
        entry_report = build_entry_signal_sweep_report(period=args.period)
        path = write_sweep_report(entry_report, args.output_dir)
        print(json.dumps(entry_report, indent=2, sort_keys=True))
        print(f"Wrote {path}")

    if args.sweep in ("sizing", "all"):
        sizing_report = build_sizing_exit_sweep_report(period=args.period)
        path = write_sweep_report(sizing_report, args.output_dir)
        print(json.dumps(sizing_report, indent=2, sort_keys=True))
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
