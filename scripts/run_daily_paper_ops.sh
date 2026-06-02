#!/usr/bin/env bash
# Daily paper slice for rank/LLM validation accumulation (scheduler entrypoint).
# Full bootstrap without alpha/guard refresh; refreshes candidate cache for rank gate.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH=.

mkdir -p logs/paper_ops
LOG_FILE="${PAPER_DAILY_LOG:-logs/paper_ops/daily_scheduler.log}"

{
  echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) daily paper ops start ==="
  SKIP_ALPHA=1 \
  SKIP_GUARD_REFRESH="${SKIP_GUARD_REFRESH:-1}" \
  SKIP_CROWDING_GATE="${SKIP_CROWDING_GATE:-1}" \
  REFRESH_CANDIDATE_CACHE=1 \
  bash "$ROOT/scripts/run_paper_ops_bootstrap.sh"
  echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) daily paper ops done ==="
} >>"$LOG_FILE" 2>&1

echo "Daily paper ops complete. Log: $LOG_FILE"
echo "Summary: logs/paper_ops/latest_summary.json"
echo "Validation: logs/paper_validation/latest_summary.json"
