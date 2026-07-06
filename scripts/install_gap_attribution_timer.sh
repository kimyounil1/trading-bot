#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_FILE="$PROJECT_DIR/config/ops_reports_config.json"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
mkdir -p "$SYSTEMD_USER_DIR"

CALENDAR="$("$PROJECT_DIR/.venv/bin/python" - <<PY
import json
from pathlib import Path
config = json.loads(Path("$CONFIG_FILE").read_text(encoding="utf-8"))
timezone = str(config.get("timezone", "")).strip()
block = config.get("weekly_gap_attribution", {})
value = str(block.get("on_calendar", "")).strip()
if not value:
    raise SystemExit("Missing on_calendar for weekly_gap_attribution in $CONFIG_FILE")
if timezone and "/" not in value:
    value = f"{value} {timezone}"
print(value)
PY
)"

chmod +x "$PROJECT_DIR/scripts/run_weekly_gap_attribution.sh"

SERVICE="$SYSTEMD_USER_DIR/trading-bot-gap-attribution.service"
TIMER="$SYSTEMD_USER_DIR/trading-bot-gap-attribution.timer"

cat > "$SERVICE" <<SERVICE_EOF
[Unit]
Description=Trading Bot weekly sim-paper gap attribution

[Service]
Type=oneshot
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/scripts/run_weekly_gap_attribution.sh
SERVICE_EOF

cat > "$TIMER" <<TIMER_EOF
[Unit]
Description=Weekly sim-paper gap attribution (guard opportunity-cost evidence)

[Timer]
OnCalendar=$CALENDAR
Persistent=true
AccuracySec=1min

[Install]
WantedBy=timers.target
TIMER_EOF

systemctl --user daemon-reload

echo "Created:"
echo "  $TIMER (OnCalendar=$CALENDAR)"
echo
echo "Enable:"
echo "  systemctl --user enable --now trading-bot-gap-attribution.timer"
