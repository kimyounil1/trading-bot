#!/usr/bin/env bash
# Sync curated research artifacts to Google Drive via rclone.
#
# Incremental: rclone copy uploads only missing files or files whose
# size/mtime changed on disk (default). Re-running is safe and cheap.
#
# One-time setup: docs/research_data_gdrive.md
# Periodic sync: bash scripts/install_research_gdrive_sync_timer.sh
#
# Usage:
#   bash scripts/sync_research_to_gdrive.sh           # incremental copy
#   bash scripts/sync_research_to_gdrive.sh --dry-run
#   RESEARCH_GDRIVE_REMOTE="gdrive:my-folder" bash scripts/sync_research_to_gdrive.sh
set -euo pipefail
cd "$(dirname "$0")/.."

MANIFEST="config/research_gdrive_sync.json"
LOG_FILE="logs/ml/gdrive_sync.log"
DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
fi

mkdir -p logs/ml

if ! command -v rclone >/dev/null 2>&1; then
  echo "rclone not found. Install: sudo apt install rclone" >&2
  echo "Then follow: docs/research_data_gdrive.md" >&2
  exit 1
fi

if [[ ! -f "$MANIFEST" ]]; then
  echo "Missing $MANIFEST" >&2
  exit 1
fi

REMOTE="${RESEARCH_GDRIVE_REMOTE:-$(.venv/bin/python - <<'PY'
import json
from pathlib import Path
print(json.loads(Path("config/research_gdrive_sync.json").read_text())["remote"])
PY
)}"

RCLONE_FLAGS=(--transfers 4 --checkers 8 --tpslimit 8 --drive-acknowledge-abuse --local-no-check-updated)
if [[ "$DRY_RUN" == "1" ]]; then
  RCLONE_FLAGS+=(--dry-run)
fi
if [[ -t 1 && "$DRY_RUN" != "1" ]]; then
  RCLONE_FLAGS+=(--progress)
fi

log() {
  echo "[$(date -Iseconds)] $*"
  echo "[$(date -Iseconds)] $*" >> "$LOG_FILE"
}

log "start remote=$REMOTE dry_run=$DRY_RUN"

STAGE_RESEARCH=""
STAGE_DATA=""
if pgrep -f "scripts.llm_retro_scoring" >/dev/null 2>&1 && [[ -d data/research ]]; then
  STAGE_RESEARCH="$(mktemp -d)"
  cp -a data/research/. "$STAGE_RESEARCH/"
  log "snapshot data/research (retro batch active)"
fi

META_DIR=""
cleanup() {
  if [[ -n "$STAGE_DATA" && -d "$STAGE_DATA" ]]; then
    rm -rf "$STAGE_DATA"
  fi
  if [[ -n "$STAGE_RESEARCH" && -d "$STAGE_RESEARCH" ]]; then
    rm -rf "$STAGE_RESEARCH"
  fi
  if [[ -n "$META_DIR" && -d "$META_DIR" ]]; then
    rm -rf "$META_DIR"
  fi
}
trap cleanup EXIT

DIRS=()
while IFS= read -r line; do
  DIRS+=("$line")
done < <(.venv/bin/python - <<'PY'
import json
from pathlib import Path
cfg = json.loads(Path("config/research_gdrive_sync.json").read_text())
for d in cfg["directories"]:
    print(d)
PY
)

for rel in "${DIRS[@]}"; do
  if [[ ! -e "$rel" ]]; then
    echo "skip (missing): $rel"
    continue
  fi
  src="$rel"
  if [[ "$rel" == "data" && -n "$STAGE_RESEARCH" ]]; then
    STAGE_DATA="$(mktemp -d)"
    cp -a data/. "$STAGE_DATA/"
    cp -a "$STAGE_RESEARCH/." "$STAGE_DATA/research/"
    src="$STAGE_DATA"
    log "snapshot data/ (research overlay while retro batch active)"
  fi
  echo "==> copy $rel"
  log "copy $rel"
  rclone copy "$src" "$REMOTE/$rel" "${RCLONE_FLAGS[@]}"
done

SYNC_FULL_ML="$(.venv/bin/python - <<'PY'
import json
from pathlib import Path
cfg = json.loads(Path("config/research_gdrive_sync.json").read_text())
print("1" if cfg.get("sync_full_logs_ml") else "0")
PY
)"

# logs/ml: full tree or filtered subset
if [[ -d logs/ml ]]; then
  if [[ "$SYNC_FULL_ML" == "1" ]]; then
    echo "==> copy logs/ml (full)"
    log "copy logs/ml (full)"
    rclone copy logs/ml "$REMOTE/logs/ml" "${RCLONE_FLAGS[@]}" \
      --exclude "/model_calibration_rows.csv"
  else
  echo "==> copy logs/ml (filtered)"
  mapfile -t ML_INCLUDES < <(.venv/bin/python - <<'PY'
import json
from pathlib import Path
cfg = json.loads(Path("config/research_gdrive_sync.json").read_text())["logs_ml"]
if cfg.get("include_root_json_csv"):
    print("/*.json")
    print("/*.csv")
for p in cfg.get("include_patterns", []):
    print("/" + p)
PY
)
  mapfile -t ML_EXCLUDES < <(.venv/bin/python - <<'PY'
import json
from pathlib import Path
cfg = json.loads(Path("config/research_gdrive_sync.json").read_text())["logs_ml"]
for p in cfg.get("exclude_patterns", []):
    print("/" + p)
PY
)
  ML_ARGS=()
  for inc in "${ML_INCLUDES[@]}"; do ML_ARGS+=(--include "$inc"); done
  for exc in "${ML_EXCLUDES[@]}"; do ML_ARGS+=(--exclude "$exc"); done
  rclone copy logs/ml "$REMOTE/logs/ml" "${RCLONE_FLAGS[@]}" "${ML_ARGS[@]}"
  fi
fi

# reports: skip transient agent_pipeline runs
if [[ -d reports ]]; then
  echo "==> copy reports (exclude agent_pipeline)"
  rclone copy reports "$REMOTE/reports" "${RCLONE_FLAGS[@]}" \
    --exclude "/agent_pipeline/**"
fi

# Private secrets (.env) — Drive folder is user-private; do not share link publicly.
PRIVATE_SUBDIR="$(.venv/bin/python - <<'PY'
import json
from pathlib import Path
cfg = json.loads(Path("config/research_gdrive_sync.json").read_text())
print(cfg.get("private_remote_subdir", "_private"))
PY
)"
while IFS= read -r priv; do
  if [[ -f "$priv" ]]; then
    echo "==> copy $priv -> $PRIVATE_SUBDIR/"
    log "copy private $priv"
    rclone copy "$priv" "$REMOTE/$PRIVATE_SUBDIR/" "${RCLONE_FLAGS[@]}"
  fi
done < <(.venv/bin/python - <<'PY'
import json
from pathlib import Path
cfg = json.loads(Path("config/research_gdrive_sync.json").read_text())
for f in cfg.get("private_files", []):
    print(f)
PY
)

# Upload sync metadata for traceability
META_DIR="$(mktemp -d)"
COMMIT="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
STAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
SCORES_LINES=0
if [[ -f data/research/llm_retro_scores.jsonl ]]; then
  SCORES_LINES="$(wc -l < data/research/llm_retro_scores.jsonl | tr -d ' ')"
fi
cat > "$META_DIR/_sync_manifest.json" <<EOF
{
  "synced_at": "$STAMP",
  "git_commit": "$COMMIT",
  "remote": "$REMOTE",
  "llm_retro_scores_lines": $SCORES_LINES,
  "manifest": "config/research_gdrive_sync.json"
}
EOF
rclone copy "$META_DIR" "$REMOTE/" "${RCLONE_FLAGS[@]}"

echo "Done -> $REMOTE (_sync_manifest.json updated)"
log "done remote=$REMOTE scores_lines=$SCORES_LINES"
