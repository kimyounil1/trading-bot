"""21-day tournament sleeve leaderboard vs benchmarks."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.data_loader import load_price_data_batch
from src.portfolio_sleeves import TOURNAMENT_SLEEVE_ID, load_sleeve_definitions
from src.settings import load_settings

DEFAULT_OUTPUT_DIR = Path("logs/tournament")
LOOKBACK_DAYS = 21
BENCHMARK_TICKERS = ("SPY", "QQQ", "MTUM")
# Tournament sleeve passes when it beats the best benchmark by at least this margin.
DEFAULT_MIN_EXCESS_RETURN_PCT = 0.0


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fmt_pct(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{float(value):+.2%}"


def _tournament_verdict(
    *,
    tournament_return: float | None,
    best_bench_name: str,
    best_bench_return: float | None,
    excess: float | None,
    min_excess_return_pct: float,
) -> dict[str, Any]:
    """Classify the sleeve as PASS / FAIL / INSUFFICIENT_DATA vs the best benchmark."""
    if tournament_return is None or best_bench_return is None or excess is None:
        return {
            "verdict": "INSUFFICIENT_DATA",
            "passed": None,
            "reason": "tournament sleeve return or benchmark return unavailable (paper observation pending)",
            "verdict_ko": "토너먼트 슬리브 판정 불가: 수익률/벤치마크 데이터 부족 (paper 관측 대기)",
        }
    bench_label = best_bench_name or "benchmark"
    if excess >= min_excess_return_pct:
        return {
            "verdict": "PASS",
            "passed": True,
            "reason": (
                f"excess {excess:+.4f} vs best benchmark {bench_label} "
                f">= threshold {min_excess_return_pct:+.4f}"
            ),
            "verdict_ko": f"토너먼트 슬리브 PASS: best benchmark({bench_label}) 대비 초과수익 {excess:+.2%}",
        }
    return {
        "verdict": "FAIL",
        "passed": False,
        "reason": (
            f"excess {excess:+.4f} vs best benchmark {bench_label} "
            f"< threshold {min_excess_return_pct:+.4f}"
        ),
        "verdict_ko": f"토너먼트 슬리브 FAIL: best benchmark({bench_label}) 대비 {excess:+.2%} (임계치 미달)",
    }


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
    min_excess_return_pct: float = DEFAULT_MIN_EXCESS_RETURN_PCT,
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

    verdict = _tournament_verdict(
        tournament_return=tournament_return,
        best_bench_name=best_bench_name,
        best_bench_return=best_bench_return,
        excess=excess,
        min_excess_return_pct=min_excess_return_pct,
    )

    tournament_def = load_sleeve_definitions(settings).get(TOURNAMENT_SLEEVE_ID)
    paper_only = bool(tournament_def.paper_only) if tournament_def else False
    live_enabled = (
        str(getattr(settings, "trading_environment", "paper")).lower() == "live"
        and not paper_only
    )

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
        "min_excess_return_pct": min_excess_return_pct,
        "verdict": verdict["verdict"],
        "verdict_passed": verdict["passed"],
        "verdict_reason": verdict["reason"],
        "verdict_ko": verdict["verdict_ko"],
        "paper_only": paper_only,
        "live_enabled": live_enabled,
        "sources": {"sleeve_summary": str(sleeve_summary_path)},
    }


def format_tournament_score_summary(report: dict[str, Any]) -> str:
    sleeve = report.get("tournament_sleeve") or {}
    lookback = report.get("lookback_days")
    return "\n".join(
        [
            "=== Tournament sleeve score ===",
            report.get("verdict_ko", ""),
            "",
            f"Verdict: {report.get('verdict')} "
            f"(threshold excess >= {_fmt_pct(report.get('min_excess_return_pct'))})",
            f"Tournament return ({lookback}d): {_fmt_pct(sleeve.get('return_pct'))}",
            f"Best benchmark: {report.get('best_benchmark') or '—'} "
            f"({_fmt_pct(report.get('best_benchmark_return_pct'))})",
            f"Excess vs best benchmark: {_fmt_pct(report.get('excess_return_vs_best_benchmark_pct'))}",
            f"Max drawdown: {_fmt_pct(sleeve.get('max_drawdown_pct'))}",
            f"Mode: {'LIVE' if report.get('live_enabled') else 'PAPER'}",
        ]
    )


def write_tournament_score_report(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    *,
    min_excess_return_pct: float = DEFAULT_MIN_EXCESS_RETURN_PCT,
) -> Path:
    report = build_tournament_score_report(min_excess_return_pct=min_excess_return_pct)
    output_dir.mkdir(parents=True, exist_ok=True)
    latest = output_dir / "latest_summary.json"
    latest.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    with (output_dir / "history.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(report, ensure_ascii=False) + "\n")
    return latest


def main() -> None:
    parser = argparse.ArgumentParser(description="Build tournament score summary")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument(
        "--min-excess-return-pct",
        type=float,
        default=DEFAULT_MIN_EXCESS_RETURN_PCT,
        help="Excess return vs best benchmark required for a PASS verdict (default 0.0).",
    )
    args = parser.parse_args()
    path = write_tournament_score_report(
        output_dir=Path(args.output_dir),
        min_excess_return_pct=args.min_excess_return_pct,
    )
    report = json.loads(path.read_text(encoding="utf-8"))
    print(format_tournament_score_summary(report))
    print(f"\nWrote {path}")


if __name__ == "__main__":
    main()
