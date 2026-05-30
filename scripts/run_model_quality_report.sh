#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

METRICS_PATH="${1:-logs/ml/fold_metrics.csv}"
if [[ ! -f "$METRICS_PATH" && -f logs/ml/ai_model_metrics.csv ]]; then
  METRICS_PATH="logs/ml/ai_model_metrics.csv"
fi

PYTHONPATH=. "$PROJECT_DIR/.venv/bin/python" -m src.ml_quality_report \
  --metrics "$METRICS_PATH" \
  --output-dir logs/ml
