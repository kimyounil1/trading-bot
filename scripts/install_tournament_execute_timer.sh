#!/usr/bin/env bash
# Install systemd user timer for KST day-market paper execute (tournament data).
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_FILE="$PROJECT_DIR/config/tournament_execute_config.json"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
mkdir -p "$SYSTEMD_USER_DIR"

ON_CALENDAR_LINES="$("$PROJECT_DIR/.venv/bin/python" - <<PY
import json
from pathlib import Path
config = json.loads(Path("$CONFIG_FILE").read_text(encoding="utf-8"))
timezone = str(config.get("timezone", "")).strip()
times = config.get("on_calendar_times") or [config.get("on_calendar", "Mon..Fri 10:30:00")]
for item in times:
    value = str(item).strip()
    if timezone and "/" not in value:
        value = f"{value} {timezone}"
    print(f"OnCalendar={value}")
PY
)"

SERVICE_NAME="$("$PROJECT_DIR/.venv/bin/python" - <<PY
import json
from pathlib import Path
config = json.loads(Path("$CONFIG_FILE").read_text(encoding="utf-8"))
print(config.get("service_name", "trading-bot-tournament-execute.service"))
PY
)"

TIMER_NAME="$("$PROJECT_DIR/.venv/bin/python" - <<PY
import json
from pathlib import Path
config = json.loads(Path("$CONFIG_FILE").read_text(encoding="utf-8"))
print(config.get("timer_name", "trading-bot-tournament-execute.timer"))
PY
)"

SERVICE_FILE="$SYSTEMD_USER_DIR/$SERVICE_NAME"
TIMER_FILE="$SYSTEMD_USER_DIR/$TIMER_NAME"

chmod +x "$PROJECT_DIR/scripts/run_tournament_paper_execute.sh"
chmod +x "$PROJECT_DIR/scripts/run_bot_once.sh"

cat > "$SERVICE_FILE" <<SERVICE
[Unit]
Description=Trading Bot paper execute (tournament sleeve data, KST day market)

[Service]
Type=oneshot
WorkingDirectory=$PROJECT_DIR
Environment=PYTHONPATH=.
ExecStart=$PROJECT_DIR/scripts/run_tournament_paper_execute.sh
SERVICE

cat > "$TIMER_FILE" <<TIMER
[Unit]
Description=KST day-market paper execute for tournament sleeve

[Timer]
$ON_CALENDAR_LINES
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
echo "Schedule:"
echo "$ON_CALENDAR_LINES"
echo
echo "Enable:"
echo "  systemctl --user enable --now $TIMER_NAME"
echo
echo "Manual:"
echo "  bash scripts/run_tournament_paper_execute.sh"
