import json
from pathlib import Path

from src.model_quality_summary import build_model_quality_summary


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_model_quality_summary_keeps_ai_as_filter_when_gates_fail(tmp_path: Path) -> None:
    ml_dir = tmp_path / "ml"
    _write_json(
        ml_dir / "model_promotion_report.json",
        {
            "challenger_avg_roc_auc": 0.5094,
            "champion_avg_roc_auc": 0.5075,
            "ml_quality_gate_failures": [
                "overall_avg_brier_score=0.3371 > max 0.2500"
            ],
            "challenger_portfolio_oos": {
                "total_return": 0.0683,
                "benchmark_return": 0.1856,
            },
        },
    )
    _write_json(
        ml_dir / "model_calibration_report.json",
        {"overall_avg_brier_score": 0.0, "bin_count": 0},
    )
    _write_json(
        ml_dir / "fold_stability_report.json",
        {
            "roc_auc": {"mean": 0.5094, "std": 0.0745},
            "by_regime": {"BULL": {"mean": 0.49}},
        },
    )
    _write_json(
        ml_dir / "threshold_retune_report.json",
        {"best_buy_threshold": 0.4, "best_exit_threshold": 0.4},
    )
    benchmark = tmp_path / "benchmark_gap.json"
    _write_json(benchmark, {"beats_benchmark": True, "gap_pct": 8.9964})

    report = build_model_quality_summary(
        ml_dir=ml_dir,
        benchmark_gap_path=benchmark,
        rank_label_path=tmp_path / "missing_rank_label.json",
    )

    assert report["decision"] == "keep_ai_as_filter_and_sizing_overlay"
    assert report["health"] == "needs_work"
    assert report["metrics"]["overall_avg_brier_score"] == 0.3371
    assert "Probability calibration is poor" in " ".join(report["blockers"])


def test_model_quality_summary_includes_rank_label_gate_failure(tmp_path: Path) -> None:
    ml_dir = tmp_path / "ml"
    _write_json(
        ml_dir / "model_promotion_report.json",
        {"challenger_avg_roc_auc": 0.55, "challenger_portfolio_oos": {}},
    )
    _write_json(
        ml_dir / "model_calibration_report.json",
        {"overall_avg_brier_score": 0.2, "bin_count": 10},
    )
    _write_json(
        ml_dir / "fold_stability_report.json",
        {"roc_auc": {"mean": 0.55, "std": 0.02}},
    )
    _write_json(ml_dir / "label_horizon_report.json", {"status": "ok"})
    benchmark = tmp_path / "benchmark_gap.json"
    rank_label = tmp_path / "rank_label.json"
    _write_json(benchmark, {"beats_benchmark": True, "gap_pct": 8.9964})
    _write_json(
        rank_label,
        {
            "metrics": {"top_bucket_auc": 0.58436},
            "portfolio_oos": {
                "gap_pct": 1.6094,
                "sharpe_ratio": 0.9911,
                "max_drawdown": -0.1973,
                "turnover_proxy": 1.076,
            },
            "gate": {"passed": False},
        },
    )

    report = build_model_quality_summary(
        ml_dir=ml_dir,
        benchmark_gap_path=benchmark,
        rank_label_path=rank_label,
    )

    assert report["metrics"]["rank_label_top_bucket_auc"] == 0.5844
    assert report["metrics"]["rank_label_oos_gap_pct"] == 1.6094
    assert "Cross-sectional rank AI" in " ".join(report["blockers"])
