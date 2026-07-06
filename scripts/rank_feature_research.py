"""Rank-feature edge research via cross-sectional Information Coefficient (IC).

The rank AI gate ranks stocks cross-sectionally each day, so the right test for a
candidate feature is the cross-sectional IC: each day, Spearman-rank-correlate the
feature across all names with the *forward* return; average the daily ICs.

This validates feature edge WITHOUT touching the production model
(`rank_models.joblib`). Only features that beat the existing baseline ICs should be
promoted (then a separate gated retrain).

Candidate (learnable) features distilled from the PBA discretionary playbook:
  - rs_60d / rs_120d   : multi-horizon relative strength vs SPY (PBA "Holy RS")
  - vol_contraction    : vol_10d / vol_60d  (VCP / tight base; <1 = contracting)
  - gap_vol_20d        : max 1-day gap-up over 20d x volume surge (earnings-gap proxy)
  - up_day_frac_20d    : fraction of up days in 20d (momentum persistence)
  - dist_52w_high      : closeness to 52w high (leadership)

Baseline (already in FEATURE_COLUMNS):
  - return_20d, spy_rel_return_20d, rsi_14, high_52w_ratio, ma_ratio_10_50

Usage:
  .venv/bin/python -m scripts.rank_feature_research --horizon 20
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

RAW_DIR = Path("data/raw")
PERIOD = "2y"


def load_daily(ticker: str) -> pd.DataFrame | None:
    path = RAW_DIR / ticker / f"{PERIOD}.csv"
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path)
    except Exception:
        return None
    if df.empty or not {"date", "open", "high", "low", "close", "volume"} <= set(df.columns):
        return None
    df["date"] = pd.to_datetime(df["date"])
    df = df.dropna(subset=["open", "high", "low", "close"]).sort_values("date").reset_index(drop=True)
    if len(df) < 260 or df["close"].median() < 5:
        return None
    dollar_vol = (df["close"] * df["volume"]).median()
    if dollar_vol < 5_000_000:
        return None
    if df["close"].pct_change().abs().max() > 1.0:
        return None
    return df


def build_features(df: pd.DataFrame, spy_close: pd.Series, horizon: int) -> pd.DataFrame:
    df = df.copy()
    c = df["close"]
    # --- baseline (existing) ---
    df["return_20d"] = c.pct_change(20)
    spy = df["date"].map(spy_close)
    df["spy_rel_return_20d"] = df["return_20d"] - spy.pct_change(20).values \
        if False else df["return_20d"] - (spy / spy.shift(20) - 1.0)
    delta = c.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df["rsi_14"] = 100 - 100 / (1 + rs)
    df["high_52w_ratio"] = c / c.rolling(252).max()
    ma10 = c.rolling(10).mean(); ma50 = c.rolling(50).mean()
    df["ma_ratio_10_50"] = ma10 / ma50 - 1.0
    # --- candidates ---
    df["rs_60d"] = c.pct_change(60) - (spy / spy.shift(60) - 1.0)
    df["rs_120d"] = c.pct_change(120) - (spy / spy.shift(120) - 1.0)
    ret1 = c.pct_change()
    vol10 = ret1.rolling(10).std(); vol60 = ret1.rolling(60).std()
    df["vol_contraction"] = vol10 / vol60.replace(0, np.nan)
    gap = (df["open"] / c.shift(1) - 1.0).clip(lower=0)
    vol_surge = df["volume"] / df["volume"].rolling(20).mean()
    df["gap_vol_20d"] = (gap * vol_surge).rolling(20).max()
    df["up_day_frac_20d"] = (ret1 > 0).rolling(20).mean()
    df["dist_52w_high"] = df["high_52w_ratio"]  # higher = nearer high
    # --- forward target ---
    df["fwd_return"] = c.shift(-horizon) / c - 1.0
    return df


FEATURES = [
    # baseline
    "return_20d", "spy_rel_return_20d", "rsi_14", "high_52w_ratio", "ma_ratio_10_50",
    # candidates
    "rs_60d", "rs_120d", "vol_contraction", "gap_vol_20d", "up_day_frac_20d",
]
BASELINE = {"return_20d", "spy_rel_return_20d", "rsi_14", "high_52w_ratio", "ma_ratio_10_50"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizon", type=int, default=20)
    ap.add_argument("--min-names", type=int, default=20, help="min names/day for IC")
    args = ap.parse_args()

    spy = load_daily("SPY")
    if spy is None:
        raise SystemExit("SPY cache required")
    spy_close = spy.set_index("date")["close"]

    tickers = sorted(p.parent.name for p in RAW_DIR.glob(f"*/{PERIOD}.csv"))
    tickers = [t for t in tickers if t not in {"SPY", "QQQ", "DIA", "IWM"}]

    panels = []
    for t in tickers:
        df = load_daily(t)
        if df is None:
            continue
        f = build_features(df, spy_close, args.horizon)
        f["ticker"] = t
        panels.append(f[["date", "ticker", "fwd_return"] + FEATURES])
    panel = pd.concat(panels, ignore_index=True)
    print(f"Panel: {panel['ticker'].nunique()} names, {panel['date'].nunique()} days, "
          f"{len(panel):,} rows, horizon={args.horizon}d\n")

    # cross-sectional IC per day, then average over time
    results = {}
    for feat in FEATURES:
        daily_ic = []
        for _, g in panel.groupby("date"):
            sub = g[[feat, "fwd_return"]].dropna()
            if len(sub) < args.min_names:
                continue
            ic = sub[feat].corr(sub["fwd_return"], method="spearman")
            if pd.notna(ic):
                daily_ic.append(ic)
        arr = np.array(daily_ic)
        mean_ic = arr.mean()
        std_ic = arr.std()
        t_stat = mean_ic / std_ic * np.sqrt(len(arr)) if std_ic > 0 else 0.0
        results[feat] = {
            "mean_ic": round(float(mean_ic), 4),
            "ic_std": round(float(std_ic), 4),
            "t_stat": round(float(t_stat), 2),
            "ir": round(float(mean_ic / std_ic), 3) if std_ic > 0 else 0.0,
            "hit_rate": round(float((arr > 0).mean() * 100), 1),
            "n_days": len(arr),
            "kind": "baseline" if feat in BASELINE else "candidate",
        }

    base_best = max(abs(results[f]["mean_ic"]) for f in BASELINE)
    print(f"{'feature':<20} {'kind':<10} {'meanIC':>8} {'t-stat':>7} {'IR':>7} "
          f"{'hit%':>6} {'days':>6}  edge?")
    for feat in sorted(FEATURES, key=lambda x: -abs(results[x]["mean_ic"])):
        r = results[feat]
        # meaningful edge: |t|>=2 AND beats best baseline |IC| (for candidates)
        strong = abs(r["t_stat"]) >= 2.0
        beats = abs(r["mean_ic"]) >= base_best * 0.9
        flag = ""
        if r["kind"] == "candidate":
            flag = "ADOPT" if (strong and beats) else ("weak-edge" if strong else "no-edge")
        print(f"{feat:<20} {r['kind']:<10} {r['mean_ic']:>8.4f} {r['t_stat']:>7.2f} "
              f"{r['ir']:>7.3f} {r['hit_rate']:>6.1f} {r['n_days']:>6}  {flag}")

    out = Path("reports/rank_feature_ic.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"horizon": args.horizon, "base_best_ic": round(base_best, 4),
                               "results": results}, indent=2), encoding="utf-8")
    print(f"\nbase_best|IC|={base_best:.4f}  (candidates must approach/beat this with |t|>=2)")
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
