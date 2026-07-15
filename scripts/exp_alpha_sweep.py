"""One-off research sweep: how to close/beat the equal-weight benchmark.

Loads price data once, then runs run_portfolio_backtest under several
parameter scenarios (churn reduction, universe pruning, combos) and prints a
comparison table. Also reports SPY buy-hold as an alternate benchmark.

Usage: PYTHONPATH=. .venv/bin/python scripts/exp_alpha_sweep.py
"""

from __future__ import annotations

import copy

import pandas as pd

from src.settings import load_settings
from src.data_loader import load_price_data_batch
from src.macro_loader import load_macro_data
from src.portfolio_backtest_settings import portfolio_backtest_kwargs
from src.portfolio_backtester import run_portfolio_backtest
from src.sector import get_sector

DRAG_SECTORS = {"consumer", "transport", "telecom", "media", "utilities"}


def _spy_buy_hold_return(ticker_data: dict[str, pd.DataFrame]) -> float:
    spy = ticker_data.get("SPY")
    if spy is None or spy.empty:
        return float("nan")
    col = "adj_close" if "adj_close" in spy.columns else "close"
    series = pd.to_numeric(spy[col], errors="coerce").dropna()
    if series.empty:
        return float("nan")
    return float(series.iloc[-1] / series.iloc[0] - 1.0)


def main() -> None:
    settings = load_settings()
    print(f"Loading {len(settings.tickers)} tickers...")
    tickers_to_load = list(dict.fromkeys(list(settings.tickers) + ["^VIX", "SPY"]))
    loaded = load_price_data_batch(tickers_to_load, period="2y")
    full_ticker_data = {t: loaded[t] for t in settings.tickers if t in loaded}
    vix_df = loaded.get("^VIX")
    macro_df = load_macro_data(period="2y") if settings.use_ai_score else None
    rs_bench = loaded.get(settings.relative_strength_benchmark_ticker)

    spy_ret = _spy_buy_hold_return(full_ticker_data)

    pruned_ticker_data = {
        t: df for t, df in full_ticker_data.items() if get_sector(t) not in DRAG_SECTORS
    }

    base_kwargs = portfolio_backtest_kwargs(
        settings,
        ticker_data=full_ticker_data,
        relative_strength_benchmark_df=rs_bench,
        vix_df=vix_df,
        macro_df=macro_df,
    )

    def run(label: str, *, ticker_data=None, **overrides):
        kw = copy.copy(base_kwargs)
        if ticker_data is not None:
            kw["ticker_data"] = ticker_data
        kw.update(overrides)
        result, _, trades = run_portfolio_backtest(**kw)
        gap = (result.total_return - result.benchmark_return) * 100.0
        spy_gap = (result.total_return - spy_ret) * 100.0 if spy_ret == spy_ret else float("nan")
        return {
            "scenario": label,
            "ret_%": round(result.total_return * 100, 2),
            "bench_%": round(result.benchmark_return * 100, 2),
            "gap_pp": round(gap, 2),
            "spy_gap_pp": round(spy_gap, 2),
            "mdd_%": round(result.max_drawdown * 100, 2),
            "sharpe": round(result.sharpe_ratio, 2),
            "trades": result.trades,
            "win_%": round(result.win_rate * 100, 1),
        }

    rows = []
    # 0) baseline = current config
    rows.append(run("0_baseline"))

    # Round 2: full universe, vary trailing stop (the main lever found)
    rows.append(run("t_0.15", trailing_stop_pct=0.15))
    rows.append(run("t_0.20", trailing_stop_pct=0.20))
    rows.append(run("t_0.25", trailing_stop_pct=0.25))
    rows.append(run("t_0.30", trailing_stop_pct=0.30))
    rows.append(run("t_off", trailing_stop_pct=0.0))

    # Concentration on full universe with let-winners-run
    rows.append(
        run(
            "c_6x16_t0.20",
            trailing_stop_pct=0.20,
            max_positions=6,
            target_position_pct=0.16,
            rank_ai_weight=2.0,
        )
    )
    rows.append(
        run(
            "c_4x24_t0.20",
            trailing_stop_pct=0.20,
            max_positions=4,
            target_position_pct=0.24,
            rank_ai_weight=2.0,
        )
    )
    # AI-weighted ranking with current breadth + let run
    rows.append(run("ai_w2_t0.20", trailing_stop_pct=0.20, rank_ai_weight=2.0))

    df = pd.DataFrame(rows)
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 20)
    print("\n=== Alpha sweep (equal-weight benchmark unless noted) ===")
    print(f"SPY buy-hold return over window: {spy_ret*100:.2f}%\n")
    print(df.to_string(index=False))
    print(
        "\nNote: bench_% is equal-weight buy-hold of that scenario's universe "
        "(pruned universe changes the bench). spy_gap_pp compares to SPY only."
    )


if __name__ == "__main__":
    main()
