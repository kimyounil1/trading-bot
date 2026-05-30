"""Post-workflow audit summary gate ([AGY])."""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECK_SCRIPT = ROOT / "scripts" / "check_audit_daily_summary.py"
GOLDEN_SUMMARY = ROOT / "tests/fixtures/audit_daily/golden_latest_summary.json"


def _run_check(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    return subprocess.run(
        [sys.executable, str(CHECK_SCRIPT), *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_check_audit_daily_summary_validates_fixture(tmp_path):
    summary = tmp_path / "latest_summary.json"
    summary.write_text(GOLDEN_SUMMARY.read_text(encoding="utf-8"), encoding="utf-8")
    result = _run_check("--path", str(summary))
    assert result.returncode == 0
    assert "audit daily summary ok" in result.stdout


def test_check_audit_daily_summary_skips_missing(tmp_path):
    missing = tmp_path / "missing.json"
    result = _run_check("--path", str(missing))
    assert result.returncode == 0
    assert "skip" in result.stdout


def test_check_audit_daily_summary_require_fails(tmp_path):
    missing = tmp_path / "missing.json"
    result = _run_check("--path", str(missing), "--require")
    assert result.returncode == 1
