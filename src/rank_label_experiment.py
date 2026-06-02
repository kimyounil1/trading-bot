"""Cross-sectional rank-label AI experiment.

This is research-only: it does not replace the production champion model.

Experiment design:
- Build future-return percentile per date across the universe.
- Train models to predict top-bucket membership / percentile rank.
- In OOS portfolio simulation, keep existing exit rules and only allow buys from
  the predicted top bucket.
- Gate on portfolio curve, drawdown, turnover, and benchmark gap.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from lightgbm import LGBMClassifier, LGBMRegressor
from sklearn.metrics import mean_squared_error, roc_auc_score

from src.data_loader import load_price_data_batch
from src.features import FEATURE_COLUMNS, build_features
from src.macro_loader import load_macro_data
from src.portfolio_backtester import _build_equal_weight_benchmark_values
from src.retrain_holdout import exclude_holdout_from_ticker_data, portfolio_holdout_window
from src.settings import load_settings


DEFAULT_OUTPUT_DIR = Path("logs/ml/rank_label_experiment")
DEFAULT_TOP_BUCKET_PCT = 0.30

RANK_LABEL_REPORT_KEYS = (
    "generated_at",
    "label",
    "metrics",
    "portfolio_oos",
    "benchmark_oos",
    "gate",
    "recommendation",
    "artifacts",
)


@dataclass(frozen=True)
class RankExperimentConfig:
    prediction_horizon: int = 20
    top_bucket_pct: float = DEFAULT_TOP_BUCKET_PCT
    period: str = "5y"
    max_positions: int = 12
    target_position_pct: float = 0.15
    stop_loss_pct: float = 0.05
    take_profit_pct: float = 0.10
    trailing_stop_pct: float = 0.20
    min_score_quantile: float = 0.70
    max_turnover_proxy: float = 1.20
    initial_cash: float = 10_000.0
    transaction_cost_pct: float = 0.001


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_rank_dataset(
    ticker_data: dict[str, pd.DataFrame],
    *,
    prediction_horizon: int,
    vix_df: pd.DataFrame | None = None,
    spy_df: pd.DataFrame | None = None,
    macro_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for ticker, df in ticker_data.items():
        try:
            features = build_features(
                df,
                prediction_horizon=prediction_horizon,
                target_return_threshold=0.0,
                vix_df=vix_df,
                spy_df=spy_df,
                macro_df=macro_df,
            )
        except ValueError:
            continue
        features = features.copy()
        features["ticker"] = ticker
        frames.append(features)
    if not frames:
        raise ValueError("No feature frames available for rank experiment")

    dataset = pd.concat(frames, ignore_index=True)
    dataset["date"] = pd.to_datetime(dataset["date"], errors="coerce")
    dataset = dataset.dropna(subset=["date", "future_return"]).copy()
    # Percentile rank inside each date. Higher future return = higher percentile.
    dataset["future_return_percentile"] = dataset.groupby("date")["future_return"].rank(
        pct=True,
        method="average",
    )
    return dataset.sort_values(["date", "ticker"]).reset_index(drop=True)


def _train_rank_models(train_df: pd.DataFrame, top_bucket_pct: float) -> tuple[Any, Any]:
    train_df = train_df.copy()
    cutoff = 1.0 - top_bucket_pct
    train_df["top_bucket_label"] = (
        train_df["future_return_percentile"] >= cutoff
    ).astype(int)
    classifier = LGBMClassifier(
        n_estimators=250,
        learning_rate=0.04,
        max_depth=5,
        num_leaves=31,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=42,
        n_jobs=-1,
        verbose=-1,
    )
    regressor = LGBMRegressor(
        n_estimators=250,
        learning_rate=0.04,
        max_depth=5,
        num_leaves=31,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=42,
        n_jobs=-1,
        verbose=-1,
    )
    x_train = train_df[FEATURE_COLUMNS]
    classifier.fit(x_train, train_df["top_bucket_label"])
    regressor.fit(x_train, train_df["future_return_percentile"])
    return classifier, regressor


def _score_oos(
    test_df: pd.DataFrame,
    *,
    classifier: Any,
    regressor: Any,
    top_bucket_pct: float,
) -> pd.DataFrame:
    out = test_df.copy()
    x_test = out[FEATURE_COLUMNS]
    cutoff = 1.0 - top_bucket_pct
    out["top_bucket_label"] = (out["future_return_percentile"] >= cutoff).astype(int)
    out["rank_clf_score"] = classifier.predict_proba(x_test)[:, 1]
    out["rank_reg_score"] = regressor.predict(x_test).clip(0.0, 1.0)
    # Blend classification confidence with percentile regression. This is still
    # research-only and intentionally simple.
    out["rank_score"] = (out["rank_clf_score"] + out["rank_reg_score"]) / 2.0
    out["predicted_score_percentile"] = out.groupby("date")["rank_score"].rank(
        pct=True,
        method="average",
    )
    return out


def _exit_reason(pos: dict[str, Any], price: float, cfg: RankExperimentConfig) -> str | None:
    entry = float(pos["entry_price"])
    if price <= 0 or entry <= 0:
        return None
    pnl = price / entry - 1.0
    if cfg.stop_loss_pct > 0 and pnl <= -cfg.stop_loss_pct:
        return "stop_loss"
    if cfg.take_profit_pct > 0 and pnl >= cfg.take_profit_pct:
        return "take_profit"
    highest = max(float(pos.get("highest_price", entry)), price)
    pos["highest_price"] = highest
    if cfg.trailing_stop_pct > 0 and price < highest * (1.0 - cfg.trailing_stop_pct):
        return "trailing_stop"
    return None


def _simulate_top_bucket_portfolio(
    scored_df: pd.DataFrame,
    ticker_data: dict[str, pd.DataFrame],
    cfg: RankExperimentConfig,
) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame]:
    cash = cfg.initial_cash
    positions: dict[str, dict[str, Any]] = {}
    trades: list[dict[str, Any]] = []
    equity_rows: list[dict[str, Any]] = []

    dates = sorted(scored_df["date"].dropna().unique())
    score_cutoff = cfg.min_score_quantile

    for current_date in dates:
        day_df = scored_df[scored_df["date"] == current_date].copy()
        prices = {row["ticker"]: float(row["close"]) for _, row in day_df.iterrows()}

        # Existing exit rules remain structural; rank model only gates buys/adds.
        for ticker in list(positions.keys()):
            if ticker not in prices:
                continue
            pos = positions[ticker]
            price = prices[ticker]
            reason = _exit_reason(pos, price, cfg)
            if reason is None:
                pos["last_price"] = price
                continue
            exit_value = pos["qty"] * price
            cash += exit_value * (1.0 - cfg.transaction_cost_pct)
            trades.append(
                {
                    "ticker": ticker,
                    "entry_date": pos["entry_date"],
                    "exit_date": current_date,
                    "entry_price": pos["entry_price"],
                    "exit_price": price,
                    "cost_basis": pos["cost_basis"],
                    "exit_value": exit_value,
                    "return_pct": price / pos["entry_price"] - 1.0,
                    "reason": reason,
                }
            )
            del positions[ticker]

        positions_value = sum(
            pos["qty"] * prices.get(ticker, pos["last_price"])
            for ticker, pos in positions.items()
        )
        equity = cash + positions_value

        allowed = day_df[
            (day_df["predicted_score_percentile"] >= score_cutoff)
            & (~day_df["ticker"].isin(positions.keys()))
        ].sort_values("rank_score", ascending=False)
        slots_left = max(cfg.max_positions - len(positions), 0)
        selected = allowed.head(slots_left)

        for _, row in selected.iterrows():
            price = float(row["close"])
            if price <= 0 or cash <= 0:
                continue
            target_value = equity * cfg.target_position_pct
            available = min(cash, target_value)
            if available <= 0:
                continue
            net = available * (1.0 - cfg.transaction_cost_pct)
            qty = net / price
            cash -= available
            positions[str(row["ticker"])] = {
                "qty": qty,
                "entry_price": price,
                "entry_date": current_date,
                "cost_basis": available,
                "last_price": price,
                "highest_price": price,
            }

        for ticker, pos in positions.items():
            if ticker in prices:
                pos["last_price"] = prices[ticker]
        positions_value = sum(pos["qty"] * pos["last_price"] for pos in positions.values())
        equity_rows.append(
            {
                "date": current_date,
                "cash": cash,
                "positions_value": positions_value,
                "equity": cash + positions_value,
                "positions_count": len(positions),
                "open_symbols": ",".join(sorted(positions.keys())),
            }
        )

    equity_df = pd.DataFrame(equity_rows)
    if equity_df.empty:
        raise ValueError("No equity rows generated")
    equity_df["daily_return"] = equity_df["equity"].pct_change().fillna(0.0)
    equity_df["running_max"] = equity_df["equity"].cummax()
    equity_df["drawdown"] = equity_df["equity"] / equity_df["running_max"] - 1.0
    benchmark_values = _build_equal_weight_benchmark_values(
        equity_df["date"],
        ticker_data,
        cfg.initial_cash,
    )
    equity_df["benchmark_equity"] = benchmark_values
    trades_df = pd.DataFrame(trades)
    final_equity = float(equity_df["equity"].iloc[-1])
    benchmark_equity = float(equity_df["benchmark_equity"].iloc[-1])
    daily_std = float(equity_df["daily_return"].std())
    sharpe = (
        float(equity_df["daily_return"].mean() / daily_std * (252**0.5))
        if daily_std > 1e-10
        else 0.0
    )
    summary = {
        "initial_cash": cfg.initial_cash,
        "final_equity": final_equity,
        "total_return": final_equity / cfg.initial_cash - 1.0,
        "benchmark_return": benchmark_equity / cfg.initial_cash - 1.0,
        "gap_pct": (final_equity / cfg.initial_cash - benchmark_equity / cfg.initial_cash) * 100.0,
        "max_drawdown": float(equity_df["drawdown"].min()),
        "sharpe_ratio": sharpe,
        "trades": int(len(trades_df)),
        "turnover_proxy": int(len(trades_df)) / max(len(equity_df), 1),
        "win_rate": (
            float((trades_df["return_pct"] > 0).mean()) if not trades_df.empty else 0.0
        ),
    }
    return summary, equity_df, trades_df


def build_rank_label_experiment(
    *,
    cfg: RankExperimentConfig,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    settings = load_settings()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    loaded = load_price_data_batch(list(dict.fromkeys(list(settings.tickers) + ["^VIX", "SPY"])), period=cfg.period)
    ticker_data = {ticker: loaded[ticker] for ticker in settings.tickers if ticker in loaded}
    vix_df = loaded.get("^VIX")
    spy_df = loaded.get("SPY")
    macro_df = None

    full_dataset = _build_rank_dataset(
        ticker_data,
        prediction_horizon=cfg.prediction_horizon,
        vix_df=vix_df,
        spy_df=spy_df,
        macro_df=macro_df,
    )
    holdout_start, holdout_end = portfolio_holdout_window(ticker_data)
    train_df = full_dataset[full_dataset["date"] < holdout_start].copy()
    test_df = full_dataset[
        (full_dataset["date"] >= holdout_start)
        & (full_dataset["date"] <= holdout_end)
    ].copy()
    if train_df.empty or test_df.empty:
        raise ValueError("Rank experiment train/test split is empty")

    classifier, regressor = _train_rank_models(train_df, cfg.top_bucket_pct)
    scored = _score_oos(
        test_df,
        classifier=classifier,
        regressor=regressor,
        top_bucket_pct=cfg.top_bucket_pct,
    )
    portfolio, equity_df, trades_df = _simulate_top_bucket_portfolio(scored, ticker_data, cfg)

    try:
        auc = float(roc_auc_score(scored["top_bucket_label"], scored["rank_clf_score"]))
    except ValueError:
        auc = None
    rmse = float(mean_squared_error(scored["future_return_percentile"], scored["rank_reg_score"]) ** 0.5)
    model_path = output_dir / "rank_models.joblib"
    joblib.dump({"classifier": classifier, "regressor": regressor, "config": asdict(cfg)}, model_path)
    scored_path = output_dir / "oos_scores.csv"
    equity_path = output_dir / "portfolio_equity.csv"
    trades_path = output_dir / "portfolio_trades.csv"
    scored[["date", "ticker", "future_return_percentile", "top_bucket_label", "rank_score", "predicted_score_percentile"]].to_csv(scored_path, index=False)
    equity_df.to_csv(equity_path, index=False)
    trades_df.to_csv(trades_path, index=False)

    gate_passed = (
        portfolio["gap_pct"] >= 0
        and portfolio["max_drawdown"] >= -0.20
        and portfolio["sharpe_ratio"] >= 1.0
        and portfolio["turnover_proxy"] <= cfg.max_turnover_proxy
    )
    report = {
        "generated_at": _utc_now_iso(),
        "label": {
            "kind": "cross_sectional_future_return_percentile",
            "prediction_horizon": cfg.prediction_horizon,
            "top_bucket_pct": cfg.top_bucket_pct,
            "min_score_quantile": cfg.min_score_quantile,
        },
        "metrics": {
            "top_bucket_auc": auc,
            "rank_percentile_rmse": rmse,
            "test_rows": int(len(scored)),
            "test_positive_rate": float(scored["top_bucket_label"].mean()),
        },
        "portfolio_oos": portfolio,
        "benchmark_oos": {
            "kind": "equal_weight_buy_hold_same_universe",
            "return": portfolio["benchmark_return"],
        },
        "gate": {
            "passed": gate_passed,
            "criteria": {
                "gap_pct_min": 0.0,
                "max_drawdown_floor": -0.20,
                "min_sharpe": 1.0,
                "max_turnover_proxy": cfg.max_turnover_proxy,
            },
        },
        "recommendation": (
            "Promote to deeper paper experiment: top bucket rank AI passed portfolio gate."
            if gate_passed
            else "Do not wire rank AI yet; portfolio gate failed."
        ),
        "artifacts": {
            "model": str(model_path),
            "scores": str(scored_path),
            "equity": str(equity_path),
            "trades": str(trades_path),
        },
    }
    validate_rank_label_report(report)
    return report


def validate_rank_label_report(report: dict[str, Any]) -> dict[str, Any]:
    missing = [key for key in RANK_LABEL_REPORT_KEYS if key not in report]
    if missing:
        raise ValueError(f"Missing rank label report keys: {missing}")
    return report


def write_rank_label_report(
    report: dict[str, Any],
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "latest_summary.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run cross-sectional rank label experiment")
    parser.add_argument("--prediction-horizon", type=int, default=20)
    parser.add_argument("--top-bucket-pct", type=float, default=DEFAULT_TOP_BUCKET_PCT)
    parser.add_argument("--min-score-quantile", type=float, default=0.70)
    parser.add_argument("--max-turnover-proxy", type=float, default=1.20)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    settings = load_settings()
    cfg = RankExperimentConfig(
        prediction_horizon=args.prediction_horizon,
        top_bucket_pct=args.top_bucket_pct,
        max_positions=int(settings.max_total_positions),
        target_position_pct=float(settings.max_position_pct),
        stop_loss_pct=float(settings.stop_loss_pct),
        take_profit_pct=float(settings.take_profit_pct),
        trailing_stop_pct=float(settings.trailing_stop_pct),
        min_score_quantile=args.min_score_quantile,
        max_turnover_proxy=args.max_turnover_proxy,
    )
    report = build_rank_label_experiment(cfg=cfg, output_dir=args.output_dir)
    path = write_rank_label_report(report, args.output_dir)
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
