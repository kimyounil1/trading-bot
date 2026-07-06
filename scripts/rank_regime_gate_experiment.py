"""Offline regime-conditional rank-gate experiment on the paper 110 universe.

Keeps the production rank model config (h20, top15%, base cutoff q85) and varies the
buy-gate cutoff by market regime (src.market_regime: BULL / NEUTRAL / BEAR). The
simulation itself is untouched: rows failing the regime cutoff for their date get their
predicted percentile masked to -1, and the simulator runs with min_score_quantile=0.

Variants:
  baseline            : 0.85 in every regime (production replica)
  bear_tighten        : BEAR 0.95
  bear_block          : no buys in BEAR
  neutral_bear_tighten: NEUTRAL 0.90, BEAR 0.95
  bear_loosen         : BEAR 0.75 (buy-the-dip control arm)

Outputs comparison report to logs/ml/rank_regime_gate/.

Usage:
  .venv/bin/python -m scripts.rank_regime_gate_experiment [--holdout-months N]
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.data_loader import load_price_data_batch
from src.macro_loader import load_macro_data
from src.market_regime import compute_daily_regime
from src.rank_label_experiment import (
    RankExperimentConfig,
    _build_rank_dataset,
    _score_oos,
    _simulate_top_bucket_portfolio,
    _train_rank_models,
)
from src.retrain_holdout import portfolio_holdout_window
from src.settings import load_settings

OUTPUT_DIR = Path("logs/ml/rank_regime_gate")
BASE_CUTOFF = 0.85

VARIANTS: dict[str, dict[str, float]] = {
    "baseline": {"BULL": 0.85, "NEUTRAL": 0.85, "BEAR": 0.85},
    "bear_tighten": {"BULL": 0.85, "NEUTRAL": 0.85, "BEAR": 0.95},
    "bear_block": {"BULL": 0.85, "NEUTRAL": 0.85, "BEAR": 1.01},
    "neutral_bear_tighten": {"BULL": 0.85, "NEUTRAL": 0.90, "BEAR": 0.95},
    "bear_loosen": {"BULL": 0.85, "NEUTRAL": 0.85, "BEAR": 0.75},
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _apply_regime_cutoffs(
    scored: pd.DataFrame,
    regime_by_date: pd.Series,
    cutoffs: dict[str, float],
) -> pd.DataFrame:
    """Mask predicted percentiles below the date's regime cutoff (simulator gate at 0)."""
    out = scored.copy()
    regimes = out["date"].map(regime_by_date).fillna("NEUTRAL")
    thresholds = regimes.map(lambda r: cutoffs.get(str(r), BASE_CUTOFF))
    out.loc[out["predicted_score_percentile"] < thresholds, "predicted_score_percentile"] = -1.0
    return out


def _verdict(results: dict[str, dict]) -> dict:
    base = results["baseline"]
    best_name, best = None, None
    for name, res in results.items():
        if name == "baseline":
            continue
        sharpe_delta = res["sharpe_ratio"] - base["sharpe_ratio"]
        mdd_delta = res["max_drawdown"] - base["max_drawdown"]  # positive = shallower
        return_delta = res["total_return"] - base["total_return"]
        passed = sharpe_delta >= 0.2 and mdd_delta >= 0.01 and return_delta >= -0.02
        results[name]["gate"] = {
            "sharpe_delta": round(sharpe_delta, 4),
            "mdd_delta": round(mdd_delta, 4),
            "return_delta": round(return_delta, 4),
            "passed": passed,
        }
        if passed and (best is None or res["sharpe_ratio"] > best["sharpe_ratio"]):
            best_name, best = name, res
    if best_name is None:
        return {
            "winner": "baseline",
            "recommendation": "Keep the flat q85 cutoff; no regime variant clears the gate",
        }
    return {
        "winner": best_name,
        "recommendation": (
            f"Variant '{best_name}' improves risk-adjusted OOS results; "
            "consider wiring a regime-conditional rank cutoff behind a config flag"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--holdout-months", type=int, default=6)
    args = parser.parse_args()

    settings = load_settings()
    cfg = RankExperimentConfig(
        prediction_horizon=20,
        top_bucket_pct=0.15,
        min_score_quantile=BASE_CUTOFF,
        period="5y",
    )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    tickers = list(dict.fromkeys([str(t).strip().upper() for t in settings.tickers] + ["^VIX", "SPY"]))
    print(f"Loading {len(tickers)} tickers ({cfg.period})...")
    loaded = load_price_data_batch(tickers, period=cfg.period)
    ticker_data = {t: loaded[t] for t in settings.tickers if t in loaded}
    vix_df = loaded.get("^VIX")
    spy_df = loaded.get("SPY")
    try:
        macro_df = load_macro_data()
    except Exception:
        macro_df = None

    dataset = _build_rank_dataset(
        ticker_data,
        prediction_horizon=cfg.prediction_horizon,
        vix_df=vix_df,
        spy_df=spy_df,
        macro_df=macro_df,
    )
    holdout_start, holdout_end = portfolio_holdout_window(
        ticker_data, months=args.holdout_months
    )
    train_df = dataset[dataset["date"] < holdout_start].copy()
    test_df = dataset[
        (dataset["date"] >= holdout_start) & (dataset["date"] <= holdout_end)
    ].copy()
    print(f"Train rows={len(train_df):,}  Test rows={len(test_df):,}")
    print(f"Holdout {holdout_start.date()} .. {holdout_end.date()}\n")

    clf, reg = _train_rank_models(train_df, cfg.top_bucket_pct)
    scored = _score_oos(test_df, classifier=clf, regressor=reg, top_bucket_pct=cfg.top_bucket_pct)

    regime_by_date = compute_daily_regime(spy_df, vix_df)
    regime_by_date.index = pd.to_datetime(regime_by_date.index)
    holdout_regimes = regime_by_date[
        (regime_by_date.index >= holdout_start) & (regime_by_date.index <= holdout_end)
    ]
    regime_counts = holdout_regimes.value_counts().to_dict()
    print(f"Holdout regime days: {regime_counts}\n")

    sim_cfg = replace(cfg, min_score_quantile=0.0)
    results: dict[str, dict] = {}
    for name, cutoffs in VARIANTS.items():
        variant_scored = _apply_regime_cutoffs(scored, regime_by_date, cutoffs)
        portfolio, _, _ = _simulate_top_bucket_portfolio(variant_scored, ticker_data, sim_cfg)
        results[name] = {
            "cutoffs": cutoffs,
            **{k: round(v, 4) if isinstance(v, float) else v for k, v in portfolio.items()},
        }

    verdict = _verdict(results)

    report = {
        "generated_at": _utc_now(),
        "holdout": {"start": str(holdout_start.date()), "end": str(holdout_end.date())},
        "holdout_months": args.holdout_months,
        "config": asdict(cfg),
        "holdout_regime_days": {str(k): int(v) for k, v in regime_counts.items()},
        "variants": results,
        "verdict": verdict,
    }
    suffix = "" if args.holdout_months == 6 else f"_h{args.holdout_months}m"
    summary_path = OUTPUT_DIR / f"comparison_summary{suffix}.json"
    summary_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("=== Regime-conditional cutoff variants (same model, same holdout) ===")
    for name, res in results.items():
        print(
            f"{name:<22} ret={res['total_return']:.2%}  bench={res['benchmark_return']:.2%}  "
            f"Sharpe={res['sharpe_ratio']:.2f}  MDD={res['max_drawdown']:.2%}  "
            f"trades={res['trades']}  win={res['win_rate']:.1%}"
        )
    print(f"\nVerdict: {verdict}")
    print(f"Saved: {summary_path}")


if __name__ == "__main__":
    main()
