from pathlib import Path

from src.tournament_score_report import build_tournament_score_report


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
