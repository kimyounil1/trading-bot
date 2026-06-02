from src.label_challenger_experiment import validate_label_challenger_report


def test_validate_label_challenger_report_schema():
    report = {
        "generated_at": "2026-01-01T00:00:00Z",
        "label_candidate": {"prediction_horizon": 20, "target_return_threshold": 0.02},
        "metrics": {"avg_roc_auc": 0.55},
        "ml_quality_gate": {"passed": False},
        "challenger_portfolio_oos": {"total_return": 0.1},
        "champion_portfolio_oos": {"total_return": 0.08},
        "promotion_report": {"decision": "RETAIN_CHAMPION"},
        "decision": "retain_champion",
        "recommendation": "review",
        "artifacts": {},
    }

    assert validate_label_challenger_report(report) is report
