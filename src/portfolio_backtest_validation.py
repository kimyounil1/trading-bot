"""Validate portfolio backtest CSV outputs (schema + optional golden metrics)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

SUMMARY_COLUMNS = (
    "initial_cash",
    "final_equity",
    "total_return",
    "benchmark_return",
    "max_drawdown",
    "sharpe_ratio",
    "trades",
    "win_rate",
)

EQUITY_COLUMNS = (
    "date",
    "cash",
    "positions_value",
    "equity",
    "positions_count",
    "open_symbols",
    "daily_return",
    "running_max",
    "drawdown",
    "benchmark_equity",
)

TRADES_COLUMNS = (
    "ticker",
    "entry_date",
    "exit_date",
    "entry_price",
    "exit_price",
    "qty",
    "cost_basis",
    "exit_value",
    "return_pct",
    "exit_reason",
)

SUMMARY_METRIC_KEYS = (
    "initial_cash",
    "final_equity",
    "total_return",
    "benchmark_return",
    "max_drawdown",
    "sharpe_ratio",
    "trades",
    "win_rate",
)


def _require_columns(df: pd.DataFrame, required: tuple[str, ...], label: str) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"{label}: missing columns {missing}")


def load_summary_row(path: Path) -> dict[str, Any]:
    df = pd.read_csv(path)
    if df.empty:
        raise ValueError(f"{path}: summary is empty")
    _require_columns(df, SUMMARY_COLUMNS, "portfolio_summary")
    row = df.iloc[0]
    out: dict[str, Any] = {}
    for key in SUMMARY_METRIC_KEYS:
        val = row[key]
        if key == "trades":
            out[key] = int(val)
        elif key in ("initial_cash", "final_equity"):
            out[key] = float(val)
        else:
            out[key] = float(val)
    return out


def validate_portfolio_backtest_dir(
    output_dir: str | Path,
    *,
    golden_summary: dict[str, Any] | None = None,
    summary_rtol: float = 1e-4,
    summary_atol: float = 1e-6,
    min_equity_rows: int = 2,
    min_trades_rows: int = 0,
) -> dict[str, Any]:
    """Validate the three portfolio backtest CSVs under ``output_dir``."""
    output_dir = Path(output_dir)
    summary_path = output_dir / "portfolio_summary.csv"
    equity_path = output_dir / "portfolio_equity.csv"
    trades_path = output_dir / "portfolio_trades.csv"

    for path in (summary_path, equity_path, trades_path):
        if not path.is_file():
            raise FileNotFoundError(f"Missing portfolio backtest artifact: {path}")

    summary = load_summary_row(summary_path)

    equity_df = pd.read_csv(equity_path)
    _require_columns(equity_df, EQUITY_COLUMNS, "portfolio_equity")
    if len(equity_df) < min_equity_rows:
        raise ValueError(
            f"portfolio_equity: expected at least {min_equity_rows} rows, got {len(equity_df)}"
        )
    if equity_df["equity"].isna().any():
        raise ValueError("portfolio_equity: NaN in equity column")

    trades_df = pd.read_csv(trades_path)
    _require_columns(trades_df, TRADES_COLUMNS, "portfolio_trades")
    if len(trades_df) < min_trades_rows:
        raise ValueError(
            f"portfolio_trades: expected at least {min_trades_rows} rows, got {len(trades_df)}"
        )

    if int(summary["trades"]) != len(trades_df):
        raise ValueError(
            f"summary trades={summary['trades']} != trades rows={len(trades_df)}"
        )

    if golden_summary is not None:
        import numpy as np

        for key in SUMMARY_METRIC_KEYS:
            if key not in golden_summary:
                raise KeyError(f"golden_summary missing key: {key}")
            expected = golden_summary[key]
            actual = summary[key]
            if key == "trades":
                if int(actual) != int(expected):
                    raise AssertionError(
                        f"{key}: expected {expected}, got {actual}"
                    )
            elif not np.isclose(actual, float(expected), rtol=summary_rtol, atol=summary_atol):
                raise AssertionError(
                    f"{key}: expected {expected}, got {actual}"
                )

    return {
        "summary": summary,
        "equity_rows": len(equity_df),
        "trades_rows": len(trades_df),
    }


@dataclass
class PortfolioBacktestThresholds:
    """OOS / CI gates on portfolio_summary.csv (not golden fixture regression)."""

    max_drawdown_floor: float = -0.20
    min_return_vs_benchmark: float = -0.15
    min_sharpe: float | None = None


@dataclass
class PortfolioBacktestThresholdResult:
    summary: dict[str, Any]
    passed: bool
    failures: list[str]
    warnings: list[str]


def _apply_portfolio_thresholds_to_summary(
    summary: dict[str, Any],
    thresholds: PortfolioBacktestThresholds,
) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    warnings: list[str] = []

    max_dd = float(summary["max_drawdown"])
    if max_dd < thresholds.max_drawdown_floor:
        failures.append(
            f"max_drawdown {max_dd:.4f} worse than floor {thresholds.max_drawdown_floor:.4f}"
        )

    excess_vs_bench = float(summary["total_return"]) - float(summary["benchmark_return"])
    if excess_vs_bench < thresholds.min_return_vs_benchmark:
        failures.append(
            f"total_return - benchmark_return = {excess_vs_bench:.4f} "
            f"< min {thresholds.min_return_vs_benchmark:.4f}"
        )
    elif excess_vs_bench < 0:
        warnings.append(
            f"underperforms benchmark by {-excess_vs_bench:.4f} (within allowed gap)"
        )

    if thresholds.min_sharpe is not None:
        sharpe = float(summary["sharpe_ratio"])
        if sharpe < thresholds.min_sharpe:
            failures.append(f"sharpe_ratio {sharpe:.4f} < min {thresholds.min_sharpe:.4f}")

    return failures, warnings


def check_portfolio_summary_thresholds(
    summary: dict[str, Any],
    thresholds: PortfolioBacktestThresholds | None = None,
) -> PortfolioBacktestThresholdResult:
    """Apply portfolio-level gates to an in-memory summary row (retrain promotion)."""
    thresholds = thresholds or PortfolioBacktestThresholds()
    failures, warnings = _apply_portfolio_thresholds_to_summary(summary, thresholds)
    return PortfolioBacktestThresholdResult(
        summary=summary,
        passed=not failures,
        failures=failures,
        warnings=warnings,
    )


def check_portfolio_backtest_thresholds(
    output_dir: str | Path,
    thresholds: PortfolioBacktestThresholds | None = None,
    *,
    validate_schema: bool = True,
) -> PortfolioBacktestThresholdResult:
    """Apply portfolio-level gates after schema validation."""
    thresholds = thresholds or PortfolioBacktestThresholds()

    if validate_schema:
        result = validate_portfolio_backtest_dir(output_dir, min_equity_rows=2)
        summary = result["summary"]
    else:
        summary = load_summary_row(Path(output_dir) / "portfolio_summary.csv")

    failures, warnings = _apply_portfolio_thresholds_to_summary(summary, thresholds)
    return PortfolioBacktestThresholdResult(
        summary=summary,
        passed=not failures,
        failures=failures,
        warnings=warnings,
    )
