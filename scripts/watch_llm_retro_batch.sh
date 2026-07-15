#!/usr/bin/env bash
# Poll llm_retro_scores.jsonl and emit checkpoint reports at milestones.
set -euo pipefail
cd "$(dirname "$0")/.."

SCORES="data/research/llm_retro_scores.jsonl"
LOG="logs/llm_retro_scoring.log"
WATCH_LOG="logs/ml/llm_retro_watch.log"
TARGET="${LLM_RETRO_TARGET:-9866}"
MILESTONES=(500 1000 1500 2000 2500 3000 3500 4000 4500 5000 5500 6000 6500 7000 7500 8000 8500 9000 9500)
POLL_SEC="${LLM_RETRO_POLL_SEC:-120}"

mkdir -p logs/ml/llm_retro_checkpoints

log() { echo "[$(date -Iseconds)] $*" | tee -a "$WATCH_LOG"; }

count_lines() {
  if [[ -f "$SCORES" ]]; then
    wc -l < "$SCORES" | tr -d ' '
  else
    echo 0
  fi
}

run_checkpoint() {
  local label="$1"
  local run_ic="${2:-0}"
  log "checkpoint $label (run_ic=$run_ic)"
  if [[ "$run_ic" == "1" ]]; then
    PYTHONPATH=. .venv/bin/python -m scripts.llm_retro_checkpoint_report \
      --label "$label" --run-ic --target "$TARGET" >> "$WATCH_LOG" 2>&1 || true
  else
    PYTHONPATH=. .venv/bin/python -m scripts.llm_retro_checkpoint_report \
      --label "$label" --target "$TARGET" >> "$WATCH_LOG" 2>&1 || true
  fi
}

declare -A DONE=()
log "watch start target=$TARGET poll=${POLL_SEC}s"

while true; do
  n="$(count_lines)"
  for m in "${MILESTONES[@]}"; do
    if [[ "$n" -ge "$m" && -z "${DONE[$m]:-}" ]]; then
      ic=0
      if (( m % 1000 == 0 )); then ic=1; fi
      run_checkpoint "n${m}" "$ic"
      DONE[$m]=1
      if [[ "${RESEARCH_GDRIVE_SYNC_ON_CHECKPOINT:-0}" == "1" ]]; then
        log "gdrive sync after checkpoint n${m}"
        bash scripts/sync_research_to_gdrive.sh >> "$WATCH_LOG" 2>&1 || true
      fi
    fi
  done

  if [[ "$n" -ge "$TARGET" && -z "${DONE[final]:-}" ]]; then
    run_checkpoint "final" 1
    DONE[final]=1
  fi

  if ! pgrep -f "scripts.llm_retro_scoring" >/dev/null 2>&1; then
    final_n="$(count_lines)"
    if [[ -z "${DONE[stopped]:-}" ]]; then
      if [[ "$final_n" -lt "$TARGET" ]]; then
        run_checkpoint "stopped_n${final_n}" 1
      fi
      DONE[stopped]=1
    fi
    log "batch process ended at n=$final_n"
    break
  fi

  sleep "$POLL_SEC"
done

log "watch done"
