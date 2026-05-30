#!/usr/bin/env bash
# Close one dev pass: pytest → review packet → Codex scoped review → NEXT_TODO.
#
# Usage:
#   RUN_ID=phase20_golden bash scripts/run_pass_complete.sh
#   RUN_ID=phase20_golden bash scripts/run_pass_complete.sh "Cursor feature + AGY golden tests"
#   RUN_ID=phase20_golden TASK_FILE=prompts/my_pass.md bash scripts/run_pass_complete.sh
#
# Requires: .venv, Codex CLI with credits for step 3.
# FULL_PYTEST=1 for entire suite; SKIP_PYTEST=1 if already green.
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
    tests/test_portfolio_backtest_golden.py
fi

echo "=== [2/3] Codex review via orchestrator (post-workflow + scoped review) ==="
export IMPLEMENTATION_AGENT
CODEX_EXIT=0
.venv/bin/python scripts/agent_orchestrator.py \
  --run-id "$RUN_ID" \
  --task-file "$OUT_DIR/TASK.md" \
  --run-codex-review \
  --scoped-review \
  --ignore-artifacts \
  || CODEX_EXIT=$?

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
if [[ "$CODEX_EXIT" -ne 0 ]] || [[ ! -f "$OUT_DIR/NEXT_TODO.codex.md" ]]; then
  echo "Codex review incomplete (exit ${CODEX_EXIT:-?}). Fix credits/CLI, then re-run:"
  echo "  RUN_ID=$RUN_ID SKIP_PYTEST=1 bash scripts/run_pass_complete.sh"
  exit "${CODEX_EXIT:-1}"
fi

echo "Pass complete. Implement items from NEXT_TODO.codex.md in Cursor, then repeat."
PYTHONPATH=. .venv/bin/python scripts/agent_workload_report.py --record 2>/dev/null || true
exit 0
