#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
LOG_DIR="$PROJECT_DIR/logs/news_collector_runs"
mkdir -p "$LOG_DIR"

export PYTHONUNBUFFERED=1
CMD=(
  "$PROJECT_DIR/.venv/bin/python"
  -u
  -m
  src.collect_news
  --no-yfinance-fallback
)

{
  echo "timestamp=$TIMESTAMP"
  echo "project_dir=$PROJECT_DIR"
  echo "command=${CMD[*]}"
  echo "--------------------------------------------------------------------------------"
  "${CMD[@]}"
} > "$LOG_DIR/news_collector_${TIMESTAMP}.log" 2>&1
