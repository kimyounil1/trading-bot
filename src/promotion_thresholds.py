"""Portfolio OOS gates for champion promotion (stricter than CI post-workflow)."""

from __future__ import annotations

import os

from src.portfolio_backtest_validation import PortfolioBacktestThresholds


def promotion_portfolio_thresholds() -> PortfolioBacktestThresholds:
    """Challenger must beat benchmark (excess return >= 0) unless env overrides."""
    min_vs = float(os.environ.get("PROMOTION_MIN_RETURN_VS_BENCHMARK", "0.0"))
    min_sharpe_raw = os.environ.get("PROMOTION_MIN_SHARPE", "1.0")
    min_sharpe = float(min_sharpe_raw) if min_sharpe_raw.strip() else None
    return PortfolioBacktestThresholds(
        max_drawdown_floor=float(os.environ.get("PROMOTION_MAX_DRAWDOWN_FLOOR", "-0.20")),
        min_return_vs_benchmark=min_vs,
        min_sharpe=min_sharpe,
    )


def ci_portfolio_thresholds() -> PortfolioBacktestThresholds:
    """Post-workflow / CI: allow moderate benchmark underperformance."""
    return PortfolioBacktestThresholds(
        max_drawdown_floor=-0.20,
        min_return_vs_benchmark=-0.15,
        min_sharpe=None,
    )
