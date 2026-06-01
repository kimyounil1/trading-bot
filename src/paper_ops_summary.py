"""Aggregate paper ops bootstrap artifacts into one summary JSON."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_OUTPUT_DIR = Path("logs/paper_ops")
DEFAULT_AUDIT_PATH = Path("logs/execution_audit.csv")
DEFAULT_LLM_CACHE_PATH = Path("data/llm_cache.json")
DEFAULT_LLM_ADVISORY_PATH = Path("logs/llm_advisory/latest_summary.json")
DEFAULT_CROWDING_GATE_PATH = Path("logs/crowding_paper/go_no_go_checklist.json")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def build_paper_ops_summary(
    *,
    audit_path: Path = DEFAULT_AUDIT_PATH,
    llm_cache_path: Path = DEFAULT_LLM_CACHE_PATH,
    llm_advisory_path: Path = DEFAULT_LLM_ADVISORY_PATH,
    crowding_gate_path: Path = DEFAULT_CROWDING_GATE_PATH,
) -> dict[str, Any]:
    llm_advisory = _load_json_if_exists(llm_advisory_path) or {}
    crowding_gate = _load_json_if_exists(crowding_gate_path) or {}

    llm_cache_keys = 0
    if llm_cache_path.is_file():
        cache_payload = json.loads(llm_cache_path.read_text(encoding="utf-8"))
        if isinstance(cache_payload, dict):
            llm_cache_keys = len(cache_payload)

    audit_rows = 0
    if audit_path.is_file():
        audit_rows = max(0, sum(1 for _ in audit_path.open(encoding="utf-8")) - 1)

    config_apply = crowding_gate.get("config_apply") or {}
    return {
        "generated_at": _utc_now_iso(),
        "execution_audit_path": str(audit_path),
        "execution_audit_rows": audit_rows,
        "llm_cache_path": str(llm_cache_path),
        "llm_cache_keys": llm_cache_keys,
        "llm_advisory_path": str(llm_advisory_path),
        "llm_advisory": {
            "rows": llm_advisory.get("rows", 0),
            "advisory_would_reject": llm_advisory.get("advisory_would_reject", 0),
            "buy_submitted": llm_advisory.get("buy_submitted", 0),
            "buy_submitted_despite_llm_reject": llm_advisory.get(
                "buy_submitted_despite_llm_reject", 0
            ),
        },
        "crowding_gate_path": str(crowding_gate_path),
        "crowding_decision": crowding_gate.get("decision"),
        "crowding_config_applied": bool(config_apply.get("applied", False)),
        "notes": [
            "Run via: bash scripts/run_paper_ops_bootstrap.sh",
            "Crowding proposal applies to strategy_config only when gate decision is GO_PAPER.",
        ],
    }


def write_paper_ops_summary(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    **kwargs: Any,
) -> Path:
    report = build_paper_ops_summary(**kwargs)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "latest_summary.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Write paper ops bootstrap summary JSON")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    path = write_paper_ops_summary(Path(args.output_dir))
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
