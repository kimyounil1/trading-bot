"""21-day tournament sleeve leaderboard vs benchmarks."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.data_loader import load_price_data_batch
from src.portfolio_sleeves import TOURNAMENT_SLEEVE_ID
from src.settings import load_settings

DEFAULT_OUTPUT_DIR = Path("logs/tournament")
LOOKBACK_DAYS = 21
BENCHMARK_TICKERS = ("SPY", "QQQ", "MTUM")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rolling_return(df: pd.DataFrame, days: int) -> float | None:
    if df is None or df.empty or len(df) < days + 1:
        return None
    close_col = "adj_close" if "adj_close" in df.columns else "close"
    start = float(df[close_col].iloc[-days - 1])
    end = float(df[close_col].iloc[-1])
    if start <= 0:
        return None
    return round((end / start) - 1.0, 6)


def _ew_universe_return(settings: Any, days: int) -> float | None:
    tickers = [str(t).upper() for t in getattr(settings, "tickers", [])[:20]]
    if not tickers:
        return None
    try:
        data = load_price_data_batch(tickers, period="3mo")
    except Exception:
        return None
    returns: list[float] = []
    for ticker in tickers:
        value = _rolling_return(data.get(ticker), days)
        if value is not None:
            returns.append(value)
    if not returns:
        return None
    return round(sum(returns) / len(returns), 6)


def build_tournament_score_report(
    *,
    sleeve_summary_path: Path = Path("logs/sleeves/latest_summary.json"),
    lookback_days: int = LOOKBACK_DAYS,
) -> dict[str, Any]:
    settings = load_settings()
    sleeve_summary = {}
    if sleeve_summary_path.is_file():
        try:
            sleeve_summary = json.loads(sleeve_summary_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            sleeve_summary = {}

    tournament = (sleeve_summary.get("sleeves") or {}).get(TOURNAMENT_SLEEVE_ID) or {}
    tournament_return = tournament.get("return_pct")

    benchmark_returns: dict[str, float | None] = {}
    try:
        bench_data = load_price_data_batch(list(BENCHMARK_TICKERS), period="3mo")
    except Exception:
        bench_data = {}
    for ticker in BENCHMARK_TICKERS:
        benchmark_returns[ticker] = _rolling_return(bench_data.get(ticker), lookback_days)
    benchmark_returns["EW"] = _ew_universe_return(settings, lookback_days)

    valid_bench = {k: v for k, v in benchmark_returns.items() if v is not None}
    best_bench_name = max(valid_bench, key=valid_bench.get) if valid_bench else ""
    best_bench_return = valid_bench.get(best_bench_name)

    excess = None
    if tournament_return is not None and best_bench_return is not None:
        excess = round(float(tournament_return) - float(best_bench_return), 6)

    return {
        "generated_at": _utc_now_iso(),
        "lookback_days": lookback_days,
        "tournament_sleeve": {
            "return_pct": tournament_return,
            "max_drawdown_pct": tournament.get("max_drawdown_pct"),
            "turnover": tournament.get("turnover"),
            "profit_factor": None,
            "order_budget": tournament.get("order_budget"),
            "target_weight": tournament.get("target_weight"),
        },
        "benchmarks": benchmark_returns,
        "best_benchmark": best_bench_name or None,
        "best_benchmark_return_pct": best_bench_return,
        "excess_return_vs_best_benchmark_pct": excess,
        "paper_only": True,
        "live_enabled": False,
        "sources": {"sleeve_summary": str(sleeve_summary_path)},
    }


def write_tournament_score_report(output_dir: Path = DEFAULT_OUTPUT_DIR) -> Path:
    report = build_tournament_score_report()
    output_dir.mkdir(parents=True, exist_ok=True)
    latest = output_dir / "latest_summary.json"
    latest.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    with (output_dir / "history.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(report, ensure_ascii=False) + "\n")
    return latest


def main() -> None:
    parser = argparse.ArgumentParser(description="Build tournament score summary")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    path = write_tournament_score_report(output_dir=Path(args.output_dir))
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
