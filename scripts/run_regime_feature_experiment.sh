#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

PYTHONPATH=. "$PROJECT_DIR/.venv/bin/python" -m src.regime_weakness_report --output-dir logs/ml
PYTHONPATH=. "$PROJECT_DIR/.venv/bin/python" -m src.regime_feature_experiment --output-dir logs/ml
