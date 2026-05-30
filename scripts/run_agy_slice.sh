#!/usr/bin/env bash
# Run the [AGY] test slice for a pass (pytest only; no main.py edits).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

AGY_PROMPT="${AGY_PROMPT:-${1:-}}"
TEST_PATHS="${AGY_TEST_PATHS:-tests/test_portfolio_backtest_gate.py}"

if [[ -n "$AGY_PROMPT" && -f "$AGY_PROMPT" ]]; then
  echo "AGY prompt: $AGY_PROMPT"
fi

echo "=== AGY slice: pytest ==="
PYTHONPATH=. .venv/bin/python -m pytest -q $TEST_PATHS
echo "AGY slice pytest: OK"
