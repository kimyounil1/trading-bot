#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH=.

if [[ "${REFRESH_CANDIDATE_CACHE:-}" == "1" ]]; then
  echo "Refreshing candidate cache for rank gate snapshot..."
  .venv/bin/python -m src.generate_candidate_cache
fi

.venv/bin/python -m src.rank_ai_gate_impact_report "$@"
.venv/bin/python -m scripts.rank_gate_counterfactual || echo "WARN: rank gate counterfactual skipped"
