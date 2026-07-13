#!/usr/bin/env python3
"""Compare 1x, always-2x, and SPY bull-only 2x margin policies."""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data_loader import load_cached_price_data
from src.margin_leverage_overlay import (
    simulate_conditional_margin_overlay,
    summarize_conditional_margin_overlay,
)


OUTPUT_DIR = Path("logs/margin_leverage_validation_20260713")


def _comparison_rows(
    *,
    mode: str,
    baseline_path: Path,
    existing_summary_path: Path,
    windows: dict[str, pd.Timestamp],
    spy: pd.DataFrame,
    vix: pd.DataFrame,
) -> tuple[list[dict], pd.DataFrame]:
    baseline = pd.read_csv(baseline_path)
    conditional = simulate_conditional_margin_overlay(
        baseline,
        spy,
        bull_leverage_factor=2.0,
        defensive_leverage_factor=1.0,
        regime_ma_fast=50,
        regime_ma_slow=200,
        annual_margin_interest_rate=0.0625,
        transition_cost_pct=0.001,
    )
    always_two = simulate_conditional_margin_overlay(
        baseline,
        spy,
        bull_leverage_factor=2.0,
        defensive_leverage_factor=2.0,
        regime_ma_fast=50,
        regime_ma_slow=200,
        annual_margin_interest_rate=0.0625,
        transition_cost_pct=0.001,
    )
    conditional_vix = simulate_conditional_margin_overlay(
        baseline,
        spy,
        vix_df=vix,
        max_vix=22.0,
        bull_leverage_factor=2.0,
        defensive_leverage_factor=1.0,
        regime_ma_fast=50,
        regime_ma_slow=200,
        annual_margin_interest_rate=0.0625,
        transition_cost_pct=0.001,
    )
    rows: list[dict] = []
    existing = pd.read_csv(existing_summary_path)
    for window, start in windows.items():
        for factor, policy in ((1.0, "always_1x"), (2.0, "always_2x")):
            matched = existing[
                (existing["window"] == window)
                & (existing["leverage_factor"] == factor)
            ]
            if matched.empty:
                continue
            row = matched.iloc[0]
            rows.append(
                {
                    "mode": mode,
                    "window": window,
                    "policy": policy,
                    "total_return": row["total_return"],
                    "max_drawdown": row["max_drawdown"],
                    "sharpe_ratio": row["sharpe_ratio"],
                    "avg_gross_exposure": row["avg_gross_exposure"],
                    "max_gross_exposure": row["max_gross_exposure"],
                    "leveraged_days_pct": 1.0 if factor == 2.0 else 0.0,
                    "margin_interest_paid": row["margin_interest_paid"],
                    "start": row["start"],
                    "end": row["end"],
                }
            )
        metrics = summarize_conditional_margin_overlay(conditional, start=start)
        rows.append(
            {
                "mode": mode,
                "window": window,
                "policy": "spy_bull_2x_else_1x",
                **metrics,
            }
        )
        always_two_metrics = summarize_conditional_margin_overlay(
            always_two, start=start
        )
        rows.append(
            {
                "mode": mode,
                "window": window,
                "policy": "always_2x_daily_rebalanced",
                **always_two_metrics,
            }
        )
        conditional_vix_metrics = summarize_conditional_margin_overlay(
            conditional_vix, start=start
        )
        rows.append(
            {
                "mode": mode,
                "window": window,
                "policy": "spy_bull_vix22_2x_else_1x",
                **conditional_vix_metrics,
            }
        )
    return rows, conditional


def main() -> None:
    spy = load_cached_price_data("SPY", period="5y")
    vix = load_cached_price_data("^VIX", period="5y")
    technical_equity = pd.read_csv(OUTPUT_DIR / "equity_1.00x.csv")
    operational_equity = pd.read_csv(OUTPUT_DIR / "operational_equity_1.00x.csv")
    technical_end = pd.to_datetime(technical_equity["date"]).max()
    operational_end = pd.to_datetime(operational_equity["date"]).max()

    technical_rows, technical_conditional = _comparison_rows(
        mode="technical",
        baseline_path=OUTPUT_DIR / "equity_1.00x.csv",
        existing_summary_path=OUTPUT_DIR / "summary.csv",
        windows={
            "6m": technical_end - pd.DateOffset(months=6),
            "1y": technical_end - pd.DateOffset(years=1),
            "4y": technical_end - pd.DateOffset(years=4),
        },
        spy=spy,
        vix=vix,
    )
    operational_rows, operational_conditional = _comparison_rows(
        mode="operational",
        baseline_path=OUTPUT_DIR / "operational_equity_1.00x.csv",
        existing_summary_path=OUTPUT_DIR / "operational_summary.csv",
        windows={
            "6m": operational_end - pd.DateOffset(months=6),
            "1y": operational_end - pd.DateOffset(years=1),
        },
        spy=spy,
        vix=vix,
    )

    summary = pd.DataFrame([*technical_rows, *operational_rows])
    summary.to_csv(OUTPUT_DIR / "conditional_summary.csv", index=False)
    technical_conditional.to_csv(
        OUTPUT_DIR / "conditional_technical_equity.csv", index=False
    )
    operational_conditional.to_csv(
        OUTPUT_DIR / "conditional_operational_equity.csv", index=False
    )
    print(summary.to_string(index=False))
    print(f"saved={OUTPUT_DIR / 'conditional_summary.csv'}")


if __name__ == "__main__":
    main()
