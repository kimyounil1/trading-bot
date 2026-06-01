#!/usr/bin/env bash
# One-shot paper ops bootstrap: dry-run bot, advisory report, alpha + operational summaries,
# crowding gate refresh (report only). Proposal merge requires APPLY_CROWDING_CONFIG=1.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH=.
mkdir -p logs/paper_ops

echo "=== [1/6] Bot dry-run (execution_audit + signals) ==="
bash scripts/run_bot_once.sh dry-run

echo "=== [2/6] LLM advisory report ==="
bash scripts/run_llm_advisory_report.sh

if [[ "${SKIP_ALPHA:-}" == "1" ]]; then
  echo "=== [3/6] Alpha pipeline — SKIP_ALPHA=1 ==="
  echo "=== [4/6] Operational in-loop — SKIP_ALPHA=1 ==="
else
  echo "=== [3/6] Alpha pipeline ==="
  bash scripts/run_alpha_pipeline.sh

  echo "=== [4/6] Operational in-loop (cache replay) ==="
  bash scripts/run_operational_alpha_validation.sh
fi

echo "=== [5/6] Guard impact + crowding gate (apply proposal on GO only) ==="
GUARD_IMPACT="logs/guard_impact/latest_summary.json"
SKIP_CROWDING_GATE=0
GUARD_REFRESHED=0

if [[ -f models/ai_score_model.joblib ]] && [[ "${SKIP_GUARD_REFRESH:-}" != "1" ]]; then
  bash scripts/run_guard_impact_report.sh
  GUARD_REFRESHED=1
elif [[ -f "$GUARD_IMPACT" ]]; then
  echo "Using existing ${GUARD_IMPACT} (skip guard_impact refresh; gate report only)"
elif [[ "${SKIP_ALPHA:-}" == "1" ]]; then
  echo "WARN: ${GUARD_IMPACT} missing and model unavailable — skipping crowding gate."
  echo "      Restore baseline: git checkout -- ${GUARD_IMPACT}"
  SKIP_CROWDING_GATE=1
else
  echo "ERROR: ${GUARD_IMPACT} missing. Train model or restore baseline." >&2
  exit 1
fi

if [[ "$SKIP_CROWDING_GATE" != "1" ]]; then
  if [[ "${APPLY_CROWDING_CONFIG:-}" == "1" ]]; then
    bash scripts/run_crowding_paper_gate.sh --apply-config
  else
    bash scripts/run_crowding_paper_gate.sh
  fi
fi

echo "=== [6/7] Extended-hours limit fill report ==="
.venv/bin/python -m src.extended_hours_fill_report || echo "WARN: extended-hours fill report skipped (Alpaca unavailable)"

echo "=== [7/7] Paper ops summary ==="
.venv/bin/python -m src.paper_ops_summary

echo "Done. See logs/paper_ops/latest_summary.json, logs/execution_audit.csv, logs/llm_advisory/latest_summary.json"
