import json
from pathlib import Path

from src.execution_alignment_report import (
    build_execution_alignment_report,
    validate_execution_alignment_report,
)

FIXTURE_AUDIT = Path(__file__).resolve().parent / "fixtures" / "audit_daily" / "golden_latest_summary.json"


def test_execution_alignment_report_schema(tmp_path):
    slippage = tmp_path / "slippage.json"
    slippage.write_text(
        json.dumps(
            {
                "status": "ok",
                "matched_trades": 5,
                "overall_avg_slippage_pct": 0.12,
                "total_slippage_usd": 10.5,
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "out"
    report = build_execution_alignment_report(
        audit_path=FIXTURE_AUDIT,
        slippage_path=slippage,
        output_dir=out,
    )
    validate_execution_alignment_report(report)
    assert report["current"]["slippage_matched_trades"] == 5
    assert (out / "latest_summary.json").is_file()
