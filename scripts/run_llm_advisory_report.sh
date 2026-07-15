#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH=.
.venv/bin/python -m src.llm_advisory_impact_report "$@"
.venv/bin/python -m scripts.llm_gate_counterfactual || echo "WARN: LLM gate counterfactual skipped"
