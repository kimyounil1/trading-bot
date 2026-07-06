"""News-sentiment rank-feature research via cross-sectional IC.

Consumes the Alpaca headline backfill (scripts/news_sentiment_backfill.py,
data/news_history/) and scores headlines with the same VADER analyzer used live
(src/news_sentiment). Same IC methodology as the other feature research scripts.

Point-in-time rule: headlines are bucketed by their US/Eastern calendar date and only
become usable on the NEXT trading day, so day D features see articles up to D-1.

Candidate features:
  - news_sent_1d   : mean VADER compound of D-1 articles
  - news_sent_5d   : article-count-weighted mean compound over [D-5, D-1]
  - news_vol_surge : log1p(articles in [D-5, D-1]) - log1p(5 * daily avg over [D-60, D-1])
  - news_sent_x_vol: news_sent_5d * log1p(article count over [D-5, D-1])

Baseline reference (same panel): return_20d, high_52w_ratio, ma_ratio_10_50.

Usage:
  .venv/bin/python -m scripts.news_feature_research --horizon 20
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.earnings_feature_research import build_baseline_features, load_daily

NEWS_HISTORY_DIR = Path("data/news_history")

BASELINE = ["return_20d", "high_52w_ratio", "ma_ratio_10_50"]
CANDIDATES = ["news_sent_1d", "news_sent_5d", "news_vol_surge", "news_sent_x_vol"]


def _score_headlines(headlines: pd.Series, analyzer) -> pd.Series:
    unique = headlines.dropna().unique()
    scores = {h: analyzer.polarity_scores(h)["compound"] for h in unique}
    return headlines.map(scores)


def load_daily_news_aggregate(ticker: str, analyzer) -> pd.DataFrame | None:
    """Per US/Eastern calendar date: mean compound + article count."""
    path = NEWS_HISTORY_DIR / f"{ticker}.csv"
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path)
    except Exception:
        return None
    if df.empty or "headline" not in df.columns:
        return None
    ts = pd.to_datetime(df["created_at"], errors="coerce", utc=True)
    df = df.assign(et_date=ts.dt.tz_convert("US/Eastern").dt.normalize().dt.tz_localize(None))
    df = df.dropna(subset=["et_date", "headline"])
    if df.empty:
        return None
    df["compound"] = _score_headlines(df["headline"], analyzer)
    agg = (
        df.groupby("et_date")
        .agg(sent_mean=("compound", "mean"), n_articles=("compound", "size"))
        .sort_index()
    )
    return agg


def build_news_features(price_df: pd.DataFrame, agg: pd.DataFrame) -> pd.DataFrame:
    """Daily calendar rollups, shifted so trading day D only sees up to D-1."""
    df = price_df.copy().reset_index(drop=True)
    full_range = pd.date_range(agg.index.min(), df["date"].max(), freq="D")
    daily = agg.reindex(full_range)
    counts = daily["n_articles"].fillna(0.0)
    sent_weighted = (daily["sent_mean"] * daily["n_articles"]).fillna(0.0)

    count_5d = counts.rolling(5).sum()
    sent_5d = sent_weighted.rolling(5).sum() / count_5d.replace(0, np.nan)
    avg_daily_60d = counts.rolling(60).mean()
    vol_surge = np.log1p(count_5d) - np.log1p(5.0 * avg_daily_60d)

    feats = pd.DataFrame(
        {
            "news_sent_1d": daily["sent_mean"],
            "news_sent_5d": sent_5d,
            "news_vol_surge": vol_surge,
            "news_sent_x_vol": sent_5d * np.log1p(count_5d),
        },
        index=full_range,
    )
    # Trading day D reads the rollup as of calendar day D-1.
    lookup = df["date"] - pd.Timedelta(days=1)
    aligned = feats.reindex(lookup)
    aligned.index = df.index
    return pd.concat([df, aligned], axis=1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizon", type=int, default=20)
    ap.add_argument("--min-names", type=int, default=20)
    args = ap.parse_args()

    from src.news_sentiment import _get_vader
    from src.settings import load_settings

    analyzer = _get_vader()
    tickers = [str(t).strip().upper() for t in load_settings().tickers]

    panels = []
    covered = 0
    for t in tickers:
        price_df = load_daily(t)
        if price_df is None:
            continue
        agg = load_daily_news_aggregate(t, analyzer)
        if agg is None or agg.empty:
            continue
        covered += 1
        f = build_news_features(price_df, agg)
        f = build_baseline_features(f)
        f["fwd_return"] = f["close"].shift(-args.horizon) / f["close"] - 1.0
        f["ticker"] = t
        # Restrict to the news coverage window (plus warmup for the 60d baseline).
        f = f[f["date"] >= agg.index.min() + pd.Timedelta(days=60)]
        panels.append(f[["date", "ticker", "fwd_return"] + BASELINE + CANDIDATES])

    panel = pd.concat(panels, ignore_index=True)
    print(
        f"Panel: {panel['ticker'].nunique()} names, {panel['date'].nunique()} days, "
        f"{len(panel):,} rows, horizon={args.horizon}d (news coverage for {covered})\n"
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
    print(f"{'feature':<18} {'kind':<10} {'meanIC':>8} {'t-stat':>7} {'IR':>7} {'hit%':>6} {'days':>6}  edge?")
    for feat in sorted(features, key=lambda x: -abs(results[x].get("mean_ic") or 0)):
        r = results[feat]
        if r.get("mean_ic") is None:
            print(f"{feat:<18} no data")
            continue
        strong = abs(r["t_stat"]) >= 2.0
        beats = abs(r["mean_ic"]) >= base_best * 0.9
        flag = ""
        if r["kind"] == "candidate":
            flag = "ADOPT" if (strong and beats) else ("weak-edge" if strong else "no-edge")
        print(
            f"{feat:<18} {r['kind']:<10} {r['mean_ic']:>8.4f} {r['t_stat']:>7.2f} "
            f"{r['ir']:>7.3f} {r['hit_rate']:>6.1f} {r['n_days']:>6}  {flag}"
        )

    out = Path("reports/news_feature_ic.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {"horizon": args.horizon, "base_best_ic": round(base_best, 4), "results": results},
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nbase_best|IC|={base_best:.4f}  (candidates must approach/beat this with |t|>=2)")
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
