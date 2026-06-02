#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

PYTHONPATH=. "$PROJECT_DIR/.venv/bin/python" -m src.calibration_experiment \
  --rows logs/ml/model_calibration_rows.csv \
  --output-dir logs/ml

PYTHONPATH=. "$PROJECT_DIR/.venv/bin/python" -m src.label_horizon_report \
  --output-dir logs/ml

PYTHONPATH=. "$PROJECT_DIR/.venv/bin/python" -m src.model_quality_summary \
  --ml-dir logs/ml \
  --benchmark-gap logs/benchmark_gap/latest_summary.json \
  --output-dir logs/model_quality
