"""Estimate backtest PnL impact if live LLM + news sentiment filters were applied at entry."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

import src.config  # noqa: F401  # load .env (GEMINI_API_KEY) before LLM calls

from src.llm_analyst import evaluate_ticker_consensus
from src.news_sentiment import get_ticker_sentiment
from src.portfolio_backtest_validation import load_summary_row
from src.settings import load_settings

DEFAULT_BACKTEST_DIR = Path("logs/portfolio_backtest")
DEFAULT_OUTPUT_DIR = Path("logs/llm_backtest_impact")

LLM_BACKTEST_IMPACT_KEYS = (
    "generated_at",
    "mode",
    "baseline",
    "with_live_filters",
    "trade_level",
    "notes",
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _trade_pnl(trades_df: pd.DataFrame) -> pd.Series:
    if "exit_value" in trades_df.columns and "cost_basis" in trades_df.columns:
        return pd.to_numeric(trades_df["exit_value"], errors="coerce") - pd.to_numeric(
            trades_df["cost_basis"], errors="coerce"
        )
    return pd.to_numeric(trades_df["return_pct"], errors="coerce") * pd.to_numeric(
        trades_df["cost_basis"], errors="coerce"
    )


def _evaluate_entry_filters(
    ticker: str,
    entry_date: str,
    settings: Any,
    *,
    cache_only: bool,
    live_news: bool,
) -> dict[str, Any]:
    llm_ok, llm_reason = evaluate_ticker_consensus(
        ticker,
        settings=settings,
        as_of_date=entry_date,
        cache_only=cache_only,
    )
    news_ok = True
    news_score: float | None = None
    news_reason = ""
    if getattr(settings, "news_sentiment_enabled", False):
        if live_news:
            news_score = get_ticker_sentiment(ticker)
            threshold = float(getattr(settings, "news_sentiment_threshold", -0.30))
            if news_score is not None and news_score < threshold:
                news_ok = False
                news_reason = (
                    f"negative news sentiment (score={news_score:.2f}, threshold={threshold})"
                )
        else:
            news_reason = "news_sentiment skipped (cache-only replay; use --live-news)"

    would_enter = bool(llm_ok and news_ok)
    return {
        "ticker": ticker,
        "entry_date": entry_date,
        "llm_approved": llm_ok,
        "llm_reason": llm_reason,
        "news_approved": news_ok,
        "news_score": news_score,
        "news_reason": news_reason,
        "would_enter": would_enter,
    }


def build_llm_backtest_impact_report(
    backtest_dir: str | Path = DEFAULT_BACKTEST_DIR,
    settings: Any | None = None,
    *,
    cache_only: bool = True,
    live_news: bool = False,
    max_trades: int | None = None,
) -> dict[str, Any]:
    """Replay portfolio trades through LLM (+ optional news) filters.

    cache_only: use data/llm_cache.json per ticker+entry_date only (no API).
    live_news: call VADER on current headlines (indicative, not historical).
    """
    backtest_dir = Path(backtest_dir)
    settings = settings or load_settings()
    trades_path = backtest_dir / "portfolio_trades.csv"
    if not trades_path.is_file():
        raise FileNotFoundError(f"Missing {trades_path}")

    summary = load_summary_row(backtest_dir / "portfolio_summary.csv")
    trades = pd.read_csv(trades_path)
    trades["pnl"] = _trade_pnl(trades)
    trades["entry_date"] = pd.to_datetime(trades["entry_date"], errors="coerce").dt.strftime(
        "%Y-%m-%d"
    )
    if max_trades is not None and max_trades > 0:
        trades = trades.head(int(max_trades)).copy()

    mode = "cache_replay" if cache_only and not live_news else "live_probe"
    evaluations: list[dict[str, Any]] = []
    for _, row in trades.iterrows():
        entry = row["entry_date"]
        if not entry or entry == "NaT":
            continue
        meta = _evaluate_entry_filters(
            str(row["ticker"]),
            entry,
            settings,
            cache_only=cache_only,
            live_news=live_news,
        )
        meta["pnl"] = float(row["pnl"])
        evaluations.append(meta)

    eval_df = pd.DataFrame(evaluations)
    if eval_df.empty:
        raise ValueError("No trade entries evaluated")

    baseline_pnl = float(trades["pnl"].sum())
    blocked = eval_df[~eval_df["would_enter"]]
    approved = eval_df[eval_df["would_enter"]]
    adjusted_pnl = float(approved["pnl"].sum()) if not approved.empty else 0.0

    blocked_losses = float(blocked.loc[blocked["pnl"] < 0, "pnl"].sum()) if not blocked.empty else 0.0
    blocked_gains = float(blocked.loc[blocked["pnl"] > 0, "pnl"].sum()) if not blocked.empty else 0.0

    strat_return = float(summary["total_return"])
    bench_return = float(summary["benchmark_return"])
    pnl_ratio = adjusted_pnl / baseline_pnl if abs(baseline_pnl) > 1e-9 else 1.0
    approx_adjusted_return = strat_return * pnl_ratio

    notes = [
        "Trade-level replay: approximate portfolio return scales realized trade PnL ratio.",
        "LLM cache keys are {ticker}_{YYYY-MM-DD}; populate via paper/live runs for historical accuracy.",
    ]
    if live_news:
        notes.append("News sentiment uses current yfinance headlines (not entry-date history).")

    report = {
        "generated_at": _utc_now_iso(),
        "mode": mode,
        "baseline": {
            "strategy_return_pct": round(strat_return * 100.0, 4),
            "benchmark_return_pct": round(bench_return * 100.0, 4),
            "trade_count": int(len(trades)),
            "realized_pnl_sum": round(baseline_pnl, 2),
        },
        "with_live_filters": {
            "approx_strategy_return_pct": round(approx_adjusted_return * 100.0, 4),
            "approx_gap_vs_benchmark_pp": round(
                (approx_adjusted_return - bench_return) * 100.0, 4
            ),
            "beats_benchmark_approx": approx_adjusted_return >= bench_return,
            "approved_trades": int(len(approved)),
            "blocked_trades": int(len(blocked)),
            "adjusted_realized_pnl_sum": round(adjusted_pnl, 2),
        },
        "trade_level": {
            "llm_reject_count": int((~eval_df["llm_approved"]).sum()),
            "news_reject_count": int((~eval_df["news_approved"]).sum()),
            "blocked_pnl_sum": round(float(blocked["pnl"].sum()), 2) if not blocked.empty else 0.0,
            "blocked_losses_avoided": round(-blocked_losses, 2),
            "blocked_gains_missed": round(blocked_gains, 2),
        },
        "notes": notes,
        "sample_blocks": blocked.head(10).to_dict(orient="records"),
    }
    return report


def validate_llm_backtest_impact_report(report: dict[str, Any]) -> None:
    for key in LLM_BACKTEST_IMPACT_KEYS:
        if key not in report:
            raise ValueError(f"Missing LLM backtest impact key: {key}")


def format_llm_backtest_impact_report(report: dict[str, Any]) -> str:
    base = report["baseline"]
    adj = report["with_live_filters"]
    tl = report["trade_level"]
    lines = [
        "=== LLM / news filter impact on backtest trades ===",
        f"Mode: {report.get('mode')}",
        f"Baseline strategy return: {base['strategy_return_pct']}% "
        f"({base['trade_count']} trades, PnL sum ${base['realized_pnl_sum']:.0f})",
        f"After filters (approx): {adj['approx_strategy_return_pct']}% "
        f"(gap vs bench {adj['approx_gap_vs_benchmark_pp']:+.2f} pp, "
        f"beats_benchmark≈{adj['beats_benchmark_approx']})",
        f"Blocked: {adj['blocked_trades']} trades | "
        f"losses avoided ${tl['blocked_losses_avoided']:.0f} | "
        f"gains missed ${tl['blocked_gains_missed']:.0f}",
        f"LLM rejects: {tl['llm_reject_count']} | News rejects: {tl['news_reject_count']}",
    ]
    for note in report.get("notes") or []:
        lines.append(f"  note: {note}")
    return "\n".join(lines)


def write_llm_backtest_impact_artifacts(
    report: dict[str, Any],
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    validate_llm_backtest_impact_report(report)
    path = output_dir / "latest_summary.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def run_llm_backtest_impact_report(
    backtest_dir: str | Path = DEFAULT_BACKTEST_DIR,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    *,
    cache_only: bool = True,
    live_news: bool = False,
    max_trades: int | None = None,
) -> dict[str, Any]:
    report = build_llm_backtest_impact_report(
        backtest_dir,
        cache_only=cache_only,
        live_news=live_news,
        max_trades=max_trades,
    )
    write_llm_backtest_impact_artifacts(report, output_dir)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM/news filter impact on portfolio backtest trades")
    parser.add_argument("--backtest-dir", default=str(DEFAULT_BACKTEST_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument(
        "--live-llm",
        action="store_true",
        help="Call Gemini on cache miss (uses current news; slow)",
    )
    parser.add_argument(
        "--live-news",
        action="store_true",
        help="Apply VADER news_sentiment with current headlines",
    )
    parser.add_argument(
        "--max-trades",
        type=int,
        default=None,
        help="Limit trade replay count (live probe sampling)",
    )
    args = parser.parse_args()
    report = run_llm_backtest_impact_report(
        args.backtest_dir,
        args.output_dir,
        cache_only=not args.live_llm,
        live_news=args.live_news,
        max_trades=args.max_trades,
    )
    print(format_llm_backtest_impact_report(report))
    print(f"\nWrote {args.output_dir}/latest_summary.json")


if __name__ == "__main__":
    main()
