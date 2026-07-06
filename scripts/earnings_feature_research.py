"""Earnings-based rank-feature research via cross-sectional IC.

Same methodology as scripts/rank_feature_research.py (daily cross-sectional Spearman
IC vs forward return), but for point-in-time earnings features built from yfinance
historical earnings dates (10y+ of report dates with EPS estimate/actual/surprise).

Point-in-time rules:
  - Report info (surprise, reaction) becomes usable the NEXT trading day after the
    report date (conservative for after-close reporters).
  - days_to_earnings uses the actual next report date; mild lookahead in that the
    exact date is only announced ~2-4 weeks ahead, acceptable for research.

Candidate features:
  - days_since_earnings : trading days since last report
  - days_to_earnings    : calendar days until next report
  - last_surprise_pct   : EPS surprise % of the most recent report
  - surprise_streak     : consecutive positive-surprise count as of last report
  - pead_react          : close-to-close return around the last report (carried 60d)
  - pead_react_decay    : pead_react * exp(-days_since/20)

Baseline reference (same panel): high_52w_ratio, ma_ratio_10_50, return_20d.

Usage:
  .venv/bin/python -m scripts.earnings_feature_research --horizon 20
"""

from __future__ import annotations

import argparse
import json
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

RAW_DIR = Path("data/raw")
EARNINGS_HISTORY_DIR = Path("data/earnings_history")
PERIOD = "5y"
PEAD_CARRY_DAYS = 60

BASELINE = ["return_20d", "high_52w_ratio", "ma_ratio_10_50"]
CANDIDATES = [
    "days_since_earnings",
    "days_to_earnings",
    "last_surprise_pct",
    "surprise_streak",
    "pead_react",
    "pead_react_decay",
]


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
    df = df.dropna(subset=["close"]).sort_values("date").reset_index(drop=True)
    if len(df) < 260 or df["close"].median() < 5:
        return None
    return df


def fetch_earnings_history(ticker: str, cache_ttl_hours: int = 24 * 7) -> pd.DataFrame | None:
    """Historical report dates + EPS surprise, cached under data/earnings_history/."""
    EARNINGS_HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = EARNINGS_HISTORY_DIR / f"{ticker.upper()}.csv"
    if cache_path.exists():
        age_hours = (time.time() - cache_path.stat().st_mtime) / 3600
        if age_hours < cache_ttl_hours:
            try:
                cached = pd.read_csv(cache_path)
                cached["report_date"] = pd.to_datetime(cached["report_date"])
                return cached
            except Exception:
                pass
    try:
        import yfinance as yf

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            raw = yf.Ticker(ticker).get_earnings_dates(limit=40)
    except Exception:
        return None
    if raw is None or raw.empty:
        return None
    out = pd.DataFrame(
        {
            "report_date": pd.to_datetime(raw.index.tz_localize(None).normalize()),
            "eps_estimate": pd.to_numeric(raw.get("EPS Estimate"), errors="coerce").values,
            "eps_reported": pd.to_numeric(raw.get("Reported EPS"), errors="coerce").values,
            "surprise_pct": pd.to_numeric(raw.get("Surprise(%)"), errors="coerce").values,
        }
    ).sort_values("report_date").reset_index(drop=True)
    out.to_csv(cache_path, index=False)
    return out


def build_earnings_features(price_df: pd.DataFrame, reports: pd.DataFrame) -> pd.DataFrame:
    """Per trading day: point-in-time features from the report history."""
    df = price_df.copy().reset_index(drop=True)
    dates = df["date"]
    close = df["close"]

    reports = reports.dropna(subset=["report_date"]).sort_values("report_date")
    reports = reports[reports["report_date"] <= dates.max()]

    # Per report: effective date (next trading day) and close-to-close reaction.
    date_index = pd.Series(np.arange(len(dates)), index=dates)
    report_rows = []
    streak = 0
    for _, rep in reports.iterrows():
        rd = rep["report_date"]
        pos_after = int(dates.searchsorted(rd, side="right"))
        if pos_after >= len(dates):
            continue
        pos_before = pos_after - 1
        reaction = np.nan
        if pos_before >= 0:
            prev_close = close.iloc[pos_before]
            eff_close = close.iloc[pos_after]
            if prev_close and prev_close > 0:
                reaction = float(eff_close / prev_close - 1.0)
        surprise = rep["surprise_pct"]
        if pd.notna(surprise):
            streak = streak + 1 if surprise > 0 else 0
        report_rows.append(
            {
                "effective_pos": pos_after,
                "report_date": rd,
                "surprise_pct": surprise,
                "surprise_streak": streak,
                "pead_react": reaction,
            }
        )
    if not report_rows:
        return pd.DataFrame()
    rep_df = pd.DataFrame(report_rows)

    n = len(df)
    days_since = np.full(n, np.nan)
    last_surprise = np.full(n, np.nan)
    surprise_streak = np.full(n, np.nan)
    pead_react = np.full(n, np.nan)
    for _, rep in rep_df.iterrows():
        start = int(rep["effective_pos"])
        days_since[start:] = np.arange(n - start)
        last_surprise[start:] = rep["surprise_pct"]
        surprise_streak[start:] = rep["surprise_streak"]
        pead_react[start:] = rep["pead_react"]

    df["days_since_earnings"] = days_since
    df["last_surprise_pct"] = last_surprise
    df["surprise_streak"] = surprise_streak
    df["pead_react"] = np.where(days_since <= PEAD_CARRY_DAYS, pead_react, np.nan)
    df["pead_react_decay"] = df["pead_react"] * np.exp(-df["days_since_earnings"] / 20.0)

    # days_to_earnings: calendar days until the next report date.
    report_dates = rep_df["report_date"].to_numpy(dtype="datetime64[D]")
    all_reports = reports["report_date"].to_numpy(dtype="datetime64[D]")
    day_arr = dates.to_numpy(dtype="datetime64[D]")
    next_idx = np.searchsorted(all_reports, day_arr, side="right")
    days_to = np.full(n, np.nan)
    valid = next_idx < len(all_reports)
    days_to[valid] = (all_reports[next_idx[valid]] - day_arr[valid]).astype(float)
    df["days_to_earnings"] = days_to
    return df


def build_baseline_features(df: pd.DataFrame) -> pd.DataFrame:
    c = df["close"]
    df["return_20d"] = c.pct_change(20)
    df["high_52w_ratio"] = c / c.rolling(252).max()
    ma10 = c.rolling(10).mean()
    ma50 = c.rolling(50).mean()
    df["ma_ratio_10_50"] = ma10 / ma50 - 1.0
    return df


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizon", type=int, default=20)
    ap.add_argument("--min-names", type=int, default=20)
    args = ap.parse_args()

    from src.settings import load_settings

    tickers = [str(t).strip().upper() for t in load_settings().tickers]

    panels = []
    fetched = 0
    for t in tickers:
        price_df = load_daily(t)
        if price_df is None:
            continue
        reports = fetch_earnings_history(t)
        if reports is None or reports.empty:
            continue
        fetched += 1
        f = build_earnings_features(price_df, reports)
        if f.empty:
            continue
        f = build_baseline_features(f)
        f["fwd_return"] = f["close"].shift(-args.horizon) / f["close"] - 1.0
        f["ticker"] = t
        panels.append(f[["date", "ticker", "fwd_return"] + BASELINE + CANDIDATES])

    panel = pd.concat(panels, ignore_index=True)
    print(
        f"Panel: {panel['ticker'].nunique()} names, {panel['date'].nunique()} days, "
        f"{len(panel):,} rows, horizon={args.horizon}d (earnings history for {fetched})\n"
    )

    features = BASELINE + CANDIDATES
    results = {}
    for feat in features:
        daily_ic = []
        for _, g in panel.groupby("date"):
            sub = g[[feat, "fwd_return"]].dropna()
            if len(sub) < args.min_names:
                continue
            ic = sub[feat].corr(sub["fwd_return"], method="spearman")
            if pd.notna(ic):
                daily_ic.append(ic)
        arr = np.array(daily_ic)
        if len(arr) == 0:
            results[feat] = {"mean_ic": None, "n_days": 0}
            continue
        mean_ic = float(arr.mean())
        std_ic = float(arr.std())
        t_stat = mean_ic / std_ic * np.sqrt(len(arr)) if std_ic > 0 else 0.0
        results[feat] = {
            "mean_ic": round(mean_ic, 4),
            "ic_std": round(std_ic, 4),
            "t_stat": round(float(t_stat), 2),
            "ir": round(mean_ic / std_ic, 3) if std_ic > 0 else 0.0,
            "hit_rate": round(float((arr > 0).mean() * 100), 1),
            "n_days": len(arr),
            "kind": "baseline" if feat in BASELINE else "candidate",
        }

    base_best = max(
        abs(results[f]["mean_ic"]) for f in BASELINE if results[f].get("mean_ic") is not None
    )
    print(f"{'feature':<22} {'kind':<10} {'meanIC':>8} {'t-stat':>7} {'IR':>7} {'hit%':>6} {'days':>6}  edge?")
    for feat in sorted(features, key=lambda x: -abs(results[x].get("mean_ic") or 0)):
        r = results[feat]
        if r.get("mean_ic") is None:
            print(f"{feat:<22} no data")
            continue
        strong = abs(r["t_stat"]) >= 2.0
        beats = abs(r["mean_ic"]) >= base_best * 0.9
        flag = ""
        if r["kind"] == "candidate":
            flag = "ADOPT" if (strong and beats) else ("weak-edge" if strong else "no-edge")
        print(
            f"{feat:<22} {r['kind']:<10} {r['mean_ic']:>8.4f} {r['t_stat']:>7.2f} "
            f"{r['ir']:>7.3f} {r['hit_rate']:>6.1f} {r['n_days']:>6}  {flag}"
        )

    out = Path("reports/earnings_feature_ic.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {"horizon": args.horizon, "period": PERIOD, "base_best_ic": round(base_best, 4), "results": results},
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nbase_best|IC|={base_best:.4f}  (candidates must approach/beat this with |t|>=2)")
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
