"""Rank AI enhancement suite: label variants, exit sweep, rank-percentile sizing.

Runs three offline experiments (paper config unchanged):
  1) Rank label: raw vs risk-adjusted vs SPY-excess percentile labels
  2) Exit params: focused grid with rank gate on (2y cached)
  3) Position sizing: flat vs rank-percentile-scaled notional

Usage:
  .venv/bin/python -m scripts.rank_enhancement_suite
  .venv/bin/python -m scripts.rank_enhancement_suite --skip-exit   # faster
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone
from itertools import product
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier, LGBMRegressor
from sklearn.metrics import brier_score_loss, mean_squared_error, roc_auc_score

from src.data_loader import load_cached_price_data_batch, load_price_data_batch
from src.features import FEATURE_COLUMNS, build_features
from src.macro_loader import load_macro_data
from src.portfolio_backtest_settings import portfolio_backtest_kwargs
from src.portfolio_backtester import run_portfolio_backtest
from src.rank_label_experiment import RankExperimentConfig, _simulate_top_bucket_portfolio
from src.retrain_holdout import portfolio_holdout_window
from src.settings import load_settings

OUTPUT = Path("reports/rank_enhancement_suite.json")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _mean_cs_ic(scored: pd.DataFrame) -> float:
    ics = []
    for _, g in scored.groupby("date"):
        sub = g[["rank_score", "future_return_percentile"]].dropna()
        if len(sub) < 20:
            continue
        ic = sub["rank_score"].corr(sub["future_return_percentile"], method="spearman")
        if pd.notna(ic):
            ics.append(ic)
    return float(np.mean(ics)) if ics else 0.0


def build_rank_dataset_labeled(
    ticker_data: dict[str, pd.DataFrame],
    *,
    prediction_horizon: int,
    label_mode: str,
    vix_df=None,
    spy_df=None,
    macro_df=None,
) -> pd.DataFrame:
    spy_fwd = None
    if spy_df is not None and not spy_df.empty:
        s = spy_df.copy()
        s["date"] = pd.to_datetime(s["date"])
        s = s.sort_values("date")
        s["spy_fwd"] = s["close"].shift(-prediction_horizon) / s["close"] - 1.0
        spy_fwd = s.set_index("date")["spy_fwd"]

    frames = []
    for ticker, df in ticker_data.items():
        try:
            f = build_features(
                df,
                prediction_horizon=prediction_horizon,
                target_return_threshold=0.0,
                vix_df=vix_df,
                spy_df=spy_df,
                macro_df=macro_df,
            )
        except ValueError:
            continue
        f = f.copy()
        f["ticker"] = ticker
        frames.append(f)
    if not frames:
        raise ValueError("empty rank dataset")
    ds = pd.concat(frames, ignore_index=True)
    ds["date"] = pd.to_datetime(ds["date"])
    ds = ds.dropna(subset=["date", "future_return"]).copy()

    if label_mode == "raw":
        rank_col = "future_return"
    elif label_mode == "risk_adj":
        vol = ds["volatility_20d"].replace(0, np.nan).clip(lower=1e-4)
        ds["label_value"] = ds["future_return"] / vol
        rank_col = "label_value"
    elif label_mode == "excess":
        if spy_fwd is None:
            raise ValueError("SPY required for excess label")
        ds["spy_fwd"] = ds["date"].map(spy_fwd)
        ds["label_value"] = ds["future_return"] - ds["spy_fwd"]
        rank_col = "label_value"
    else:
        raise ValueError(f"unknown label_mode: {label_mode}")

    ds["future_return_percentile"] = ds.groupby("date")[rank_col].rank(
        pct=True, method="average",
    )
    ds = ds.dropna(subset=["future_return_percentile", rank_col]).copy()
    return ds.sort_values(["date", "ticker"]).reset_index(drop=True)


def _train_score_eval(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    ticker_data: dict,
    cfg: RankExperimentConfig,
    *,
    label_name: str,
) -> dict:
    cutoff = 1.0 - cfg.top_bucket_pct
    train = train_df.copy()
    train["top_bucket_label"] = (train["future_return_percentile"] >= cutoff).astype(int)
    test = test_df.copy()
    test["top_bucket_label"] = (test["future_return_percentile"] >= cutoff).astype(int)

    clf = LGBMClassifier(
        n_estimators=200, learning_rate=0.05, max_depth=5, random_state=42,
        n_jobs=-1, verbose=-1,
    )
    reg = LGBMRegressor(
        n_estimators=200, learning_rate=0.05, max_depth=5, random_state=42,
        n_jobs=-1, verbose=-1,
    )
    x_tr = train[FEATURE_COLUMNS]
    clf.fit(x_tr, train["top_bucket_label"])
    reg.fit(x_tr, train["future_return_percentile"])

    scored = test.copy()
    x_te = scored[FEATURE_COLUMNS]
    scored["rank_clf_score"] = clf.predict_proba(x_te)[:, 1]
    scored["rank_reg_score"] = reg.predict(x_te).clip(0, 1)
    scored["rank_score"] = (scored["rank_clf_score"] + scored["rank_reg_score"]) / 2
    scored["predicted_score_percentile"] = scored.groupby("date")["rank_score"].rank(
        pct=True, method="average",
    )

    try:
        auc = float(roc_auc_score(scored["top_bucket_label"], scored["rank_clf_score"]))
    except ValueError:
        auc = None
    brier = float(brier_score_loss(scored["top_bucket_label"], scored["rank_clf_score"]))
    rmse = float(mean_squared_error(scored["future_return_percentile"], scored["rank_reg_score"]) ** 0.5)
    ic = _mean_cs_ic(scored)
    port, _, _ = _simulate_top_bucket_portfolio(scored, ticker_data, cfg)
    return {
        "label": label_name,
        "top_bucket_auc": round(auc, 4) if auc else None,
        "brier": round(brier, 4),
        "rmse": round(rmse, 4),
        "mean_cs_ic": round(ic, 4),
        "portfolio_gap_pct": round(port["gap_pct"], 2),
        "portfolio_sharpe": round(port["sharpe_ratio"], 3),
        "portfolio_mdd": round(port["max_drawdown"], 4),
    }


def run_label_experiments(ticker_data, vix_df, spy_df, macro_df) -> dict:
    cfg = RankExperimentConfig(prediction_horizon=20, top_bucket_pct=0.15, min_score_quantile=0.85)
    holdout_start, holdout_end = portfolio_holdout_window(ticker_data)
    results = {}
    for mode, name in [("raw", "raw_return"), ("risk_adj", "risk_adjusted"), ("excess", "spy_excess")]:
        ds = build_rank_dataset_labeled(
            ticker_data, prediction_horizon=20, label_mode=mode,
            vix_df=vix_df, spy_df=spy_df, macro_df=macro_df,
        )
        train = ds[ds["date"] < holdout_start]
        test = ds[(ds["date"] >= holdout_start) & (ds["date"] <= holdout_end)]
        results[name] = _train_score_eval(train, test, ticker_data, cfg, label_name=name)

    best = max(results.items(), key=lambda kv: (kv[1]["mean_cs_ic"], kv[1].get("top_bucket_auc") or 0))
    raw = results["raw_return"]
    winner_passes = (
        best[0] != "raw_return"
        and best[1]["mean_cs_ic"] >= raw["mean_cs_ic"] + 0.003
        and best[1]["portfolio_gap_pct"] >= raw["portfolio_gap_pct"] - 2.0
    )
    return {
        "variants": results,
        "winner": best[0],
        "promote": winner_passes,
        "note": "Promote only if non-raw label beats raw on IC+portfolio gate",
    }


def _risk_adj(ret: float, mdd: float) -> float:
    return ret / abs(mdd) if mdd != 0 else 0.0


def _portfolio_backtest_base_kw(
    settings,
    ticker_data: dict,
    loaded: dict,
    vix_df,
    macro_df,
    holdout_start,
    holdout_end,
) -> dict:
    benchmark_df = (
        loaded.get(settings.market_regime_ticker)
        if settings.market_regime_filter_enabled
        else None
    )
    relative_strength_benchmark_df = (
        loaded.get(settings.relative_strength_benchmark_ticker)
        if settings.relative_strength_filter_enabled
        else None
    )
    return portfolio_backtest_kwargs(
        settings,
        ticker_data=ticker_data,
        benchmark_df=benchmark_df,
        relative_strength_benchmark_df=relative_strength_benchmark_df,
        vix_df=vix_df,
        macro_df=macro_df,
        evaluation_start_date=holdout_start,
        evaluation_end_date=holdout_end,
        initial_cash=100_000.0,
    )


def run_exit_sweep(
    settings, ticker_data, loaded, vix_df, macro_df, holdout_start, holdout_end,
) -> dict:
    base_kw = _portfolio_backtest_base_kw(
        settings, ticker_data, loaded, vix_df, macro_df, holdout_start, holdout_end,
    )
    current = {
        "stop_loss_pct": settings.stop_loss_pct,
        "take_profit_pct": settings.take_profit_pct,
        "trailing_stop_pct": settings.trailing_stop_pct,
    }
    rows = []
    grid_stop = [0.03, 0.05, 0.07]
    grid_trail = [0.08, 0.10, 0.12, 0.15]
    grid_tp = [0.08, 0.10, 0.15]

    for sl, tr, tp in product(grid_stop, grid_trail, grid_tp):
        kw = {**base_kw, "stop_loss_pct": sl, "take_profit_pct": tp, "trailing_stop_pct": tr}
        res, _, _ = run_portfolio_backtest(**kw)
        rows.append({
            "stop_loss_pct": sl,
            "take_profit_pct": tp,
            "trailing_stop_pct": tr,
            "total_return_pct": round(res.total_return * 100, 2),
            "benchmark_return_pct": round(res.benchmark_return * 100, 2),
            "gap_pct": round((res.total_return - res.benchmark_return) * 100, 2),
            "max_drawdown_pct": round(res.max_drawdown * 100, 2),
            "sharpe": round(res.sharpe_ratio, 3),
            "trades": res.trades,
            "risk_adj": round(_risk_adj(res.total_return, res.max_drawdown), 3),
            "is_current": sl == current["stop_loss_pct"] and tr == current["trailing_stop_pct"] and tp == current["take_profit_pct"],
        })

    cur = next(r for r in rows if r["is_current"])
    best = max(rows, key=lambda r: (r["risk_adj"], r["gap_pct"]))
    promote = (
        best["risk_adj"] > cur["risk_adj"] * 1.05
        and best["gap_pct"] >= cur["gap_pct"] - 1.0
        and best["max_drawdown_pct"] >= cur["max_drawdown_pct"] - 2.0
    )
    rows.sort(key=lambda r: -r["risk_adj"])
    return {
        "current_config": cur,
        "best": best,
        "promote": promote,
        "top5": rows[:5],
    }


def run_sizing_experiment(
    settings, ticker_data, loaded, vix_df, macro_df, holdout_start, holdout_end,
) -> dict:
    base_kw = _portfolio_backtest_base_kw(
        settings, ticker_data, loaded, vix_df, macro_df, holdout_start, holdout_end,
    )
    variants = {
        "flat": {"rank_position_sizing_enabled": False},
        "rank_linear_0.6_1.25": {
            "rank_position_sizing_enabled": True,
            "rank_position_sizing_min_mult": 0.6,
            "rank_position_sizing_max_mult": 1.25,
        },
        "rank_linear_0.5_1.4": {
            "rank_position_sizing_enabled": True,
            "rank_position_sizing_min_mult": 0.5,
            "rank_position_sizing_max_mult": 1.4,
        },
    }
    results = {}
    for name, extra in variants.items():
        res, _, _ = run_portfolio_backtest(**{**base_kw, **extra})
        results[name] = {
            "total_return_pct": round(res.total_return * 100, 2),
            "gap_pct": round((res.total_return - res.benchmark_return) * 100, 2),
            "max_drawdown_pct": round(res.max_drawdown * 100, 2),
            "sharpe": round(res.sharpe_ratio, 3),
            "trades": res.trades,
        }
    flat = results["flat"]
    best_name = max(results, key=lambda k: (results[k]["sharpe"], results[k]["gap_pct"]))
    best = results[best_name]
    promote = (
        best_name != "flat"
        and best["sharpe"] >= flat["sharpe"] + 0.05
        and best["gap_pct"] >= flat["gap_pct"] - 1.0
    )
    return {"variants": results, "best": best_name, "promote": promote}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-exit", action="store_true", help="skip exit grid (slow)")
    args = ap.parse_args()

    settings = load_settings()
    print("=== 1) Label experiments ===")
    loaded = load_price_data_batch(
        list(dict.fromkeys(list(settings.tickers) + ["^VIX", "SPY"])), period="5y",
    )
    ticker_data = {t: loaded[t] for t in settings.tickers if t in loaded}
    vix_df = loaded.get("^VIX")
    spy_df = loaded.get("SPY")
    try:
        macro_df = load_macro_data()
    except Exception:
        macro_df = None
    label_report = run_label_experiments(ticker_data, vix_df, spy_df, macro_df)
    for k, v in label_report["variants"].items():
        print(f"  {k:<16} AUC={v['top_bucket_auc']} IC={v['mean_cs_ic']} gap={v['portfolio_gap_pct']}%")
    print(f"  winner={label_report['winner']} promote={label_report['promote']}\n")

    print("=== 2) Exit sweep (holdout, rank gate) ===" if not args.skip_exit else "=== 2) Exit sweep SKIPPED ===")
    cached = load_cached_price_data_batch(settings.tickers, period="2y")
    aux_tickers = []
    if settings.market_regime_filter_enabled:
        aux_tickers.append(settings.market_regime_ticker)
    if settings.relative_strength_filter_enabled:
        aux_tickers.append(settings.relative_strength_benchmark_ticker)
    for t in dict.fromkeys(aux_tickers):
        if t not in cached:
            cached[t] = load_price_data_batch([t], period="2y")[t]
    ticker_2y = {t: cached[t] for t in settings.tickers if t in cached}
    holdout_start, holdout_end = portfolio_holdout_window(ticker_2y)
    exit_report = None
    if not args.skip_exit:
        exit_report = run_exit_sweep(
            settings, ticker_2y, cached, vix_df, macro_df, holdout_start, holdout_end,
        )
        print(f"  current gap={exit_report['current_config']['gap_pct']}% sharpe={exit_report['current_config']['sharpe']}")
        print(f"  best sl={exit_report['best']['stop_loss_pct']} tr={exit_report['best']['trailing_stop_pct']} "
              f"tp={exit_report['best']['take_profit_pct']} gap={exit_report['best']['gap_pct']}% "
              f"promote={exit_report['promote']}\n")

    print("=== 3) Rank-percentile sizing ===")
    sizing_report = run_sizing_experiment(
        settings, ticker_2y, cached, vix_df, macro_df, holdout_start, holdout_end,
    )
    for k, v in sizing_report["variants"].items():
        print(f"  {k:<22} gap={v['gap_pct']}% sharpe={v['sharpe']} mdd={v['max_drawdown_pct']}%")
    print(f"  best={sizing_report['best']} promote={sizing_report['promote']}\n")

    report = {
        "generated_at": _utc(),
        "holdout": {"start": str(holdout_start.date()), "end": str(holdout_end.date())},
        "label_experiments": label_report,
        "exit_sweep": exit_report,
        "rank_sizing": sizing_report,
        "summary": {
            "label_promote": label_report["promote"],
            "exit_promote": exit_report["promote"] if exit_report else None,
            "sizing_promote": sizing_report["promote"],
        },
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Saved: {OUTPUT}")


if __name__ == "__main__":
    main()
