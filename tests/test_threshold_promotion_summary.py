import json
from pathlib import Path

from src.threshold_promotion_summary import (
    SUMMARY_KEYS,
    build_threshold_promotion_summary,
)


def test_build_threshold_promotion_summary_actions(tmp_path: Path):
    ml = tmp_path / "ml"
    mq = tmp_path / "model_quality"
    ml.mkdir()
    mq.mkdir()

    (ml / "threshold_retune_report.json").write_text(
        json.dumps({"best_buy_threshold": 0.55}),
        encoding="utf-8",
    )
    (ml / "model_promotion_report.json").write_text(
        json.dumps({"decision": "RETAIN", "ml_quality_gate_failures": ["auc"]}),
        encoding="utf-8",
    )
    (ml / "label_challenger_sweep_report.json").write_text(
        json.dumps(
            {
                "recommendation": "keep champion",
                "best_by_portfolio_gap": {"slug": "h20_t0p02"},
            }
        ),
        encoding="utf-8",
    )

    report = build_threshold_promotion_summary(ml_dir=ml, model_quality_dir=mq)
    for key in SUMMARY_KEYS:
        assert key in report
    assert report["promotion"]["decision"] == "RETAIN"
    assert any("ai_score_buy_threshold=0.55" in action for action in report["recommended_actions"])
    assert any("promotion remains blocked" in action.lower() for action in report["recommended_actions"])
    assert any("keep champion" in action for action in report["recommended_actions"])
