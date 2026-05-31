#!/usr/bin/env bash
# One-shot paper ops bootstrap: dry-run bot, advisory report, alpha + operational summaries.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH=.

echo "=== [1/4] Bot dry-run (execution_audit + signals) ==="
bash scripts/run_bot_once.sh dry-run

echo "=== [2/4] LLM advisory report ==="
bash scripts/run_llm_advisory_report.sh

echo "=== [3/4] Alpha pipeline ==="
bash scripts/run_alpha_pipeline.sh

echo "=== [4/4] Operational in-loop (cache replay) ==="
bash scripts/run_operational_alpha_validation.sh

echo "Done. See logs/execution_audit.csv and logs/*/latest_summary.json"
