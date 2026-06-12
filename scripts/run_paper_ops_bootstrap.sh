#!/usr/bin/env bash
# One-shot paper ops bootstrap: dry-run bot, advisory report, alpha + operational summaries,
# crowding gate refresh (report only). Proposal merge requires APPLY_CROWDING_CONFIG=1.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH=.
mkdir -p logs/paper_ops

echo "=== [1/9] Bot dry-run (execution_audit + signals) ==="
bash scripts/run_bot_once.sh dry-run

echo "=== [2/9] LLM advisory report ==="
bash scripts/run_llm_advisory_report.sh

echo "=== [2a/9] LLM block precision (forward returns; feeds live readiness) ==="
bash scripts/run_llm_block_precision.sh || echo "WARN: LLM block precision skipped"

echo "=== [2b/9] Paper buy validation (AI+LLM paths + rank gate tracker) ==="
bash scripts/run_paper_buy_validation.sh || echo "WARN: paper buy validation skipped"

echo "=== [2c/9] Paper validation trend (history rolling summary) ==="
bash scripts/run_paper_validation_trend.sh || echo "WARN: paper validation trend skipped"

echo "=== [3/9] Rank AI gate impact (optional cache refresh: REFRESH_CANDIDATE_CACHE=1) ==="
bash scripts/run_rank_ai_gate_report.sh || echo "WARN: rank AI gate report skipped"

echo "=== [4/9] Crowding live monitoring (execution_audit) ==="
bash scripts/run_crowding_live_impact_report.sh --lookback-days "${CROWDING_LIVE_LOOKBACK_DAYS:-7}" || echo "WARN: crowding live report skipped"

echo "=== [4b/9] Crowding gate reassessment (keep/tune/disable) ==="
bash scripts/run_crowding_gate_reassessment.sh || echo "WARN: crowding gate reassessment skipped"

if [[ "${SKIP_ALPHA:-}" == "1" ]]; then
  echo "=== [5/9] Alpha pipeline — SKIP_ALPHA=1 ==="
  echo "=== [6/9] Operational in-loop — SKIP_ALPHA=1 ==="
else
  echo "=== [5/9] Alpha pipeline ==="
  bash scripts/run_alpha_pipeline.sh

  echo "=== [6/9] Operational in-loop (cache replay) ==="
  bash scripts/run_operational_alpha_validation.sh
fi

echo "=== [7/9] Guard impact + crowding gate (apply proposal on GO only) ==="
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

echo "=== [8/9] Extended-hours limit fill report ==="
.venv/bin/python -m src.extended_hours_fill_report || echo "WARN: extended-hours fill report skipped (Alpaca unavailable)"

echo "=== [8b/9] Data health + live readiness ==="
bash scripts/run_data_health_check.sh || echo "WARN: data health check skipped"
bash scripts/run_live_readiness.sh || echo "WARN: live readiness skipped"

echo "=== [8c/9] Sleeve + tournament reports ==="
bash scripts/run_sleeve_performance_report.sh || echo "WARN: sleeve performance report skipped"
bash scripts/run_tournament_score_report.sh || echo "WARN: tournament score report skipped"

echo "=== [8d/9] stop5_trail10 trial tracker (no-op until --start) ==="
bash scripts/run_stop_trail_trial_report.sh || echo "WARN: stop trail trial report skipped"

echo "=== [9/9] Paper ops summary ==="
.venv/bin/python -m src.paper_ops_summary

echo "Done. See logs/paper_ops/latest_summary.json, logs/rank_ai_gate/latest_summary.json, logs/execution_audit.csv"
