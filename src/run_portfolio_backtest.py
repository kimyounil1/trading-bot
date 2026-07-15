import argparse
import math
from pathlib import Path

import pandas as pd

from src.settings import load_settings
from src.data_loader import load_price_data_batch
from src.candidate_cache import load_dynamic_universe_history
from src.instrument_meta import preferred_leveraged_long_product
from src.portfolio_backtest_settings import portfolio_backtest_kwargs
from src.portfolio_backtester import (
    run_portfolio_backtest,
    save_portfolio_backtest_outputs,
)
from src.sleeved_portfolio_backtester import run_sleeved_portfolio_backtest
from src.macro_loader import load_macro_data


def pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def latest_covered_market_date(
    ticker_data: dict[str, pd.DataFrame],
    *,
    base_tickers: list[str],
    requested_end: str | None,
    min_coverage: float = 0.8,
) -> pd.Timestamp:
    """Avoid treating a partially refreshed latest session as a full market day."""
    if not 0 < min_coverage <= 1:
        raise ValueError("min_coverage must be between 0 and 1")
    counts: dict[pd.Timestamp, int] = {}
    available = 0
    for ticker in dict.fromkeys(str(item).upper() for item in base_tickers):
        frame = ticker_data.get(ticker)
        if frame is None or frame.empty or "date" not in frame.columns:
            continue
        close_col = "close" if "close" in frame.columns else "adj_close"
        if close_col not in frame.columns:
            continue
        available += 1
        dates = pd.to_datetime(frame["date"], errors="coerce")
        closes = pd.to_numeric(frame[close_col], errors="coerce")
        valid_dates = dates[dates.notna() & closes.notna() & (closes > 0)].dt.normalize()
        for date in valid_dates.drop_duplicates():
            counts[pd.Timestamp(date)] = counts.get(pd.Timestamp(date), 0) + 1
    if not counts or available == 0:
        raise ValueError("No completed base-universe dates available")
    required = max(1, math.ceil(available * min_coverage))
    end_limit = pd.Timestamp(requested_end).normalize() if requested_end else None
    eligible = [
        date
        for date, count in counts.items()
        if count >= required and (end_limit is None or date <= end_limit)
    ]
    if not eligible:
        raise ValueError(
            f"No market date meets {min_coverage:.0%} base-universe coverage"
        )
    return max(eligible)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--allocation",
        choices=["equal_weight", "mvo", "bl_mvo"],
        default="equal_weight",
        help="Position sizing method",
    )
    parser.add_argument("--start", default=None, help="Evaluation start date")
    parser.add_argument("--end", default=None, help="Evaluation end date")
    parser.add_argument("--initial-cash", type=float, default=10_000.0)
    parser.add_argument("--force-refresh", action="store_true")
    parser.add_argument(
        "--use-universe-history",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Use recorded point-in-time dynamic-universe snapshots when available",
    )
    parser.add_argument(
        "--include-external-filters",
        action="store_true",
        help="Replay cached LLM/news filters; disabled by default when history is incomplete",
    )
    parser.add_argument("--outdir", type=Path, default=Path("logs/portfolio_backtest"))
    args = parser.parse_args()

    settings = load_settings()
    print(f"Loading {len(settings.tickers)} tickers...")
    historical_universe = (
        load_dynamic_universe_history() if args.use_universe_history else {}
    )
    dynamic_symbols = sorted(
        {
            ticker
            for date, tickers in historical_universe.items()
            if (args.start is None or date >= pd.Timestamp(args.start))
            and (args.end is None or date <= pd.Timestamp(args.end))
            for ticker in tickers
        }
    )
    signal_tickers = list(dict.fromkeys([*settings.tickers, *dynamic_symbols]))
    product_routes = {
        ticker: product
        for ticker in signal_tickers
        if (
            product := preferred_leveraged_long_product(
                ticker,
                allowlist=list(settings.leveraged_etf_allowlist),
            )
        )
    }
    tickers_to_load = list(signal_tickers)
    tickers_to_load.extend(product_routes.values())
    if settings.market_regime_filter_enabled:
        tickers_to_load.append(settings.market_regime_ticker)
    if settings.relative_strength_filter_enabled:
        tickers_to_load.append(settings.relative_strength_benchmark_ticker)
    if settings.use_ai_score and "^VIX" not in tickers_to_load:
        tickers_to_load.append("^VIX")
    tickers_to_load = list(dict.fromkeys(tickers_to_load))
    loaded_data = load_price_data_batch(
        list(dict.fromkeys(tickers_to_load)),
        period="2y",
        force_refresh=args.force_refresh,
    )
    ticker_data = {ticker: loaded_data[ticker] for ticker in signal_tickers}
    leveraged_product_data = {
        product: loaded_data[product]
        for product in product_routes.values()
        if product in loaded_data
    }
    vix_df = loaded_data.get("^VIX")
    macro_df = load_macro_data(period="2y") if settings.use_ai_score else None
    benchmark_df = (
        loaded_data[settings.market_regime_ticker]
        if settings.market_regime_filter_enabled
        else None
    )
    relative_strength_benchmark_df = (
        loaded_data[settings.relative_strength_benchmark_ticker]
        if settings.relative_strength_filter_enabled
        else None
    )
    covered_end = latest_covered_market_date(
        ticker_data,
        base_tickers=list(settings.tickers),
        requested_end=args.end,
    )
    evaluation_end = covered_end.strftime("%Y-%m-%d")
    if args.end is None or pd.Timestamp(args.end).normalize() > covered_end:
        print(
            f"Using completed market date {evaluation_end}; "
            "newer cache rows do not yet meet 80% universe coverage."
        )

    if settings.portfolio_sleeves_enabled:
        result, equity_df, trades_df = run_sleeved_portfolio_backtest(
            settings,
            ticker_data=ticker_data,
            benchmark_df=benchmark_df,
            relative_strength_benchmark_df=relative_strength_benchmark_df,
            vix_df=vix_df,
            macro_df=macro_df,
            initial_cash=args.initial_cash,
            evaluation_start_date=args.start,
            evaluation_end_date=evaluation_end,
            leveraged_product_data=leveraged_product_data,
            leveraged_product_routes=product_routes,
            historical_universe_by_date=historical_universe,
            base_universe=set(settings.tickers),
            benchmark_universe=set(settings.tickers),
            include_external_filters=args.include_external_filters,
        )
    else:
        bt_kwargs = portfolio_backtest_kwargs(
            settings,
            ticker_data=ticker_data,
            benchmark_df=benchmark_df,
            relative_strength_benchmark_df=relative_strength_benchmark_df,
            vix_df=vix_df,
            macro_df=macro_df,
            allocation_method=args.allocation,
            evaluation_start_date=args.start,
            evaluation_end_date=evaluation_end,
            initial_cash=args.initial_cash,
            leveraged_product_data=leveraged_product_data,
            leveraged_product_routes=product_routes,
            historical_universe_by_date=historical_universe,
            base_universe=set(settings.tickers),
            benchmark_universe=set(settings.tickers),
            include_external_filters=args.include_external_filters,
        )
        result, equity_df, trades_df = run_portfolio_backtest(**bt_kwargs)

    output_dir = args.outdir
    save_portfolio_backtest_outputs(
        output_dir=output_dir,
        result=result,
        equity_df=equity_df,
        trades_df=trades_df,
    )

    print("-" * 80)
    print("Portfolio backtest result")
    print(f"strategy_return={pct(result.total_return)}")
    print(f"equal_weight_buy_hold={pct(result.benchmark_return)}")
    print(f"max_drawdown={pct(result.max_drawdown)}")
    print(f"trades={result.trades}")
    print(f"win_rate={pct(result.win_rate)}")
    print(f"final_equity=${result.final_equity:.2f}")
    print(f"sharpe_ratio={result.sharpe_ratio:.3f}")
    print(f"allocation_method={args.allocation}")
    print("-" * 80)
    print(f"Saved outputs to {output_dir}")


if __name__ == "__main__":
    main()
