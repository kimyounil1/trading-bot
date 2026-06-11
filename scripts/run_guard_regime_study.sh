#!/usr/bin/env bash
# Multi-regime guard study (bull / bear / stress). ~15–20 min with AI scores.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PYTHONPATH=. .venv/bin/python -m src.guard_regime_study "$@"
