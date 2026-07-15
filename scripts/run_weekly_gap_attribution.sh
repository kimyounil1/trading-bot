#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
LOG_DIR="$PROJECT_DIR/logs/sim_paper_gap/runs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/attribution_${TIMESTAMP}.log"

{
  echo "timestamp=$TIMESTAMP"
  echo "--------------------------------------------------------------------------------"
  PYTHONPATH=. "$PROJECT_DIR/.venv/bin/python" -m scripts.sim_paper_gap_attribution
} >"$LOG_FILE" 2>&1

echo "Weekly sim-paper gap attribution completed: $LOG_FILE"
