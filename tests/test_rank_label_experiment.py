from src.rank_label_experiment import validate_rank_label_report


def test_validate_rank_label_report_schema():
    report = {
        "generated_at": "2026-01-01T00:00:00Z",
        "label": {"kind": "cross_sectional_future_return_percentile"},
        "metrics": {"top_bucket_auc": 0.55},
        "portfolio_oos": {"gap_pct": 1.0},
        "benchmark_oos": {"return": 0.1},
        "gate": {"passed": True},
        "recommendation": "review",
        "artifacts": {},
    }

    assert validate_rank_label_report(report) is report
