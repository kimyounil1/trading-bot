import json
from pathlib import Path

from src.label_challenger_sweep import (
    LabelCandidate,
    build_label_challenger_sweep,
    validate_label_challenger_sweep,
)


def test_build_label_challenger_sweep_ranks_by_portfolio_gate(tmp_path, monkeypatch):
    def fake_load(candidate, *, period, force):
        gap = -0.10 if candidate.slug == "h20_t0p02" else 0.05
        return {
            "metrics": {"avg_roc_auc": 0.55 if candidate.slug == "h20_t0p02" else 0.48},
            "challenger_portfolio_oos": {
                "total_return": 0.10 + gap,
                "benchmark_return": 0.10,
                "sharpe_ratio": 1.2,
                "max_drawdown": -0.08,
            },
            "decision": "retain_champion",
        }

    monkeypatch.setattr(
        "src.label_challenger_sweep._load_or_run_candidate",
        fake_load,
    )

    report = build_label_challenger_sweep(
        candidates=(
            LabelCandidate(20, 0.02),
            LabelCandidate(10, 0.0),
        ),
        period="5y",
        force_retrain=False,
    )

    validate_label_challenger_sweep(report)
    assert report["best_by_portfolio_gap"]["slug"] == "h10_t0p00"
    assert report["candidates"][0]["portfolio_gap_pct"] >= report["candidates"][1]["portfolio_gap_pct"]


def test_load_or_run_candidate_reads_legacy_h20_t0p02(tmp_path, monkeypatch):
    legacy_dir = tmp_path / "logs/ml/label_challenger"
    legacy_dir.mkdir(parents=True)
    (legacy_dir / "latest_summary.json").write_text(
        json.dumps(
            {
                "metrics": {"avg_roc_auc": 0.53},
                "challenger_portfolio_oos": {
                    "total_return": 0.05,
                    "benchmark_return": 0.10,
                    "sharpe_ratio": 0.5,
                    "max_drawdown": -0.12,
                },
                "decision": "retain_champion",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    from src.label_challenger_sweep import _load_or_run_candidate

    report = _load_or_run_candidate(LabelCandidate(20, 0.02), period="5y", force=False)
    assert report["decision"] == "retain_champion"
    assert report["metrics"]["avg_roc_auc"] == 0.53


def test_validate_label_challenger_sweep_schema():
    report = {
        "generated_at": "2026-01-01T00:00:00Z",
        "candidates": [],
        "best_by_portfolio_gap": None,
        "recommendation": "none",
    }
    assert validate_label_challenger_sweep(report) is report
