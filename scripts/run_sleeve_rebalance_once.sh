#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
LOG_DIR="$PROJECT_DIR/logs/bot_runs"
mkdir -p "$LOG_DIR"

export PYTHONUNBUFFERED=1
CMD=("$PROJECT_DIR/.venv/bin/python" -u -m src.main --sleeve-rebalance-only)

{
  echo "timestamp=$TIMESTAMP"
  echo "project_dir=$PROJECT_DIR"
  echo "mode=sleeve_rebalance"
  echo "command=${CMD[*]}"
  echo "--------------------------------------------------------------------------------"
  "${CMD[@]}"
} > "$LOG_DIR/bot_run_${TIMESTAMP}_sleeve_rebalance.log" 2>&1

echo "Sleeve rebalance complete. Log: logs/bot_runs/bot_run_${TIMESTAMP}_sleeve_rebalance.log"
