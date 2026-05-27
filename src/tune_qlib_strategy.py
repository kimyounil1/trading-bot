from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

import pandas as pd

from src.compare_strategy_snapshots import load_snapshot
from src.data_loader import load_cached_price_data_batch
from src.ml_model import load_ai_score_model
from src.settings import StrategySettings
from src.qlib_backtest_runner import (
    apply_signal_execution_constraints,
    build_close_price_lookup,
    build_strategy_signal_from_price_data,
    compute_report_metrics,
    extract_trades_from_positions,
    infer_backtest_window,
    load_qlib_ready_price_frame,
    load_strategy_settings_from_json,
    run_qlib_backtest,
)
from src.snapshot_utils import build_snapshot_payload, save_snapshot_payload


def parse_float_list(value: str) -> list[float]:
    return [float(item.strip()) for item in value.split(",") if item.strip()]


def parse_int_list(value: str) -> list[int]:
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Grid-search small qlib strategy parameter combinations against the baseline snapshot."
    )
    parser.add_argument("--provider-uri", required=True)
    parser.add_argument("--settings-json", default="config/strategy_config.json")
    parser.add_argument("--price-period", default="2y")
    parser.add_argument("--qlib-ready-dir", default="logs/baselines/current_strategy/qlib_ready")
    parser.add_argument("--output-dir", default="logs/qlib_runs/tuning")
    parser.add_argument("--benchmark", default="SPY")
    parser.add_argument("--region", default="us")
    parser.add_argument("--initial-cash", type=float, default=10000.0)
    parser.add_argument("--topk-list", default="4,6,8")
    parser.add_argument("--n-drop-list", default="1,2")
    parser.add_argument("--trend-weight-list", default="1.0,2.0")
    parser.add_argument("--rsi-weight-list", default="0.5,1.0")
    parser.add_argument("--ai-weight-list", default="0.5,1.0,1.5")
    parser.add_argument("--open-cost-list", default="0.0005")
    parser.add_argument("--close-cost-list", default="0.001,0.0015")
    parser.add_argument("--rsi-buy-limit-list", default=None)
    parser.add_argument("--ai-threshold-list", default=None)
    parser.add_argument("--min-cost", type=float, default=5.0)
    parser.add_argument("--deal-price", default="close")
    parser.add_argument(
        "--baseline-snapshot",
        default="logs/baselines/current_strategy/baseline_snapshot.json",
    )
    parser.add_argument("--limit", type=int, default=24)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = load_strategy_settings_from_json(args.settings_json)
    ticker_data = load_cached_price_data_batch(settings.tickers, period=args.price_period)
    price_frame = load_qlib_ready_price_frame(args.qlib_ready_dir)
    close_lookup = build_close_price_lookup(price_frame)
    baseline = load_snapshot(args.baseline_snapshot)["result"]

    ai_model_bundle = None
    if settings.use_ai_score:
        try:
            ai_model_bundle = load_ai_score_model()
        except Exception:
            ai_model_bundle = None

    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    topk_list = parse_int_list(args.topk_list)
    n_drop_list = parse_int_list(args.n_drop_list)
    trend_weight_list = parse_float_list(args.trend_weight_list)
    rsi_weight_list = parse_float_list(args.rsi_weight_list)
    ai_weight_list = parse_float_list(args.ai_weight_list)
    open_cost_list = parse_float_list(args.open_cost_list)
    close_cost_list = parse_float_list(args.close_cost_list)
    rsi_buy_limit_list = (
        parse_float_list(args.rsi_buy_limit_list)
        if args.rsi_buy_limit_list
        else [float(settings.rsi_buy_limit)]
    )
    ai_threshold_list = (
        parse_float_list(args.ai_threshold_list)
        if args.ai_threshold_list
        else [float(settings.ai_score_buy_threshold)]
    )

    rows: list[dict] = []
    combinations = itertools.islice(
        itertools.product(
            topk_list,
            n_drop_list,
            trend_weight_list,
            rsi_weight_list,
            ai_weight_list,
            open_cost_list,
            close_cost_list,
            rsi_buy_limit_list,
            ai_threshold_list,
        ),
        args.limit,
    )

    for idx, (topk, n_drop, trend_weight, rsi_weight, ai_weight, open_cost, close_cost, rsi_buy_limit, ai_threshold) in enumerate(combinations, start=1):
        print(
            f"[{idx}] topk={topk} n_drop={n_drop} trend_w={trend_weight} "
            f"rsi_w={rsi_weight} ai_w={ai_weight} open_cost={open_cost} "
            f"close_cost={close_cost} rsi_limit={rsi_buy_limit} ai_threshold={ai_threshold}"
        )
        tuned_settings = StrategySettings(**settings.__dict__.copy())
        tuned_settings.rsi_buy_limit = float(rsi_buy_limit)
        tuned_settings.ai_score_buy_threshold = float(ai_threshold)
        signal_frame = build_strategy_signal_from_price_data(
            ticker_data,
            tuned_settings,
            ai_model_bundle=ai_model_bundle,
            trend_weight=trend_weight,
            rsi_weight=rsi_weight,
            ai_weight=ai_weight,
        )
        signal_frame = apply_signal_execution_constraints(
            signal_frame,
            max_active_signals=topk,
            max_new_signals_per_day=tuned_settings.max_orders_per_run,
            cooldown_days=tuned_settings.buy_cooldown_days,
        )
        start_time, end_time = infer_backtest_window(signal_frame)
        report_df, positions = run_qlib_backtest(
            provider_uri=args.provider_uri,
            region=args.region,
            signal_frame=signal_frame,
            benchmark=args.benchmark,
            initial_cash=args.initial_cash,
            topk=topk,
            n_drop=n_drop,
            deal_price=args.deal_price,
            open_cost=open_cost,
            close_cost=close_cost,
            min_cost=args.min_cost,
            start_time=start_time,
            end_time=end_time,
        )
        metrics = compute_report_metrics(report_df, initial_cash=args.initial_cash)
        trades_df = extract_trades_from_positions(positions, close_lookup)
        if not trades_df.empty:
            metrics["trades"] = int(len(trades_df))
            metrics["win_rate"] = float((trades_df["return_pct"] > 0).mean())

        metrics["vs_baseline_return"] = metrics["total_return"] - float(baseline["total_return"])
        metrics["vs_baseline_drawdown"] = metrics["max_drawdown"] - float(baseline["max_drawdown"])
        metrics["topk"] = topk
        metrics["n_drop"] = n_drop
        metrics["trend_weight"] = trend_weight
        metrics["rsi_weight"] = rsi_weight
        metrics["ai_weight"] = ai_weight
        metrics["open_cost"] = open_cost
        metrics["close_cost"] = close_cost
        metrics["rsi_buy_limit"] = rsi_buy_limit
        metrics["ai_score_buy_threshold"] = ai_threshold
        rows.append(metrics)

    results_df = pd.DataFrame(rows).sort_values(
        ["total_return", "max_drawdown", "win_rate"],
        ascending=[False, False, False],
    ).reset_index(drop=True)
    results_path = output_dir / "tuning_results.csv"
    results_df.to_csv(results_path, index=False)

    best = results_df.iloc[0].to_dict()
    best_payload = build_snapshot_payload(
        period=args.price_period,
        tickers=settings.tickers,
        settings=settings,
        result={
            "initial_cash": args.initial_cash,
            "final_equity": float(best["final_equity"]),
            "total_return": float(best["total_return"]),
            "max_drawdown": float(best["max_drawdown"]),
            "trades": int(best["trades"]),
            "win_rate": float(best["win_rate"]),
            "benchmark_return": float(best["benchmark_return"]),
        },
        equity_rows=0,
        trade_rows=int(best["trades"]),
        extra_fields={"best_params": best},
    )
    snapshot_path = save_snapshot_payload(best_payload, output_dir / "best_snapshot.json")
    print(f"Saved tuning results to {results_path}")
    print(f"Saved best snapshot to {snapshot_path}")
    print(json.dumps(best, indent=2))


if __name__ == "__main__":
    main()
