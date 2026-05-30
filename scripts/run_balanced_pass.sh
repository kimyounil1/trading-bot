#!/usr/bin/env bash
# Balanced multi-account pass: AGY tests → orchestrator (post-workflow + Codex).
#
# Usage:
#   RUN_ID=phase20_portfolio_gate bash scripts/run_balanced_pass.sh
#   RUN_ID=phase20_portfolio_gate AGY_PROMPT=prompts/agy/phase20_portfolio_gate.md bash scripts/run_balanced_pass.sh
#
# Optional: AGY_USE_GEMINI=1 with `gemini` on PATH to implement tests from prompt (legacy).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

RUN_ID="${RUN_ID:?Set RUN_ID}"
AGY_PROMPT="${AGY_PROMPT:-prompts/agy/phase20_portfolio_gate.md}"
OUT_DIR="reports/agent_pipeline/${RUN_ID}"
mkdir -p "$OUT_DIR"

if [[ -f "$AGY_PROMPT" ]]; then
  cp "$AGY_PROMPT" "$OUT_DIR/AGY_TASK.md"
fi

echo "=== Balanced pass: $RUN_ID ==="

if [[ "${AGY_USE_GEMINI:-}" == "1" ]] && command -v gemini >/dev/null 2>&1; then
  echo "=== [AGY] Gemini CLI slice (AGY_USE_GEMINI=1) ==="
  gemini --skip-trust --approval-mode auto_edit --prompt "$(cat "$AGY_PROMPT")"
elif [[ "${SKIP_AGY:-}" == "1" ]]; then
  echo "SKIP_AGY=1 — skipping AGY pytest slice"
else
  AGY_PROMPT="$AGY_PROMPT" bash scripts/run_agy_slice.sh
fi

# AGY slice already ran above; do not pass --balanced-pass (orchestrator would run it again).
exec .venv/bin/python scripts/agent_orchestrator.py \
  --run-id "$RUN_ID" \
  --run-codex-review \
  --scoped-review \
  --ignore-artifacts \
  --max-changed-files "${MAX_CHANGED_FILES:-80}" \
  --task-file "${TASK_FILE:-$OUT_DIR/AGY_TASK.md}"
