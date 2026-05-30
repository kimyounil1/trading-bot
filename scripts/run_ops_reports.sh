#!/usr/bin/env bash
# Run operational monitoring reports (audit, LLM cache, optional slippage / heavy backtests).
#
# Usage:
#   bash scripts/run_ops_reports.sh              # daily: audit + llm cache
#   bash scripts/run_ops_reports.sh --weekly     # + slippage report
#   bash scripts/run_ops_reports.sh --heavy      # + guard impact + leverage stress
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHON="${ROOT}/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON=python3
fi

RUN_WEEKLY=0
RUN_HEAVY=0
for arg in "$@"; do
  case "$arg" in
    --weekly) RUN_WEEKLY=1 ;;
    --heavy) RUN_HEAVY=1; RUN_WEEKLY=1 ;;
    -h|--help)
      echo "Usage: bash scripts/run_ops_reports.sh [--weekly] [--heavy]"
      exit 0
      ;;
    *)
      echo "Unknown option: $arg" >&2
      exit 2
      ;;
  esac
done

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
LOG_DIR="${ROOT}/logs/ops_reports"
mkdir -p "$LOG_DIR"
LOG_FILE="${LOG_DIR}/ops_${STAMP}.log"

exec > >(tee -a "$LOG_FILE") 2>&1

echo "=== ops reports started ${STAMP} ==="

echo "--- daily audit summary ---"
bash "${ROOT}/scripts/run_daily_audit_summary.sh"

echo "--- llm cache report ---"
bash "${ROOT}/scripts/run_llm_cache_report.sh"

if [[ "$RUN_WEEKLY" -eq 1 ]]; then
  echo "--- weekly slippage report ---"
  bash "${ROOT}/scripts/run_weekly_slippage_report.sh"
  echo "--- execution alignment (audit vs slippage week-over-week) ---"
  bash "${ROOT}/scripts/run_execution_alignment_report.sh"
fi

if [[ "$RUN_HEAVY" -eq 1 ]]; then
  echo "--- guard impact (backtest comparison) ---"
  "$PYTHON" -m src.guard_impact_report
  echo "--- crowding paper go/no-go ---"
  bash "${ROOT}/scripts/run_crowding_paper_gate.sh"
  echo "--- leverage stress ---"
  bash "${ROOT}/scripts/run_leverage_stress_report.sh"
fi

echo "=== ops reports complete; log=${LOG_FILE} ==="
