#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_FILE="$PROJECT_DIR/config/slippage_report_config.json"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
mkdir -p "$SYSTEMD_USER_DIR"

SERVICE_FILE="$SYSTEMD_USER_DIR/trading-bot-slippage-report.service"
TIMER_FILE="$SYSTEMD_USER_DIR/trading-bot-slippage-report.timer"

ON_CALENDAR_LINES="$("$PROJECT_DIR/.venv/bin/python" - <<PY
import json
from pathlib import Path
config = json.loads(Path("$CONFIG_FILE").read_text())
timezone = str(config.get("timezone", "")).strip()
times = config.get("on_calendar_times", ["Sun 18:00:00"])
for item in times:
    value = str(item).strip()
    if timezone and "/" not in value:
        value = f"{value} {timezone}"
    print(f"OnCalendar={value}")
PY
)"

chmod +x "$PROJECT_DIR/scripts/run_weekly_slippage_report.sh"

cat > "$SERVICE_FILE" <<SERVICE
[Unit]
Description=Trading Bot weekly paper vs signal slippage report

[Service]
Type=oneshot
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/scripts/run_weekly_slippage_report.sh
SERVICE

cat > "$TIMER_FILE" <<TIMER
[Unit]
Description=Weekly slippage report (paper fills vs signal price)

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
echo "Schedule:"
echo "$ON_CALENDAR_LINES"
echo
echo "To enable:"
echo "  systemctl --user enable --now trading-bot-slippage-report.timer"
echo
echo "Manual run:"
echo "  bash scripts/run_weekly_slippage_report.sh"
