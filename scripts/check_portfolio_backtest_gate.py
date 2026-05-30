#!/usr/bin/env python3
"""CI/post-workflow gate for logs/portfolio_backtest/portfolio_summary.csv."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.portfolio_backtest_validation import (  # noqa: E402
    PortfolioBacktestThresholds,
    check_portfolio_backtest_thresholds,
)


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    return float(raw) if raw is not None else default


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dir",
        type=Path,
        default=Path("logs/portfolio_backtest"),
        help="Directory with portfolio_* CSV outputs",
    )
    parser.add_argument(
        "--max-drawdown-floor",
        type=float,
        default=None,
        help="Fail if max_drawdown is below this (default: env or -0.20)",
    )
    parser.add_argument(
        "--min-return-vs-benchmark",
        type=float,
        default=None,
        help="Fail if (total_return - benchmark_return) below this (default: -0.15)",
    )
    parser.add_argument(
        "--min-sharpe",
        type=float,
        default=None,
        help="Optional minimum sharpe_ratio",
    )
    args = parser.parse_args()

    thresholds = PortfolioBacktestThresholds(
        max_drawdown_floor=args.max_drawdown_floor
        if args.max_drawdown_floor is not None
        else _env_float("PORTFOLIO_MAX_DRAWDOWN_FLOOR", -0.20),
        min_return_vs_benchmark=args.min_return_vs_benchmark
        if args.min_return_vs_benchmark is not None
        else _env_float("PORTFOLIO_MIN_RETURN_VS_BENCHMARK", -0.15),
        min_sharpe=args.min_sharpe,
    )

    result = check_portfolio_backtest_thresholds(args.dir, thresholds)
    summary = result.summary
    print(
        f"portfolio gate: total_return={summary['total_return']:.4f} "
        f"benchmark={summary['benchmark_return']:.4f} "
        f"max_drawdown={summary['max_drawdown']:.4f} "
        f"sharpe={summary['sharpe_ratio']:.4f}"
    )
    for w in result.warnings:
        print(f"WARNING: {w}")
    for f in result.failures:
        print(f"FAIL: {f}", file=sys.stderr)

    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
