#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
LOG_DIR="$PROJECT_DIR/logs/candidate_cache_runs"
mkdir -p "$LOG_DIR"

{
  echo "timestamp=$TIMESTAMP"
  echo "project_dir=$PROJECT_DIR"
  echo "command=$PROJECT_DIR/.venv/bin/python -m src.generate_candidate_cache"
  echo "--------------------------------------------------------------------------------"
  "$PROJECT_DIR/.venv/bin/python" -m src.generate_candidate_cache
} > "$LOG_DIR/candidate_cache_${TIMESTAMP}.log" 2>&1
