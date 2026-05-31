"""Compare portfolio backtest baseline vs in-loop operational filters (LLM + news)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import src.config  # noqa: F401  # load .env

from src.data_loader import load_price_data_batch
from src.macro_loader import load_macro_data
from src.portfolio_backtest_settings import portfolio_backtest_kwargs
from src.portfolio_backtester import run_portfolio_backtest, save_portfolio_backtest_outputs
from src.settings import load_settings

DEFAULT_OUTPUT_DIR = Path("logs/operational_alpha")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_backtest_data(settings):
    tickers_to_load = list(settings.tickers)
    if settings.market_regime_filter_enabled:
        tickers_to_load.append(settings.market_regime_ticker)
    if settings.relative_strength_filter_enabled:
        tickers_to_load.append(settings.relative_strength_benchmark_ticker)
    if settings.use_ai_score and "^VIX" not in tickers_to_load:
        tickers_to_load.append("^VIX")
    tickers_to_load = list(dict.fromkeys(tickers_to_load))
    loaded = load_price_data_batch(tickers_to_load, period="2y")
    ticker_data = {ticker: loaded[ticker] for ticker in settings.tickers}
    return {
        "ticker_data": ticker_data,
        "benchmark_df": (
            loaded[settings.market_regime_ticker]
            if settings.market_regime_filter_enabled
            else None
        ),
        "relative_strength_benchmark_df": (
            loaded[settings.relative_strength_benchmark_ticker]
            if settings.relative_strength_filter_enabled
            else None
        ),
        "vix_df": loaded.get("^VIX"),
        "macro_df": load_macro_data(period="2y") if settings.use_ai_score else None,
    }


def _result_snapshot(result) -> dict[str, Any]:
    return {
        "total_return_pct": round(result.total_return * 100.0, 4),
        "benchmark_return_pct": round(result.benchmark_return * 100.0, 4),
        "gap_vs_benchmark_pp": round((result.total_return - result.benchmark_return) * 100.0, 4),
        "beats_benchmark": result.total_return >= result.benchmark_return,
        "max_drawdown_pct": round(result.max_drawdown * 100.0, 4),
        "sharpe_ratio": round(result.sharpe_ratio, 4),
        "trades": int(result.trades),
        "win_rate_pct": round(result.win_rate * 100.0, 2),
    }


def run_comparison(
    *,
    llm_cache_only: bool = True,
    llm_live: bool = False,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    settings = load_settings()
    data = _load_backtest_data(settings)
    base_kwargs = portfolio_backtest_kwargs(settings, **data)

    print("=== Baseline (ML only, no in-loop LLM/news) ===")
    baseline_result, baseline_eq, baseline_tr = run_portfolio_backtest(**base_kwargs)
    baseline_dir = output_dir / "baseline"
    save_portfolio_backtest_outputs(baseline_dir, baseline_result, baseline_eq, baseline_tr)

    ops_kwargs = {
        **base_kwargs,
        "llm_filter_enabled": True,
        "llm_cache_only": llm_cache_only and not llm_live,
        "news_sentiment_filter_enabled": bool(settings.news_sentiment_enabled),
        "news_sentiment_threshold": float(settings.news_sentiment_threshold),
        "operational_settings": settings,
    }
    mode = "in_loop_cache" if ops_kwargs["llm_cache_only"] else "in_loop_live_llm"
    print(f"=== Operational ({mode} + news={settings.news_sentiment_enabled}) ===")
    ops_result, ops_eq, ops_tr = run_portfolio_backtest(**ops_kwargs)
    ops_dir = output_dir / "with_operational_filters"
    save_portfolio_backtest_outputs(ops_dir, ops_result, ops_eq, ops_tr)

    baseline = _result_snapshot(baseline_result)
    operational = _result_snapshot(ops_result)
    report = {
        "generated_at": _utc_now_iso(),
        "mode": mode,
        "baseline": baseline,
        "operational": operational,
        "delta": {
            "return_pp": round(
                operational["total_return_pct"] - baseline["total_return_pct"], 4
            ),
            "trades": operational["trades"] - baseline["trades"],
            "sharpe": round(operational["sharpe_ratio"] - baseline["sharpe_ratio"], 4),
        },
        "notes": [
            "Operational = same portfolio_backtester with main.py buy filters in the entry loop.",
            "LLM uses data/llm_cache.json keyed by {ticker}_{entry_date} when cache_only.",
            "News/LLM headlines filtered by pubDate<=entry_date; yfinance only keeps recent articles.",
            "Populate cache via paper/live runs for historically accurate LLM replay.",
        ],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "latest_summary.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Baseline vs operational in-loop backtest")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument(
        "--live-llm",
        action="store_true",
        help="Call Gemini on cache miss (slow; headlines still from yfinance recent feed)",
    )
    args = parser.parse_args()
    report = run_comparison(
        llm_cache_only=not args.live_llm,
        llm_live=args.live_llm,
        output_dir=Path(args.output_dir),
    )
    b, o, d = report["baseline"], report["operational"], report["delta"]
    print("\n--- Summary ---")
    print(
        f"Baseline:      {b['total_return_pct']}% vs bench {b['benchmark_return_pct']}% "
        f"({b['trades']} trades)"
    )
    print(
        f"Operational:   {o['total_return_pct']}% vs bench {o['benchmark_return_pct']}% "
        f"({o['trades']} trades)"
    )
    print(f"Delta:         {d['return_pp']:+.2f} pp return, {d['trades']:+d} trades")
    print(f"Wrote {args.output_dir}/latest_summary.json")


if __name__ == "__main__":
    main()
