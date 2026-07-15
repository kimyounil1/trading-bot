"""One-off sanitizer for logs/execution_audit.csv.

May-June 2026 rows carry multi-thousand-char LLM chain-of-thought blobs in
reason/llm_verdict (pre parse_llm_decision fix), which breaks pd.read_csv and
forces the slow fallback reader. This rewrites the file in place (after a
timestamped backup): LLM blobs are re-parsed down to the final verdict via the
production parser, any other oversized field is truncated, and the result is
written with standard quoting so pd.read_csv works directly.

Usage: .venv/bin/python -m scripts.sanitize_execution_audit [--dry-run]
"""

from __future__ import annotations

import argparse
import csv
import shutil
from datetime import datetime
from pathlib import Path

from src.llm_analyst import parse_llm_decision

AUDIT_PATH = Path("logs/execution_audit.csv")
MAX_FIELD_LEN = 400
LLM_MARKERS = ("DECISION:", "REJECT:", "ACCEPT:")


def _shrink_llm_blob(text: str) -> str | None:
    """Re-parse a leaked chain-of-thought blob down to '[category] reason'."""
    if not any(marker in text for marker in LLM_MARKERS):
        return None
    approved, category, reason = parse_llm_decision(text)
    if not reason:
        return None
    verdict = "APPROVE" if approved else "REJECT"
    return f"{verdict}: [{category}] {reason}"


def sanitize_field(text: str) -> str:
    if len(text) <= MAX_FIELD_LEN:
        return text

    if "LLM Reject:" in text:
        prefix, _, blob = text.partition("LLM Reject:")
        shrunk = _shrink_llm_blob(blob)
        if shrunk is not None:
            return f"{prefix}LLM Reject: {shrunk}"
    shrunk = _shrink_llm_blob(text)
    if shrunk is not None:
        return shrunk
    return text[:MAX_FIELD_LEN].rstrip() + "…"


def main() -> None:
    parser = argparse.ArgumentParser(description="Sanitize execution_audit.csv LLM blobs")
    parser.add_argument("--path", default=str(AUDIT_PATH))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    path = Path(args.path)
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    header, data = rows[0], rows[1:]
    width = len(header)

    changed = 0
    padded = 0
    cleaned: list[list[str]] = []
    for fields in data:
        if not fields:
            continue
        if len(fields) != width:
            # Legacy rows predate schema additions; pad so every row parses uniformly.
            fields = (fields + [""] * width)[:width]
            padded += 1
        new_fields = []
        row_changed = False
        for cell in fields:
            new_cell = sanitize_field(cell) if len(cell) > MAX_FIELD_LEN else cell
            if new_cell != cell:
                row_changed = True
            new_fields.append(new_cell)
        if row_changed:
            changed += 1
        cleaned.append(new_fields)

    print(f"rows={len(cleaned)} shrunk={changed} width_padded={padded}")
    if args.dry_run:
        print("dry-run: no write")
        return

    stamp = datetime.now().strftime("%Y%m%d")
    backup = path.with_suffix(f".csv.bak_{stamp}")
    shutil.copy2(path, backup)
    tmp = path.with_suffix(".csv.tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(cleaned)
    tmp.replace(path)
    print(f"backup={backup}")
    print(f"rewrote {path}")


if __name__ == "__main__":
    main()
