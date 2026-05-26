"""Find the best AI exit threshold by comparing against MA-only baseline."""

from pathlib import Path

import pandas as pd

from src.settings import load_settings
from src.data_loader import load_price_data_batch
from src.portfolio_backtester import run_portfolio_backtest
from src.macro_loader import load_macro_data


THRESHOLDS = [0.20, 0.25, 0.30, 0.35, 0.40]


def pct(v: float) -> str:
    return f"{v * 100:.2f}%"


def run_one(settings, ticker_data, ai_exit_enabled: bool, ai_exit_threshold: float = 0.30,
            ai_exit_dynamic_enabled: bool = False,
            ai_exit_vix_low: float = 15.0, ai_exit_vix_high: float = 25.0,
            ai_exit_threshold_bull: float = 0.55, ai_exit_threshold_bear: float = 0.28,
            vix_df=None, macro_df=None):
    result, _, trades_df = run_portfolio_backtest(
        ticker_data=ticker_data,
        initial_cash=10000.0,
        max_positions=settings.max_total_positions,
        target_position_pct=settings.max_position_pct,
        transaction_cost_pct=0.001,
        ma_fast=settings.ma_fast,
        ma_slow=settings.ma_slow,
        rsi_buy_limit=settings.rsi_buy_limit,
        use_ai_score=settings.use_ai_score,
        ai_score_buy_threshold=settings.ai_score_buy_threshold,
        volume_filter_enabled=settings.volume_filter_enabled,
        volume_lookback_days=settings.volume_lookback_days,
        min_volume_ratio=settings.min_volume_ratio,
        rank_trend_weight=settings.rank_trend_weight,
        rank_ai_weight=settings.rank_ai_weight,
        rank_momentum_weight=settings.rank_momentum_weight,
        rank_volatility_weight=settings.rank_volatility_weight,
        ai_exit_enabled=ai_exit_enabled,
        ai_exit_threshold=ai_exit_threshold,
        ai_exit_dynamic_enabled=ai_exit_dynamic_enabled,
        ai_exit_vix_low=ai_exit_vix_low,
        ai_exit_vix_high=ai_exit_vix_high,
        ai_exit_threshold_bull=ai_exit_threshold_bull,
        ai_exit_threshold_bear=ai_exit_threshold_bear,
        vix_df=vix_df,
        macro_df=macro_df,
    )
    ai_exits = 0
    if not trades_df.empty and "exit_reason" in trades_df.columns:
        ai_exits = int((trades_df["exit_reason"] == "AI_EXIT").sum())
    return result, ai_exits


def main() -> None:
    settings = load_settings()
    print(f"Loading {len(settings.tickers)} tickers (2y)...")
    tickers_to_load = list(settings.tickers)
    if "^VIX" not in tickers_to_load:
        tickers_to_load.append("^VIX")
    loaded = load_price_data_batch(tickers_to_load, period="2y")
    ticker_data = {t: loaded[t] for t in settings.tickers if t in loaded}
    vix_df = loaded.get("^VIX")
    macro_df = load_macro_data(period="2y")
    print(f"Loaded {len(ticker_data)} tickers\n")

    rows = []

    # Baseline: MA exit only
    print("Running baseline (MA exit only)...", end=" ", flush=True)
    baseline, _ = run_one(settings, ticker_data, ai_exit_enabled=False,
                          vix_df=vix_df, macro_df=macro_df)
    print("done")
    rows.append({
        "config": "MA only (baseline)",
        "threshold": "-",
        "total_return": pct(baseline.total_return),
        "max_drawdown": pct(baseline.max_drawdown),
        "sharpe": f"{baseline.sharpe_ratio:.3f}",
        "trades": baseline.trades,
        "win_rate": pct(baseline.win_rate),
        "ai_exits": 0,
    })

    # MA + AI exit combined (fixed thresholds)
    for thr in THRESHOLDS:
        print(f"Running MA + AI exit (threshold={thr})...", end=" ", flush=True)
        result, ai_exits = run_one(settings, ticker_data, ai_exit_enabled=True,
                                   ai_exit_threshold=thr, vix_df=vix_df, macro_df=macro_df)
        print("done")
        rows.append({
            "config": "MA + AI exit",
            "threshold": thr,
            "total_return": pct(result.total_return),
            "max_drawdown": pct(result.max_drawdown),
            "sharpe": f"{result.sharpe_ratio:.3f}",
            "trades": result.trades,
            "win_rate": pct(result.win_rate),
            "ai_exits": ai_exits,
        })

    # VIX-dynamic AI exit variants
    # bull threshold LOWER (harder to exit → hold longer in bull)
    # bear threshold HIGHER (easier to exit → protect capital in bear)
    dynamic_configs = [
        {"vix_low": 15.0, "vix_high": 25.0, "bull": 0.22, "neutral": 0.40, "bear": 0.50},
        {"vix_low": 15.0, "vix_high": 25.0, "bull": 0.20, "neutral": 0.35, "bear": 0.50},
        {"vix_low": 18.0, "vix_high": 28.0, "bull": 0.22, "neutral": 0.40, "bear": 0.50},
        {"vix_low": 15.0, "vix_high": 25.0, "bull": 0.25, "neutral": 0.40, "bear": 0.45},
    ]
    for cfg in dynamic_configs:
        label = f"dyn bull={cfg['bull']}/bear={cfg['bear']} vix<{cfg['vix_low']}/<{cfg['vix_high']}"
        print(f"Running {label}...", end=" ", flush=True)
        result, ai_exits = run_one(
            settings, ticker_data, ai_exit_enabled=True,
            ai_exit_threshold=cfg["neutral"],
            ai_exit_dynamic_enabled=True,
            ai_exit_vix_low=cfg["vix_low"], ai_exit_vix_high=cfg["vix_high"],
            ai_exit_threshold_bull=cfg["bull"], ai_exit_threshold_bear=cfg["bear"],
            vix_df=vix_df, macro_df=macro_df,
        )
        print("done")
        rows.append({
            "config": label,
            "threshold": f"{cfg['bull']}/{cfg['neutral']}/{cfg['bear']}",
            "total_return": pct(result.total_return),
            "max_drawdown": pct(result.max_drawdown),
            "sharpe": f"{result.sharpe_ratio:.3f}",
            "trades": result.trades,
            "win_rate": pct(result.win_rate),
            "ai_exits": ai_exits,
        })

    print()
    print("-" * 90)
    print("AI Exit Threshold Optimization (2y backtest)")
    print("-" * 90)
    df = pd.DataFrame(rows)
    print(df.to_string(index=False))
    print("-" * 90)

    # Find best by Sharpe
    numeric_rows = [r for r in rows if r["threshold"] != "-"]
    if numeric_rows:
        best = max(numeric_rows, key=lambda r: float(r["sharpe"]))
        print(f"\nBest threshold by Sharpe: {best['threshold']} "
              f"(return={best['total_return']}, MDD={best['max_drawdown']}, "
              f"Sharpe={best['sharpe']}, ai_exits={best['ai_exits']})")

    # Save results
    output_dir = Path("logs/ai_exit_optimize")
    output_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_dir / "ai_exit_results.csv", index=False)
    print(f"Saved to {output_dir}/ai_exit_results.csv")


if __name__ == "__main__":
    main()
