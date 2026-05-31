#!/usr/bin/env bash
# Fill data/llm_cache.json for each backtest (ticker, entry_date). Then re-run operational validation.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHON="${ROOT}/.venv/bin/python"
export PYTHONPATH=.

echo "=== [1/2] Warm LLM cache from portfolio_trades ==="
WARM_EXTRA=()
if [[ "${FORCE:-}" == "1" ]]; then
  WARM_EXTRA+=(--force)
fi
if [[ -n "${MAX_ENTRIES:-}" ]]; then
  WARM_EXTRA+=(--max-entries "$MAX_ENTRIES")
fi
"$PYTHON" -m src.warm_llm_cache "${WARM_EXTRA[@]}"

echo "=== [2/2] Operational validation (in-loop cache replay) ==="
"$PYTHON" -m src.run_operational_alpha_validation

echo "=== Done. See data/llm_cache.json and logs/operational_alpha/latest_summary.json ==="
