#!/usr/bin/env bash
# Baseline vs in-loop LLM + news filters (operational path in portfolio_backtester).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHON="${ROOT}/.venv/bin/python"
export PYTHONPATH=.

EXTRA=()
if [[ "${LIVE_LLM:-}" == "1" ]]; then
  EXTRA+=(--live-llm)
fi

echo "=== operational alpha validation (in-loop filters) ==="
"$PYTHON" -m src.run_operational_alpha_validation "${EXTRA[@]}"
