#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_FILE="$PROJECT_DIR/config/scheduler_config.json"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
mkdir -p "$SYSTEMD_USER_DIR"

SERVICE_FILE="$SYSTEMD_USER_DIR/trading-bot.service"
TIMER_FILE="$SYSTEMD_USER_DIR/trading-bot.timer"

MODE="$("$PROJECT_DIR/.venv/bin/python" - <<PY
import json
from pathlib import Path
config = json.loads(Path("$CONFIG_FILE").read_text())
print(config.get("mode", "dry-run"))
PY
)"

ON_CALENDAR_LINES="$("$PROJECT_DIR/.venv/bin/python" - <<PY
import json
from pathlib import Path
config = json.loads(Path("$CONFIG_FILE").read_text())
times = config.get("on_calendar_times") or [config.get("systemd_on_calendar", "Mon..Fri 10:00:00")]
for item in times:
    print(f"OnCalendar={item}")
PY
)"

cat > "$SERVICE_FILE" <<SERVICE
[Unit]
Description=Trading Bot Runner

[Service]
Type=oneshot
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/scripts/run_bot_once.sh $MODE
SERVICE

cat > "$TIMER_FILE" <<TIMER
[Unit]
Description=Run Trading Bot on configured market schedule

[Timer]
$ON_CALENDAR_LINES
Persistent=true
AccuracySec=1min

[Install]
WantedBy=timers.target
TIMER

systemctl --user daemon-reload

echo "Created:"
echo "  $SERVICE_FILE"
echo "  $TIMER_FILE"
echo
echo "Mode: $MODE"
echo "Schedule:"
echo "$ON_CALENDAR_LINES"
echo
echo "To enable:"
echo "  systemctl --user enable --now trading-bot.timer"
echo
echo "To check:"
echo "  systemctl --user list-timers trading-bot.timer"
echo "  systemctl --user status trading-bot.timer"
