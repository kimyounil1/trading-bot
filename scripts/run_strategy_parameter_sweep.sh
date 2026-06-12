#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

SWEEP="${1:-all}"
PYTHONPATH=. "$PROJECT_DIR/.venv/bin/python" -m src.strategy_parameter_sweep \
  --sweep "$SWEEP" \
  --period 2y \
  --output-dir logs/strategy_parameter_sweep
