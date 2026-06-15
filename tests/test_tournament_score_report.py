from pathlib import Path

from src.tournament_score_report import (
    _tournament_verdict,
    build_tournament_score_report,
    format_tournament_score_summary,
)


def test_tournament_score_report_structure(tmp_path: Path) -> None:
    sleeve_dir = tmp_path / "sleeves"
    sleeve_dir.mkdir()
    (sleeve_dir / "latest_summary.json").write_text(
        '{"sleeves":{"tournament":{"return_pct":0.05,"turnover":2}}}',
        encoding="utf-8",
    )
    report = build_tournament_score_report(
        sleeve_summary_path=sleeve_dir / "latest_summary.json",
    )
    assert report["lookback_days"] == 21
    assert report["live_enabled"] is False
    assert "benchmarks" in report
    assert report["verdict"] in {"PASS", "FAIL", "INSUFFICIENT_DATA"}
    assert "min_excess_return_pct" in report


def test_verdict_pass_when_beating_benchmark() -> None:
    verdict = _tournament_verdict(
        tournament_return=0.08,
        best_bench_name="SPY",
        best_bench_return=0.05,
        excess=0.03,
        min_excess_return_pct=0.0,
    )
    assert verdict["verdict"] == "PASS"
    assert verdict["passed"] is True
    assert "SPY" in verdict["reason"]


def test_verdict_fail_when_underperforming() -> None:
    verdict = _tournament_verdict(
        tournament_return=0.02,
        best_bench_name="QQQ",
        best_bench_return=0.05,
        excess=-0.03,
        min_excess_return_pct=0.0,
    )
    assert verdict["verdict"] == "FAIL"
    assert verdict["passed"] is False


def test_verdict_respects_min_excess_threshold() -> None:
    # Beats benchmark but not by the required margin -> FAIL.
    verdict = _tournament_verdict(
        tournament_return=0.051,
        best_bench_name="MTUM",
        best_bench_return=0.05,
        excess=0.001,
        min_excess_return_pct=0.02,
    )
    assert verdict["verdict"] == "FAIL"


def test_verdict_insufficient_data_when_returns_missing() -> None:
    verdict = _tournament_verdict(
        tournament_return=None,
        best_bench_name="",
        best_bench_return=None,
        excess=None,
        min_excess_return_pct=0.0,
    )
    assert verdict["verdict"] == "INSUFFICIENT_DATA"
    assert verdict["passed"] is None


def test_format_summary_includes_verdict() -> None:
    report = {
        "lookback_days": 21,
        "tournament_sleeve": {"return_pct": 0.08, "max_drawdown_pct": -0.05},
        "best_benchmark": "SPY",
        "best_benchmark_return_pct": 0.05,
        "excess_return_vs_best_benchmark_pct": 0.03,
        "min_excess_return_pct": 0.0,
        "verdict": "PASS",
        "verdict_ko": "토너먼트 슬리브 PASS",
        "live_enabled": False,
    }
    summary = format_tournament_score_summary(report)
    assert "Verdict: PASS" in summary
    assert "Mode: PAPER" in summary
    assert "+8.00%" in summary
