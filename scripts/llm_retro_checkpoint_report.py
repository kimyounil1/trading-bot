"""Quality + IC checkpoint for LLM retro scoring batch runs.

Writes logs/ml/llm_retro_checkpoint_<label>.json and prints a short summary.
Optional Gemini pilot comparison when data/research/llm_retro_scores.gemini_pilot.jsonl exists.

Usage:
  .venv/bin/python -m scripts.llm_retro_checkpoint_report --label n233
  .venv/bin/python -m scripts.llm_retro_checkpoint_report --label n500 --run-ic
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import pandas as pd

SCORES_PATH = Path("data/research/llm_retro_scores.jsonl")
GEMINI_PILOT_PATH = Path("data/research/llm_retro_scores.gemini_pilot.jsonl")
REPORT_DIR = Path("logs/ml/llm_retro_checkpoints")
TOTAL_TARGET = 9_866


def _load_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _quality_summary(rows: list[dict]) -> dict:
    if not rows:
        return {"count": 0}
    df = pd.DataFrame(rows)
    approved = df["is_approved"]
    outlook = pd.to_numeric(df.get("outlook"), errors="coerce")
    categories = df.get("category", pd.Series(dtype=str)).astype(str)
    return {
        "count": int(len(df)),
        "tickers": int(df["ticker"].nunique()),
        "date_min": str(pd.to_datetime(df["date"]).min().date()),
        "date_max": str(pd.to_datetime(df["date"]).max().date()),
        "provider": df["provider"].value_counts().to_dict() if "provider" in df else {},
        "model": df["model"].value_counts().to_dict() if "model" in df else {},
        "approve_rate": round(float(approved.eq(True).mean()), 4),
        "reject_rate": round(float(approved.eq(False).mean()), 4),
        "approve_null_rate": round(float(approved.isna().mean()), 4),
        "outlook_null_rate": round(float(outlook.isna().mean()), 4),
        "outlook_mean": round(float(outlook.mean()), 3) if outlook.notna().any() else None,
        "category_top": dict(Counter(categories.str.strip()).most_common(8)),
    }


def _gemini_agreement(vllm_rows: list[dict], gemini_rows: list[dict]) -> dict | None:
    if not vllm_rows or not gemini_rows:
        return None
    vdf = pd.DataFrame(vllm_rows).set_index("key")
    gdf = pd.DataFrame(gemini_rows).set_index("key")
    keys = sorted(set(vdf.index) & set(gdf.index))
    if not keys:
        return {"overlap": 0}
    agree_decision = sum(vdf.loc[k, "is_approved"] == gdf.loc[k, "is_approved"] for k in keys)
    outlook_v = pd.to_numeric(vdf.loc[keys, "outlook"], errors="coerce")
    outlook_g = pd.to_numeric(gdf.loc[keys, "outlook"], errors="coerce")
    outlook_pairs = outlook_v.notna() & outlook_g.notna()
    outlook_mae = (
        float((outlook_v[outlook_pairs] - outlook_g[outlook_pairs]).abs().mean())
        if outlook_pairs.any()
        else None
    )
    return {
        "overlap": len(keys),
        "decision_agreement": round(agree_decision / len(keys), 4),
        "outlook_mae": round(outlook_mae, 3) if outlook_mae is not None else None,
    }


def _run_ic(horizon: int) -> dict | None:
    try:
        from scripts.llm_feature_research import (
            BASELINE,
            CANDIDATES,
            build_baseline_features,
            load_daily,
            load_scores,
            merge_scores_onto_prices,
        )
    except ImportError:
        return None

    import numpy as np

    scores = load_scores()
    panels = []
    for ticker, sub in scores.groupby("ticker"):
        price_df = load_daily(str(ticker))
        if price_df is None:
            continue
        f = merge_scores_onto_prices(price_df, sub)
        f = build_baseline_features(f)
        f["fwd_return"] = f["close"].shift(-horizon) / f["close"] - 1.0
        f["ticker"] = ticker
        f = f[f["date"] >= scores["date"].min()]
        panels.append(f[["date", "ticker", "fwd_return"] + BASELINE + CANDIDATES])
    if not panels:
        return {"error": "no_panel"}
    panel = pd.concat(panels, ignore_index=True)
    features = BASELINE + CANDIDATES
    results: dict = {}
    for feat in features:
        daily_ic = []
        for _, g in panel.groupby("date"):
            sub = g[[feat, "fwd_return"]].dropna()
            if len(sub) < 20 or sub[feat].nunique() < 2:
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
            "t_stat": round(float(t_stat), 2),
            "n_days": int(len(arr)),
            "kind": "baseline" if feat in BASELINE else "candidate",
        }
    valid_base = [f for f in BASELINE if results[f].get("mean_ic") is not None]
    base_best = max(abs(results[f]["mean_ic"]) for f in valid_base) if valid_base else 0.0
    return {"horizon": horizon, "base_best_ic": round(base_best, 4), "results": results}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True, help="checkpoint label, e.g. n500 or final")
    ap.add_argument("--run-ic", action="store_true")
    ap.add_argument("--horizon", type=int, default=20)
    ap.add_argument("--target", type=int, default=TOTAL_TARGET)
    args = ap.parse_args()

    rows = _load_jsonl(SCORES_PATH)
    gemini_rows = _load_jsonl(GEMINI_PILOT_PATH)
    quality = _quality_summary(rows)
    quality["progress_pct"] = round(100.0 * quality.get("count", 0) / args.target, 2)

    payload: dict = {
        "label": args.label,
        "scores_path": str(SCORES_PATH),
        "quality": quality,
        "gemini_pilot_comparison": _gemini_agreement(rows, gemini_rows),
    }
    if args.run_ic and quality.get("count", 0) >= 50:
        payload["ic"] = _run_ic(args.horizon)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORT_DIR / f"{args.label}.json"
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"=== LLM retro checkpoint: {args.label} ===")
    print(
        f"scored={quality.get('count', 0):,}/{args.target:,} "
        f"({quality.get('progress_pct', 0):.1f}%)  "
        f"approve={quality.get('approve_rate', 0):.1%}  "
        f"reject={quality.get('reject_rate', 0):.1%}  "
        f"outlook_null={quality.get('outlook_null_rate', 0):.1%}"
    )
    if payload.get("gemini_pilot_comparison"):
        cmp_ = payload["gemini_pilot_comparison"]
        if cmp_.get("overlap"):
            print(
                f"vs gemini pilot: overlap={cmp_['overlap']}  "
                f"decision_agree={cmp_.get('decision_agreement', 0):.1%}  "
                f"outlook_mae={cmp_.get('outlook_mae')}"
            )
    if payload.get("ic"):
        ic = payload["ic"]
        print(f"IC horizon={ic.get('horizon')}d  base_best|IC|={ic.get('base_best_ic')}")
        for feat, r in sorted(
            ic.get("results", {}).items(),
            key=lambda kv: -abs(kv[1].get("mean_ic") or 0),
        ):
            if r.get("mean_ic") is None:
                continue
            tag = "candidate" if r.get("kind") == "candidate" else "baseline"
            print(f"  {feat:<16} {tag:<10} IC={r['mean_ic']:+.4f}  t={r['t_stat']:+.2f}  days={r['n_days']}")
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
