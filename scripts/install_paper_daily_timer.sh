#!/usr/bin/env bash
# Install systemd user timer for daily paper ops (dry-run + validation + rank tracker).
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_FILE="$PROJECT_DIR/config/paper_daily_config.json"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
mkdir -p "$SYSTEMD_USER_DIR"

ON_CALENDAR="$("$PROJECT_DIR/.venv/bin/python" - <<PY
import json
from pathlib import Path
config = json.loads(Path("$CONFIG_FILE").read_text(encoding="utf-8"))
timezone = str(config.get("timezone", "")).strip()
value = str(config.get("on_calendar", "Mon..Fri 21:45:00")).strip()
if timezone and "/" not in value:
    value = f"{value} {timezone}"
print(value)
PY
)"

SERVICE_NAME="$("$PROJECT_DIR/.venv/bin/python" - <<PY
import json
from pathlib import Path
config = json.loads(Path("$CONFIG_FILE").read_text(encoding="utf-8"))
print(config.get("service_name", "trading-bot-daily-paper-ops.service"))
PY
)"

TIMER_NAME="$("$PROJECT_DIR/.venv/bin/python" - <<PY
import json
from pathlib import Path
config = json.loads(Path("$CONFIG_FILE").read_text(encoding="utf-8"))
print(config.get("timer_name", "trading-bot-daily-paper-ops.timer"))
PY
)"

SERVICE_FILE="$SYSTEMD_USER_DIR/$SERVICE_NAME"
TIMER_FILE="$SYSTEMD_USER_DIR/$TIMER_NAME"

chmod +x "$PROJECT_DIR/scripts/run_daily_paper_ops.sh"
chmod +x "$PROJECT_DIR/scripts/run_paper_ops_bootstrap.sh"

cat > "$SERVICE_FILE" <<SERVICE
[Unit]
Description=Trading Bot daily paper ops (dry-run, validation, rank tracker)

[Service]
Type=oneshot
WorkingDirectory=$PROJECT_DIR
Environment=PYTHONPATH=.
ExecStart=$PROJECT_DIR/scripts/run_daily_paper_ops.sh
SERVICE

cat > "$TIMER_FILE" <<TIMER
[Unit]
Description=Daily paper ops for rank/LLM validation accumulation

[Timer]
OnCalendar=$ON_CALENDAR
Persistent=true
AccuracySec=1min

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
echo
echo "Enable:"
echo "  systemctl --user enable --now $TIMER_NAME"
echo
echo "Status:"
echo "  systemctl --user list-timers $TIMER_NAME"
echo "  tail -f logs/paper_ops/daily_scheduler.log"
echo
echo "Manual run:"
echo "  bash scripts/run_daily_paper_ops.sh"
