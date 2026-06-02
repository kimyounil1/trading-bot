#!/usr/bin/env bash
# Daily paper slice for rank/LLM validation accumulation (scheduler entrypoint).
# Full bootstrap without alpha/guard refresh; refreshes candidate cache for rank gate.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH=.

mkdir -p logs/paper_ops
LOG_FILE="${PAPER_DAILY_LOG:-logs/paper_ops/daily_scheduler.log}"

notify_failure() {
  local msg="$1"
  .venv/bin/python - "$msg" <<'PY' || true
import sys
from src.notifier import notify_error
try:
    notify_error("Daily paper ops scheduler failed", RuntimeError(sys.argv[1]))
except Exception:
    pass
PY
}

set +e
{
  echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) daily paper ops start ==="
  SKIP_ALPHA=1 \
  SKIP_GUARD_REFRESH="${SKIP_GUARD_REFRESH:-1}" \
  SKIP_CROWDING_GATE="${SKIP_CROWDING_GATE:-1}" \
  REFRESH_CANDIDATE_CACHE=1 \
  bash "$ROOT/scripts/run_paper_ops_bootstrap.sh"
  EXIT_CODE=$?
  if [[ "$EXIT_CODE" -ne 0 ]]; then
    echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) daily paper ops FAILED (exit=$EXIT_CODE) ==="
    notify_failure "run_paper_ops_bootstrap exited with code $EXIT_CODE"
    exit "$EXIT_CODE"
  fi
  echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) daily paper ops done ==="
} >>"$LOG_FILE" 2>&1
EXIT_CODE=$?
set -e

if [[ "$EXIT_CODE" -ne 0 ]]; then
  echo "Daily paper ops FAILED (exit=$EXIT_CODE). Log: $LOG_FILE"
  exit "$EXIT_CODE"
fi

echo "Daily paper ops complete. Log: $LOG_FILE"
echo "Summary: logs/paper_ops/latest_summary.json"
echo "Validation: logs/paper_validation/latest_summary.json"
