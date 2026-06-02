#!/usr/bin/env bash
# Threshold retune + label challenger sweep (portfolio-first) + operator summary.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH=.

echo "=== [1/3] Threshold retune (cached backtest) ==="
if [[ "${SKIP_THRESHOLD_RETUNE:-}" == "1" ]] && [[ -f logs/ml/threshold_retune_report.json ]]; then
  echo "SKIP_THRESHOLD_RETUNE=1 and report exists — skipping retune"
else
  .venv/bin/python -m src.threshold_retune_cli
fi

echo "=== [2/3] Label challenger sweep (use existing reports unless --force) ==="
ONLY="${LABEL_SWEEP_ONLY:-}"
if [[ -n "$ONLY" ]]; then
  .venv/bin/python -m src.label_challenger_sweep --only $ONLY
else
  .venv/bin/python -m src.label_challenger_sweep
fi

echo "=== [3/3] Threshold + promotion summary ==="
.venv/bin/python -m src.threshold_promotion_summary
.venv/bin/python -m src.model_quality_summary

echo "Done. See logs/ml/threshold_retune_report.json, logs/ml/label_challenger_sweep_report.json"
