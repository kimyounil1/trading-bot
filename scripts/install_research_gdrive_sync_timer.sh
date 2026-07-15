#!/usr/bin/env bash
# Install systemd user timer for incremental research -> Google Drive sync.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_FILE="$PROJECT_DIR/config/research_gdrive_sync_config.json"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
mkdir -p "$SYSTEMD_USER_DIR"

ON_CALENDAR="$("$PROJECT_DIR/.venv/bin/python" - <<PY
import json
from pathlib import Path
config = json.loads(Path("$CONFIG_FILE").read_text(encoding="utf-8"))
timezone = str(config.get("timezone", "")).strip()
value = str(config.get("on_calendar", "0 */4:00:00")).strip()
if timezone and "/" not in value:
    value = f"{value} {timezone}"
print(value)
PY
)"

SERVICE_NAME="$("$PROJECT_DIR/.venv/bin/python" - <<PY
import json
from pathlib import Path
config = json.loads(Path("$CONFIG_FILE").read_text(encoding="utf-8"))
print(config.get("service_name", "trading-bot-research-gdrive-sync.service"))
PY
)"

TIMER_NAME="$("$PROJECT_DIR/.venv/bin/python" - <<PY
import json
from pathlib import Path
config = json.loads(Path("$CONFIG_FILE").read_text(encoding="utf-8"))
print(config.get("timer_name", "trading-bot-research-gdrive-sync.timer"))
PY
)"

SERVICE_FILE="$SYSTEMD_USER_DIR/$SERVICE_NAME"
TIMER_FILE="$SYSTEMD_USER_DIR/$TIMER_NAME"

chmod +x "$PROJECT_DIR/scripts/sync_research_to_gdrive.sh"

cat > "$SERVICE_FILE" <<SERVICE
[Unit]
Description=Trading bot research artifacts -> Google Drive (incremental rclone copy)

[Service]
Type=oneshot
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/scripts/sync_research_to_gdrive.sh
SERVICE

cat > "$TIMER_FILE" <<TIMER
[Unit]
Description=Periodic research data sync to Google Drive

[Timer]
OnCalendar=$ON_CALENDAR
Persistent=true
AccuracySec=5min

[Install]
WantedBy=timers.target
TIMER

if command -v systemctl >/dev/null 2>&1; then
  systemctl --user daemon-reload
fi

echo "Created:"
echo "  $SERVICE_FILE"
echo "  $TIMER_FILE"
echo
echo "Schedule: OnCalendar=$ON_CALENDAR"
echo "Config:   $CONFIG_FILE"
echo "Log:      logs/ml/gdrive_sync.log"
echo
echo "Enable (incremental upload every 4h; only new/changed files):"
echo "  systemctl --user enable --now $TIMER_NAME"
echo
echo "Run once now:"
echo "  bash scripts/sync_research_to_gdrive.sh"
echo
echo "Check:"
echo "  systemctl --user list-timers $TIMER_NAME"
echo "  tail -f logs/ml/gdrive_sync.log"
