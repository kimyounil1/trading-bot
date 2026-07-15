#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_FILE="$PROJECT_DIR/config/paper_backtest_parity_config.json"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
mkdir -p "$SYSTEMD_USER_DIR"

ON_CALENDAR="$($PROJECT_DIR/.venv/bin/python - <<PY
import json
from pathlib import Path
config = json.loads(Path("$CONFIG_FILE").read_text(encoding="utf-8"))
value = str(config.get("on_calendar", "")).strip()
timezone = str(config.get("timezone", "")).strip()
if not value:
    raise SystemExit("Missing on_calendar in parity config")
if timezone and "/" not in value:
    value = f"{value} {timezone}"
print(value)
PY
)"

SERVICE_FILE="$SYSTEMD_USER_DIR/trading-bot-paper-backtest-parity.service"
TIMER_FILE="$SYSTEMD_USER_DIR/trading-bot-paper-backtest-parity.timer"
chmod +x "$PROJECT_DIR/scripts/run_daily_paper_backtest_parity.sh"

cat > "$SERVICE_FILE" <<SERVICE
[Unit]
Description=Trading Bot daily paper vs backtest entry parity
After=network-online.target

[Service]
Type=oneshot
WorkingDirectory=$PROJECT_DIR
Environment=PYTHONPATH=.
ExecStart=$PROJECT_DIR/scripts/run_daily_paper_backtest_parity.sh
TimeoutStartSec=30min
SERVICE

cat > "$TIMER_FILE" <<TIMER
[Unit]
Description=Daily paper vs backtest entry parity and anomaly alert

[Timer]
OnCalendar=$ON_CALENDAR
Persistent=true
AccuracySec=1min

[Install]
WantedBy=timers.target
TIMER

systemctl --user daemon-reload

echo "Created:"
echo "  $SERVICE_FILE"
echo "  $TIMER_FILE"
echo "Schedule: $ON_CALENDAR"
echo "Enable: systemctl --user enable --now trading-bot-paper-backtest-parity.timer"
