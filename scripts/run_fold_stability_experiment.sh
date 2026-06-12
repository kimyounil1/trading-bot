#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

PYTHONPATH=. "$PROJECT_DIR/.venv/bin/python" -m src.fold_stability_experiment --output-dir logs/ml
