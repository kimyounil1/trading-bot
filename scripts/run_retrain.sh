#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
LOG_DIR="$PROJECT_DIR/logs/retrain_runs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/retrain_${TIMESTAMP}.log"

set +e
{
  echo "timestamp=$TIMESTAMP"
  echo "project_dir=$PROJECT_DIR"
  echo "--------------------------------------------------------------------------------"
  "$PROJECT_DIR/.venv/bin/python" -m src.train_ai_model
} > "$LOG_FILE" 2>&1
EXIT_CODE=$?
set -e

if [[ "$EXIT_CODE" -ne 0 ]]; then
  echo "Retrain FAILED (exit=$EXIT_CODE): $LOG_FILE"
  echo "Check logs/retrain_history.csv (status=failure) and Telegram for 'AI Retrain Failed'."
  exit "$EXIT_CODE"
fi

echo "Retrain completed: $LOG_FILE"
echo "On champion retained (not promoted), Telegram sends 'Retrain finished; champion retained'."
