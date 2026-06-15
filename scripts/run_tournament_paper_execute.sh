#!/usr/bin/env bash
# Paper execute for core + tournament sleeves (same main.py --execute path).
# Use this timer during KST day-market hours; daily paper ops stays dry-run only.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH=.

mkdir -p logs/tournament_execute
LOG_FILE="${TOURNAMENT_EXECUTE_LOG:-logs/tournament_execute/latest.log}"

{
  echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) tournament paper execute start ==="
  bash "$ROOT/scripts/run_bot_once.sh" execute
  echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) tournament paper execute done ==="
} >>"$LOG_FILE" 2>&1

echo "Tournament paper execute complete. Log: $LOG_FILE"
LATEST="$(ls -t "$ROOT/logs/bot_runs"/bot_run_*_execute.log 2>/dev/null | head -1 || true)"
if [[ -n "$LATEST" ]]; then
  echo "Bot run log: $LATEST"
fi
