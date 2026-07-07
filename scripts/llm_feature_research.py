"""LLM retro-score rank-feature research via cross-sectional IC.

Consumes data/research/llm_retro_scores.jsonl (scripts/llm_retro_scoring.py) and
runs the same IC screen as the other feature research scripts. Score days are
sparse (only days with news), so values are forward-filled up to 3 trading days —
mirroring how fresh the live veto's context is.

Candidate features:
  - llm_approved : 1/0 APPROVE decision (the validated live signal, retro-applied)
  - llm_outlook  : graded -5..5 outlook
  - llm_risk_flag: 1 when a risk category (Lawsuit/Fraud/Guidance/...) was tagged

Baseline reference (same panel): return_20d, high_52w_ratio, ma_ratio_10_50.
Remember the pretraining-leakage bias: results are optimistic by construction.

Usage:
  .venv/bin/python -m scripts.llm_feature_research --horizon 20
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.earnings_feature_research import build_baseline_features, load_daily

SCORES_PATH = Path("data/research/llm_retro_scores.jsonl")
FFILL_TRADING_DAYS = 3

BASELINE = ["return_20d", "high_52w_ratio", "ma_ratio_10_50"]
CANDIDATES = ["llm_approved", "llm_outlook", "llm_risk_flag"]


def load_scores() -> pd.DataFrame:
    if not SCORES_PATH.is_file():
        raise SystemExit(f"No retro scores yet: {SCORES_PATH} (run scripts.llm_retro_scoring)")
    rows = []
    for line in SCORES_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    df["llm_approved"] = df["is_approved"].map(
        lambda v: 1.0 if v is True else (0.0 if v is False else np.nan)
    )
    df["llm_outlook"] = pd.to_numeric(df["outlook"], errors="coerce")
    category = df["category"].astype(str).str.strip().str.lower()
    df["llm_risk_flag"] = (~category.isin({"none", "", "nan"})).astype(float)
    # a same-day duplicate should not exist, but keep the latest just in case
    return df.drop_duplicates(["ticker", "date"], keep="last")


def merge_scores_onto_prices(price_df: pd.DataFrame, scores: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy().reset_index(drop=True)
    df["date"] = pd.to_datetime(df["date"])
    merged = df.merge(
        scores[["date", "llm_approved", "llm_outlook", "llm_risk_flag"]],
        on="date",
        how="left",
    )
    for col in CANDIDATES:
        merged[col] = merged[col].ffill(limit=FFILL_TRADING_DAYS)
    return merged


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizon", type=int, default=20)
    ap.add_argument("--min-names", type=int, default=20)
    args = ap.parse_args()

    scores = load_scores()
    print(
        f"Retro scores: {len(scores):,} ticker-days, "
        f"{scores['ticker'].nunique()} tickers, "
        f"{scores['date'].min().date()} .. {scores['date'].max().date()}, "
        f"approve rate {scores['llm_approved'].mean():.1%}"
    )

    panels = []
    for ticker, sub in scores.groupby("ticker"):
        price_df = load_daily(str(ticker))
        if price_df is None:
            continue
        f = merge_scores_onto_prices(price_df, sub)
        f = build_baseline_features(f)
        f["fwd_return"] = f["close"].shift(-args.horizon) / f["close"] - 1.0
        f["ticker"] = ticker
        f = f[f["date"] >= scores["date"].min()]
        panels.append(f[["date", "ticker", "fwd_return"] + BASELINE + CANDIDATES])
    panel = pd.concat(panels, ignore_index=True)
    print(
        f"Panel: {panel['ticker'].nunique()} names, {panel['date'].nunique()} days, "
        f"{len(panel):,} rows, horizon={args.horizon}d\n"
    )

    features = BASELINE + CANDIDATES
    results = {}
    for feat in features:
        daily_ic = []
        for _, g in panel.groupby("date"):
            sub = g[[feat, "fwd_return"]].dropna()
            if len(sub) < args.min_names or sub[feat].nunique() < 2:
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

    valid_base = [f for f in BASELINE if results[f].get("mean_ic") is not None]
    base_best = max(abs(results[f]["mean_ic"]) for f in valid_base) if valid_base else 0.0
    print(f"{'feature':<16} {'kind':<10} {'meanIC':>8} {'t-stat':>7} {'IR':>7} {'hit%':>6} {'days':>6}  edge?")
    for feat in sorted(features, key=lambda x: -abs(results[x].get("mean_ic") or 0)):
        r = results[feat]
        if r.get("mean_ic") is None:
            print(f"{feat:<16} no data")
            continue
        strong = abs(r["t_stat"]) >= 2.0
        beats = abs(r["mean_ic"]) >= base_best * 0.9
        flag = ""
        if r["kind"] == "candidate":
            flag = "ADOPT" if (strong and beats) else ("weak-edge" if strong else "no-edge")
        print(
            f"{feat:<16} {r['kind']:<10} {r['mean_ic']:>8.4f} {r['t_stat']:>7.2f} "
            f"{r['ir']:>7.3f} {r['hit_rate']:>6.1f} {r['n_days']:>6}  {flag}"
        )

    out = Path("reports/llm_feature_ic.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "horizon": args.horizon,
                "scored_ticker_days": int(len(scores)),
                "base_best_ic": round(base_best, 4),
                "leakage_note": "LLM pretraining may know post-headline outcomes; optimistic bias",
                "results": results,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nbase_best|IC|={base_best:.4f}  (candidates must approach/beat this with |t|>=2)")
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
