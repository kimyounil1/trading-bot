"""Evaluate AI label horizon / return threshold candidates."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.data_loader import load_price_data_batch
from src.features import build_features
from src.macro_loader import load_macro_data
from src.market_regime import compute_daily_regime
from src.settings import load_settings


DEFAULT_OUTPUT_DIR = Path("logs/ml")
DEFAULT_HORIZONS = (5, 10, 20, 40)
DEFAULT_THRESHOLDS = (0.0, 0.02, 0.05, 0.10)
TARGET_POSITIVE_RATE = 0.50

LABEL_HORIZON_REPORT_KEYS = (
    "generated_at",
    "status",
    "candidates",
    "best_candidate",
    "recommendation",
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_float_list(value: str) -> tuple[float, ...]:
    return tuple(float(item.strip()) for item in value.split(",") if item.strip())


def _parse_int_list(value: str) -> tuple[int, ...]:
    return tuple(int(item.strip()) for item in value.split(",") if item.strip())


def _attach_regime(
    frame: pd.DataFrame,
    spy_df: pd.DataFrame | None,
    vix_df: pd.DataFrame | None,
) -> pd.DataFrame:
    out = frame.copy()
    if spy_df is None or vix_df is None or spy_df.empty or vix_df.empty:
        out["regime"] = "NEUTRAL"
        return out
    regimes = compute_daily_regime(spy_df, vix_df)
    if regimes.empty:
        out["regime"] = "NEUTRAL"
        return out
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out = out.merge(regimes.rename("regime"), left_on="date", right_index=True, how="left")
    out["regime"] = out["regime"].fillna("NEUTRAL")
    return out


def _candidate_summary(
    dataset: pd.DataFrame,
    *,
    horizon: int,
    threshold: float,
) -> dict[str, Any]:
    rows = int(len(dataset))
    positive_rate = float(dataset["target"].mean()) if rows else 0.0
    balance_penalty = abs(positive_rate - TARGET_POSITIVE_RATE)
    by_regime = {}
    regime_penalties = []
    for regime, regime_df in dataset.groupby("regime"):
        rate = float(regime_df["target"].mean()) if len(regime_df) else 0.0
        by_regime[str(regime)] = {
            "rows": int(len(regime_df)),
            "positive_rate": rate,
            "future_return_mean": float(regime_df["future_return"].mean()),
        }
        if len(regime_df) >= 100:
            regime_penalties.append(abs(rate - TARGET_POSITIVE_RATE))
    regime_balance_penalty = (
        float(sum(regime_penalties) / len(regime_penalties)) if regime_penalties else 0.5
    )
    score = balance_penalty + (0.5 * regime_balance_penalty) - min(rows / 200_000, 0.25)
    return {
        "horizon": int(horizon),
        "target_return_threshold": float(threshold),
        "rows": rows,
        "positive_rate": positive_rate,
        "future_return_mean": float(dataset["future_return"].mean()) if rows else 0.0,
        "balance_penalty": balance_penalty,
        "regime_balance_penalty": regime_balance_penalty,
        "score": score,
        "by_regime": by_regime,
    }


def build_label_horizon_report(
    ticker_data: dict[str, pd.DataFrame],
    *,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
    thresholds: tuple[float, ...] = DEFAULT_THRESHOLDS,
    vix_df: pd.DataFrame | None = None,
    spy_df: pd.DataFrame | None = None,
    macro_df: pd.DataFrame | None = None,
) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    errors: list[str] = []

    for horizon in horizons:
        for threshold in thresholds:
            frames = []
            for ticker, df in ticker_data.items():
                try:
                    features = build_features(
                        df,
                        prediction_horizon=horizon,
                        target_return_threshold=threshold,
                        vix_df=vix_df,
                        spy_df=spy_df,
                        macro_df=macro_df,
                    )
                except ValueError as exc:
                    errors.append(f"{ticker} h={horizon} t={threshold}: {exc}")
                    continue
                features = _attach_regime(features, spy_df, vix_df)
                features["ticker"] = ticker
                frames.append(features[["date", "ticker", "regime", "target", "future_return"]])
            if not frames:
                continue
            dataset = pd.concat(frames, ignore_index=True)
            candidates.append(
                _candidate_summary(dataset, horizon=horizon, threshold=threshold)
            )

    if not candidates:
        report = {
            "generated_at": _utc_now_iso(),
            "status": "missing_data",
            "candidates": [],
            "best_candidate": None,
            "recommendation": "No candidates could be evaluated; check price data coverage.",
            "errors": errors[:20],
        }
        validate_label_horizon_report(report)
        return report

    ranked = sorted(candidates, key=lambda row: float(row["score"]))
    best = ranked[0]
    current = next(
        (
            row
            for row in candidates
            if row["horizon"] == 20 and abs(row["target_return_threshold"] - 0.0) < 1e-12
        ),
        None,
    )
    recommendation = (
        f"Try horizon={best['horizon']} target>{best['target_return_threshold']:.2%} "
        "in the next retrain candidate."
    )
    if current and best["horizon"] == 20 and best["target_return_threshold"] == 0.0:
        recommendation = "Current 20-day >0% label is the best balance candidate in this grid."

    report = {
        "generated_at": _utc_now_iso(),
        "status": "ok",
        "candidates": ranked,
        "best_candidate": best,
        "current_label": current,
        "recommendation": recommendation,
        "errors": errors[:20],
    }
    validate_label_horizon_report(report)
    return report


def validate_label_horizon_report(report: dict[str, Any]) -> dict[str, Any]:
    missing = [key for key in LABEL_HORIZON_REPORT_KEYS if key not in report]
    if missing:
        raise ValueError(f"Missing label horizon report keys: {missing}")
    return report


def write_label_horizon_report(
    report: dict[str, Any],
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "label_horizon_report.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate AI label horizon candidates")
    parser.add_argument("--horizons", default="5,10,20,40")
    parser.add_argument("--thresholds", default="0,0.02,0.05,0.10")
    parser.add_argument("--period", default="5y")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    settings = load_settings()
    tickers = list(dict.fromkeys(list(settings.tickers) + ["^VIX", "SPY"]))
    loaded = load_price_data_batch(tickers, period=args.period)
    ticker_data = {ticker: loaded[ticker] for ticker in settings.tickers if ticker in loaded}
    vix_df = loaded.get("^VIX")
    spy_df = loaded.get("SPY")
    macro_df = load_macro_data(period=args.period)
    report = build_label_horizon_report(
        ticker_data,
        horizons=_parse_int_list(args.horizons),
        thresholds=_parse_float_list(args.thresholds),
        vix_df=vix_df,
        spy_df=spy_df,
        macro_df=macro_df if not macro_df.empty else None,
    )
    path = write_label_horizon_report(report, args.output_dir)
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
