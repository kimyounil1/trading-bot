"""Sector-cap / crowding-cap sweep on the paper-aligned sleeved backtest.

Backtest companion to the guard counterfactual (logs/guard_gates): the audit
replay says crowding blocks genuinely bad entries while the sector cap blocks
SPY-beating names. This sweeps both caps through the full operational
(rank-primary, sleeved) backtest so the question doesn't have to wait for
more paper data.

Reports BOTH the selection window and the untouched forward window separately
(lesson from the regime-gate card: single-window verdicts flip). Research
only — paper config untouched; adoption still gated on the 20d/30-plan
forward-parity rule in TODO.md.

Usage: PYTHONPATH=. .venv/bin/python -m scripts.exp_guard_cap_sweep
"""

from __future__ import annotations

import copy
import json
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pandas as pd

from src.candidate_cache import load_dynamic_universe_history
from src.data_loader import load_price_data_batch
from src.instrument_meta import preferred_leveraged_long_product
from src.macro_loader import load_macro_data
from src.run_portfolio_backtest import latest_covered_market_date
from src.settings import StrategySettings, load_settings
from src.sleeved_portfolio_backtester import run_sleeved_portfolio_backtest

OUTPUT_DIR = Path("logs/guard_cap_sweep")
EVAL_START = "2026-01-02"
SELECTION_END = "2026-05-01"
FORWARD_START = "2026-05-04"
INITIAL_CASH = 10_000.0

SCENARIO_SETS: dict[str, list[tuple[str, dict[str, Any]]]] = {
    "guards": [
        ("1_baseline_sector2_crowd3", {}),
        ("2_sector_max_3", {"max_sector_positions": 3}),
        ("3_sector_max_4", {"max_sector_positions": 4}),
        ("4_sector_off", {"max_sector_positions": 99}),
        ("5_crowding_off", {"crowding_guard_enabled": False}),
        ("6_crowding_max_2", {"crowding_max_positions": 2}),
    ],
    "rank_cutoff": [
        ("1_baseline_top15", {}),
        ("2_top10", {"rank_ai_buy_gate_top_bucket_pct": 0.10}),
        ("3_top20", {"rank_ai_buy_gate_top_bucket_pct": 0.20}),
        ("4_top30", {"rank_ai_buy_gate_top_bucket_pct": 0.30}),
    ],
    # Crowding redesign: binary block stays, but vary the cap and what counts
    # as "crowded" (bull markets put nearly every holding ≥5% above MA50, so
    # the trend leg saturates and the guard becomes a momentum-entry ban).
    "crowding": [
        ("1_baseline_crowd3_m15_g05", {}),
        ("2_crowd_max4", {"crowding_max_positions": 4}),
        ("3_crowd_max5", {"crowding_max_positions": 5}),
        ("4_trend_gap10", {"crowding_trend_gap_threshold": 0.10}),
        ("5_momentum_leg_only", {"crowding_trend_gap_threshold": 9.9}),
        ("6_tight_def_m25_g10", {"crowding_momentum_threshold": 0.25, "crowding_trend_gap_threshold": 0.10}),
    ],
}


@contextmanager
def _settings_patch(settings: StrategySettings):
    with patch("src.risk_manager.load_settings", return_value=settings):
        yield


def _window_metrics(equity_df: pd.DataFrame, start: str, end: str | None) -> dict[str, Any]:
    df = equity_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    mask = df["date"] >= pd.Timestamp(start)
    if end is not None:
        mask &= df["date"] <= pd.Timestamp(end)
    window = df[mask]
    if len(window) < 2:
        return {"return_pct": None, "mdd_pct": None, "sharpe": None, "trading_days": len(window)}
    start_eq = float(window.iloc[0]["equity"])
    end_eq = float(window.iloc[-1]["equity"])
    ret = end_eq / start_eq - 1.0 if start_eq > 0 else 0.0
    daily = window["equity"].pct_change().fillna(0.0)
    running_max = window["equity"].cummax()
    mdd = float((window["equity"] / running_max - 1.0).min())
    std = float(daily.std())
    sharpe = float(daily.mean() / std * (252**0.5)) if std > 1e-10 else 0.0
    return {
        "return_pct": round(ret * 100, 3),
        "mdd_pct": round(mdd * 100, 3),
        "sharpe": round(sharpe, 3),
        "trading_days": int(len(window)),
    }


def _assemble_inputs(settings: StrategySettings) -> dict[str, Any]:
    """Mirror src.run_portfolio_backtest.main data assembly (sleeved path)."""
    historical_universe = load_dynamic_universe_history()
    dynamic_symbols = sorted(
        {
            ticker
            for date, tickers in historical_universe.items()
            if date >= pd.Timestamp(EVAL_START)
            for ticker in tickers
        }
    )
    signal_tickers = list(dict.fromkeys([*settings.tickers, *dynamic_symbols]))
    product_routes = {
        ticker: product
        for ticker in signal_tickers
        if (
            product := preferred_leveraged_long_product(
                ticker,
                allowlist=list(settings.leveraged_etf_allowlist),
            )
        )
    }
    tickers_to_load = list(signal_tickers)
    tickers_to_load.extend(product_routes.values())
    if settings.market_regime_filter_enabled:
        tickers_to_load.append(settings.market_regime_ticker)
    if settings.relative_strength_filter_enabled:
        tickers_to_load.append(settings.relative_strength_benchmark_ticker)
    if settings.use_ai_score and "^VIX" not in tickers_to_load:
        tickers_to_load.append("^VIX")
    loaded = load_price_data_batch(list(dict.fromkeys(tickers_to_load)), period="2y")

    ticker_data = {t: loaded[t] for t in signal_tickers if t in loaded}
    covered_end = latest_covered_market_date(
        ticker_data,
        base_tickers=list(settings.tickers),
        requested_end=None,
    )
    return {
        "ticker_data": ticker_data,
        "benchmark_df": (
            loaded.get(settings.market_regime_ticker)
            if settings.market_regime_filter_enabled
            else None
        ),
        "relative_strength_benchmark_df": (
            loaded.get(settings.relative_strength_benchmark_ticker)
            if settings.relative_strength_filter_enabled
            else None
        ),
        "vix_df": loaded.get("^VIX"),
        "macro_df": load_macro_data(period="2y") if settings.use_ai_score else None,
        "initial_cash": INITIAL_CASH,
        "evaluation_start_date": EVAL_START,
        "evaluation_end_date": covered_end.strftime("%Y-%m-%d"),
        "leveraged_product_data": {
            product: loaded[product]
            for product in product_routes.values()
            if product in loaded
        },
        "leveraged_product_routes": product_routes,
        "historical_universe_by_date": historical_universe,
        "base_universe": set(settings.tickers),
        "benchmark_universe": set(settings.tickers),
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Guard cap / rank cutoff sweep")
    parser.add_argument("--set", choices=sorted(SCENARIO_SETS), default="guards")
    args = parser.parse_args()
    scenarios = SCENARIO_SETS[args.set]
    output_dir = OUTPUT_DIR / args.set

    base_settings = load_settings()
    if not base_settings.portfolio_sleeves_enabled:
        raise SystemExit("portfolio_sleeves_enabled must be true (paper-aligned run)")

    print(f"Scenario set: {args.set}")
    print("Assembling paper-aligned backtest inputs (single data load)...")
    inputs = _assemble_inputs(base_settings)
    eval_end = inputs["evaluation_end_date"]
    print(f"Evaluation {EVAL_START} → {eval_end} | universe={len(inputs['ticker_data'])}")

    rows: list[dict[str, Any]] = []
    for label, overrides in scenarios:
        settings = copy.deepcopy(base_settings)
        for key, value in overrides.items():
            setattr(settings, key, value)
        print(f"Running {label}...", flush=True)
        with _settings_patch(settings):
            result, equity_df, trades_df = run_sleeved_portfolio_backtest(
                settings, **inputs
            )
        selection = _window_metrics(equity_df, EVAL_START, SELECTION_END)
        forward = _window_metrics(equity_df, FORWARD_START, None)
        row = {
            "scenario": label,
            "overrides": overrides,
            "full_return_pct": round(result.total_return * 100, 3),
            "full_benchmark_pct": round(result.benchmark_return * 100, 3),
            "full_mdd_pct": round(result.max_drawdown * 100, 3),
            "full_sharpe": round(result.sharpe_ratio, 3),
            "trades": int(result.trades),
            "win_rate_pct": round(result.win_rate * 100, 1),
            "selection": selection,
            "forward": forward,
        }
        rows.append(row)
        print(
            f"  full={row['full_return_pct']:+.2f}% mdd={row['full_mdd_pct']:.2f}% "
            f"sharpe={row['full_sharpe']:.2f} trades={row['trades']} | "
            f"sel={selection['return_pct']}% fwd={forward['return_pct']}%",
            flush=True,
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scenario_set": args.set,
        "evaluation_start": EVAL_START,
        "evaluation_end": eval_end,
        "selection_end": SELECTION_END,
        "forward_start": FORWARD_START,
        "initial_cash": INITIAL_CASH,
        "scenarios": rows,
        "notes": [
            "Sleeved paper-aligned backtest (rank-primary); config on disk untouched.",
            "Judge on the forward window first; selection window overlaps model selection history.",
            "LLM gate is NOT replayed (no leak-free historical verdicts) — live counterfactual covers it.",
            "Adoption gated on TODO.md forward-parity rule (20 trading days / 30 buy plans).",
        ],
    }
    out_path = output_dir / "summary.json"
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    flat = pd.DataFrame(
        [
            {
                "scenario": r["scenario"],
                "full_ret%": r["full_return_pct"],
                "full_mdd%": r["full_mdd_pct"],
                "sharpe": r["full_sharpe"],
                "trades": r["trades"],
                "sel_ret%": r["selection"]["return_pct"],
                "fwd_ret%": r["forward"]["return_pct"],
                "fwd_mdd%": r["forward"]["mdd_pct"],
                "fwd_sharpe": r["forward"]["sharpe"],
            }
            for r in rows
        ]
    )
    flat.to_csv(output_dir / "summary.csv", index=False)
    pd.set_option("display.width", 220)
    print(f"\n=== {args.set} sweep (paper-aligned sleeved backtest) ===")
    print(flat.to_string(index=False))
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()
