"""Promotion must beat benchmark when using promotion_portfolio_thresholds."""

from src.ml_model import build_promotion_report
from src.promotion_thresholds import promotion_portfolio_thresholds


def _meta(auc: float) -> dict:
    return {"oos_metrics": {"avg_roc_auc": auc}}


def _portfolio(total: float, bench: float, sharpe: float = 1.5) -> dict:
    return {
        "total_return": total,
        "benchmark_return": bench,
        "max_drawdown": -0.1,
        "sharpe_ratio": sharpe,
        "trades": 10,
        "win_rate": 0.5,
    }


def test_promotion_rejected_when_under_benchmark():
    report = build_promotion_report(
        challenger_metadata=_meta(0.55),
        champion_metadata=_meta(0.50),
        challenger_portfolio=_portfolio(0.50, 0.58),
        champion_portfolio=_portfolio(0.48, 0.55),
        portfolio_thresholds=promotion_portfolio_thresholds(),
        require_portfolio_oos=True,
        require_ml_quality=False,
    )
    assert report["decision"] == "RETAIN_CHAMPION"
    assert not report["portfolio_gate_passed"]


def test_promotion_allowed_when_beats_benchmark_and_champion():
    report = build_promotion_report(
        challenger_metadata=_meta(0.55),
        champion_metadata=_meta(0.50),
        challenger_portfolio=_portfolio(0.62, 0.55, sharpe=1.8),
        champion_portfolio=_portfolio(0.50, 0.55, sharpe=1.2),
        portfolio_thresholds=promotion_portfolio_thresholds(),
        require_portfolio_oos=True,
        require_ml_quality=False,
    )
    assert report["decision"] == "PROMOTE"
