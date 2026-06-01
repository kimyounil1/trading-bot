#!/usr/bin/env bash
# Close one dev pass: pytest → review packet → Codex scoped review → NEXT_TODO.
#
# Usage:
#   RUN_ID=phase20_golden bash scripts/run_pass_complete.sh
#   RUN_ID=phase20_golden bash scripts/run_pass_complete.sh "Cursor feature + AGY golden tests"
#   RUN_ID=phase20_golden TASK_FILE=prompts/my_pass.md bash scripts/run_pass_complete.sh
#
# Requires: .venv, Codex CLI with credits for step 3 (skip with SKIP_CODEX=1).
# FULL_PYTEST=1 for entire suite; SKIP_PYTEST=1 if already green.
# SKIP_CODEX=1 for docs/tests/reports or follow-up fixes — see docs/codex_review_policy.md
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

RUN_ID="${RUN_ID:?Set RUN_ID, e.g. RUN_ID=phase20_golden}"
IMPLEMENTATION_AGENT="${IMPLEMENTATION_AGENT:-cursor}"
OUT_DIR="reports/agent_pipeline/${RUN_ID}"
mkdir -p "$OUT_DIR"

if [[ -n "${1:-}" ]]; then
  printf '%s\n' "$1" >"$OUT_DIR/TASK.md"
elif [[ -n "${TASK_FILE:-}" && -f "$TASK_FILE" ]]; then
  cp "$TASK_FILE" "$OUT_DIR/TASK.md"
elif [[ ! -f "$OUT_DIR/TASK.md" ]]; then
  printf 'Pass %s: Cursor implementation + AGY tests complete. Request Codex review.\n' "$RUN_ID" >"$OUT_DIR/TASK.md"
fi

echo "=== [1/3] pytest ==="
if [[ "${SKIP_PYTEST:-}" == "1" ]]; then
  echo "SKIP_PYTEST=1 — skipped"
elif [[ "${FULL_PYTEST:-}" == "1" ]]; then
  PYTHONPATH=. .venv/bin/python -m pytest -q
else
  # Default: harness-aligned subset (fast, no optional qlib/xgboost stack required).
  PYTHONPATH=. .venv/bin/python -m pytest -q \
    tests/test_report_performance.py \
    tests/test_reappraise_regime.py \
    tests/test_portfolio_backtest_golden.py \
    tests/test_portfolio_backtest_gate.py \
    tests/test_crowding_live_impact_report.py \
    tests/test_daily_audit_summary.py \
    tests/test_daily_audit_summary_schema.py \
    tests/test_retrain_notifications.py \
    tests/test_llm_cache_report_schema.py \
    tests/test_leverage_stress_report.py \
    tests/test_leverage_stress_alerts.py \
    tests/test_crowding_paper_gate.py \
    tests/test_execution_alignment_report.py \
    tests/test_llm_cache_alerts.py \
    tests/test_universe_loader.py \
    tests/test_instrument_meta.py \
    tests/test_margin_leverage_paper_gate.py \
    tests/test_main_data_freshness.py \
    tests/test_guard_impact_report.py \
    tests/test_check_audit_daily_summary.py \
    tests/test_fold_variance_report.py \
    tests/test_promotion_summary.py \
    tests/test_benchmark_gap_report.py \
    tests/test_champion_promotion_governance.py \
    tests/test_equal_weight_benchmark.py \
    tests/test_promotion_beat_benchmark.py \
    tests/test_llm_backtest_impact.py \
    tests/test_paper_ops_summary.py \
    tests/test_buy_guards.py \
    tests/test_cms_reconcile.py \
    tests/test_extended_hours_fill_report.py \
    tests/test_cms_dashboard.py \
    tests/test_broker_adapter.py \
    tests/test_trading_session.py \
    tests/test_execution_resilience.py \
    tests/test_llm_analyst_genai.py \
    tests/test_llm_vllm_fallback.py
fi

echo "=== [2/3] post-workflow / Codex ==="
export IMPLEMENTATION_AGENT
CODEX_EXIT=0
if [[ "${SKIP_CODEX:-}" == "1" ]]; then
  echo "SKIP_CODEX=1 — review packet only (no Codex). Policy: docs/codex_review_policy.md"
  RUN_ID="$RUN_ID" IMPLEMENTATION_AGENT="$IMPLEMENTATION_AGENT" \
    bash "$ROOT/scripts/run_cursor_post_workflow.sh"
else
  .venv/bin/python scripts/agent_orchestrator.py \
    --run-id "$RUN_ID" \
    --task-file "$OUT_DIR/TASK.md" \
    --run-codex-review \
    --scoped-review \
    --ignore-artifacts \
    --max-changed-files "${MAX_CHANGED_FILES:-80}" \
    || CODEX_EXIT=$?
fi

echo ""
echo "=== [3/3] Pass outputs ==="
echo "  Review packet:  $OUT_DIR/review_packet.md"
echo "  Draft TODO:     $OUT_DIR/NEXT_TODO.md"
if [[ -f "$OUT_DIR/NEXT_TODO.codex.md" ]]; then
  echo "  Codex TODO:     $OUT_DIR/NEXT_TODO.codex.md  ← read this next"
  echo ""
  echo "--- NEXT_TODO.codex.md (preview) ---"
  head -40 "$OUT_DIR/NEXT_TODO.codex.md" || true
else
  echo "  Codex TODO:     (missing — Codex did not finish)"
  if [[ -f "$OUT_DIR/codex_review_command.log" ]]; then
    echo ""
    echo "--- codex_review_command.log (tail) ---"
    tail -15 "$OUT_DIR/codex_review_command.log" || true
  fi
fi

echo ""
if [[ "${SKIP_CODEX:-}" == "1" ]]; then
  echo "Light pass complete (no Codex). Use full pass before Phase [x] on high-risk work."
elif [[ "$CODEX_EXIT" -ne 0 ]] || [[ ! -f "$OUT_DIR/NEXT_TODO.codex.md" ]]; then
  echo "Codex review incomplete (exit ${CODEX_EXIT:-?}). Fix credits/CLI, then re-run:"
  echo "  RUN_ID=$RUN_ID SKIP_PYTEST=1 bash scripts/run_pass_complete.sh"
  exit "${CODEX_EXIT:-1}"
else
  echo "Pass complete. Implement items from NEXT_TODO.codex.md in Cursor, then repeat."
fi
PYTHONPATH=. .venv/bin/python scripts/agent_workload_report.py --record 2>/dev/null || true
exit 0
