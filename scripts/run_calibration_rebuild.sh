#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

PYTHONPATH=. "$PROJECT_DIR/.venv/bin/python" -m src.ml_quality_report \
  --rebuild-calibration-rows \
  --output-dir logs/ml

PYTHONPATH=. "$PROJECT_DIR/.venv/bin/python" -m src.calibration_experiment \
  --rows logs/ml/model_calibration_rows.csv \
  --output-dir logs/ml
