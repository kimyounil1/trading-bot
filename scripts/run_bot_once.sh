#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
LOG_DIR="$PROJECT_DIR/logs/bot_runs"
mkdir -p "$LOG_DIR"

MODE="${1:-dry-run}"

if [[ "$MODE" == "execute" ]]; then
  CMD=("$PROJECT_DIR/.venv/bin/python" -m src.main --execute)
else
  CMD=("$PROJECT_DIR/.venv/bin/python" -m src.main)
fi

{
  echo "timestamp=$TIMESTAMP"
  echo "project_dir=$PROJECT_DIR"
  echo "mode=$MODE"
  echo "command=${CMD[*]}"
  echo "--------------------------------------------------------------------------------"
  "${CMD[@]}"
} > "$LOG_DIR/bot_run_${TIMESTAMP}_${MODE}.log" 2>&1
