#!/usr/bin/env python3
"""Post-workflow smoke: validate logs/audit_daily/latest_summary.json when present."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.daily_audit_summary import validate_daily_audit_summary  # noqa: E402

DEFAULT_PATH = Path("logs/audit_daily/latest_summary.json")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=DEFAULT_PATH)
    parser.add_argument(
        "--require",
        action="store_true",
        help="Fail if summary file is missing (default: skip when absent)",
    )
    args = parser.parse_args()

    if not args.path.is_file():
        if args.require:
            print(f"FAIL: audit summary not found: {args.path}", file=sys.stderr)
            return 1
        print(f"skip: {args.path} not found")
        return 0

    report = json.loads(args.path.read_text(encoding="utf-8"))
    validate_daily_audit_summary(report)
    print(
        f"audit daily summary ok: rows={report.get('row_count')} "
        f"api_errors={report.get('api_error_count')} "
        f"stale={report.get('stale_bar_count')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
