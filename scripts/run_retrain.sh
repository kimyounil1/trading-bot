#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
LOG_DIR="$PROJECT_DIR/logs/retrain_runs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/retrain_${TIMESTAMP}.log"

{
  echo "timestamp=$TIMESTAMP"
  echo "project_dir=$PROJECT_DIR"
  echo "--------------------------------------------------------------------------------"
  "$PROJECT_DIR/.venv/bin/python" -m src.train_ai_model
} > "$LOG_FILE" 2>&1

echo "Retrain completed: $LOG_FILE"
