"""Decompose portfolio backtest underperformance vs benchmark."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.sector import get_sector

DEFAULT_BACKTEST_DIR = Path("logs/portfolio_backtest")
DEFAULT_OUTPUT_DIR = Path("logs/benchmark_gap")
SLIPPAGE_SUMMARY_PATH = Path("logs/slippage_reports/latest_summary.json")

BENCHMARK_GAP_REPORT_KEYS = (
    "generated_at",
    "summary",
    "gap_pct",
    "beats_benchmark",
    "by_ticker",
    "by_sector",
    "by_entry_month",
    "slippage_context",
    "recommendations",
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_summary(backtest_dir: Path) -> dict[str, Any]:
    summary_path = backtest_dir / "portfolio_summary.csv"
    if not summary_path.is_file():
        raise FileNotFoundError(f"Missing {summary_path}")
    row = pd.read_csv(summary_path).iloc[0]
    out: dict[str, Any] = {}
    for col in row.index:
        if col == "trades":
            out[col] = int(row[col])
        else:
            val = row[col]
            out[col] = float(val) if pd.notna(val) else float("nan")
    return out


def _trade_pnl(trades_df: pd.DataFrame) -> pd.Series:
    if "exit_value" in trades_df.columns and "cost_basis" in trades_df.columns:
        return pd.to_numeric(trades_df["exit_value"], errors="coerce") - pd.to_numeric(
            trades_df["cost_basis"], errors="coerce"
        )
    return pd.to_numeric(trades_df["return_pct"], errors="coerce") * pd.to_numeric(
        trades_df["cost_basis"], errors="coerce"
    )


def build_benchmark_gap_report(
    backtest_dir: str | Path = DEFAULT_BACKTEST_DIR,
) -> dict[str, Any]:
    backtest_dir = Path(backtest_dir)
    summary = _load_summary(backtest_dir)
    trades_path = backtest_dir / "portfolio_trades.csv"
    if not trades_path.is_file():
        raise FileNotFoundError(f"Missing {trades_path}")

    trades = pd.read_csv(trades_path)
    trades["pnl"] = _trade_pnl(trades)
    trades["entry_date"] = pd.to_datetime(trades["entry_date"], errors="coerce")
    trades["sector"] = trades["ticker"].astype(str).map(get_sector)

    bench_ret = summary.get("benchmark_return", float("nan"))
    bench_valid = bench_ret == bench_ret
    gap_pct = (
        round((summary["total_return"] - bench_ret) * 100.0, 4) if bench_valid else float("nan")
    )

    by_ticker = (
        trades.groupby("ticker", as_index=False)["pnl"]
        .sum()
        .sort_values("pnl")
        .head(10)
        .to_dict(orient="records")
    )
    by_sector = (
        trades.groupby("sector", as_index=False)["pnl"]
        .sum()
        .sort_values("pnl")
        .to_dict(orient="records")
    )
    trades["entry_month"] = trades["entry_date"].dt.to_period("M").astype(str)
    by_entry_month = (
        trades.groupby("entry_month", as_index=False)["pnl"]
        .sum()
        .sort_values("entry_month")
        .to_dict(orient="records")
    )

    slippage_context: dict[str, Any] = {}
    if SLIPPAGE_SUMMARY_PATH.is_file():
        slippage = json.loads(SLIPPAGE_SUMMARY_PATH.read_text(encoding="utf-8"))
        slippage_context = {
            "overall_avg_slippage_pct": slippage.get("overall_avg_slippage_pct"),
            "matched_trades": slippage.get("matched_trades"),
            "status": slippage.get("status"),
            "note": "Paper slippage is execution-only; backtest gap is simulation vs SPY buy-hold.",
        }

    beats_benchmark = bool(bench_valid and gap_pct >= 0)
    recommendations: list[str] = []
    if not bench_valid:
        recommendations.append(
            "Benchmark return missing in portfolio_summary.csv — re-run "
            "`python -m src.run_portfolio_backtest` after fixing equal-weight benchmark."
        )
    elif not beats_benchmark:
        recommendations.append(
            "Portfolio underperforms equal-weight universe buy-hold — tune rank_ai_weight, "
            "ai_score_buy_threshold, or relative_strength_filter (config/strategy_config.json)."
        )
        if bench_valid and by_ticker:
            worst = by_ticker[0]
            recommendations.append(
                f"Largest drag: {worst.get('ticker')} PnL ${float(worst.get('pnl', 0)):.0f} — review exits or exclude in research branch."
            )
        worst_sectors = sorted(by_sector, key=lambda r: float(r.get("pnl", 0)))[:2]
        for row in worst_sectors:
            if float(row.get("pnl", 0)) < 0:
                recommendations.append(
                    f"Sector drag: {row.get('sector')} ${float(row.get('pnl', 0)):.0f}"
                )

    report = {
        "generated_at": _utc_now_iso(),
        "summary": summary,
        "gap_pct": gap_pct,
        "beats_benchmark": beats_benchmark,
        "by_ticker": by_ticker,
        "by_sector": by_sector,
        "by_entry_month": by_entry_month,
        "slippage_context": slippage_context,
        "recommendations": recommendations,
    }
    validate_benchmark_gap_report(report)
    return report


def validate_benchmark_gap_report(report: dict[str, Any]) -> dict[str, Any]:
    for key in BENCHMARK_GAP_REPORT_KEYS:
        if key not in report:
            raise ValueError(f"Missing benchmark gap report key: {key}")
    return report


def format_benchmark_gap_report(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "=== Portfolio vs benchmark gap ===",
        f"Strategy return: {summary['total_return']*100:.2f}%",
        f"Benchmark return: {summary['benchmark_return']*100:.2f}%",
        f"Gap: {report['gap_pct']:.2f} pp",
        f"Max drawdown: {summary['max_drawdown']*100:.2f}%",
        f"Trades: {summary['trades']} | Win rate: {summary['win_rate']*100:.1f}%",
        "",
        "Worst tickers (PnL):",
    ]
    for row in report["by_ticker"][:5]:
        lines.append(f"  {row['ticker']}: ${row['pnl']:.2f}")
    lines.append("Sector PnL:")
    for row in report["by_sector"]:
        lines.append(f"  {row['sector']}: ${row['pnl']:.2f}")
    if report.get("slippage_context"):
        slip = report["slippage_context"]
        lines.append(
            f"\nSlippage (paper): avg {slip.get('overall_avg_slippage_pct')}% "
            f"({slip.get('matched_trades')} matches)"
        )
    if report.get("recommendations"):
        lines.append("\nRecommendations:")
        for rec in report["recommendations"]:
            lines.append(f"  - {rec}")
    return "\n".join(lines)


def write_benchmark_gap_artifacts(
    report: dict[str, Any],
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "latest_summary.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark gap decomposition report")
    parser.add_argument("--backtest-dir", default=str(DEFAULT_BACKTEST_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    report = build_benchmark_gap_report(args.backtest_dir)
    path = write_benchmark_gap_artifacts(report, Path(args.output_dir))
    print(format_benchmark_gap_report(report))
    print(f"\nWrote {path}")


if __name__ == "__main__":
    main()
