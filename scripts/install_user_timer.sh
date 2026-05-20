#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
mkdir -p "$SYSTEMD_USER_DIR"

SERVICE_FILE="$SYSTEMD_USER_DIR/trading-bot.service"
TIMER_FILE="$SYSTEMD_USER_DIR/trading-bot.timer"

cat > "$SERVICE_FILE" <<SERVICE
[Unit]
Description=Trading Bot Paper Runner

[Service]
Type=oneshot
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/scripts/run_bot_once.sh dry-run
SERVICE

cat > "$TIMER_FILE" <<'TIMER'
[Unit]
Description=Run Trading Bot on weekdays after US market open

[Timer]
OnCalendar=Mon..Fri 10:00
Persistent=true

[Install]
WantedBy=timers.target
TIMER

systemctl --user daemon-reload

echo "Created:"
echo "  $SERVICE_FILE"
echo "  $TIMER_FILE"
echo
echo "To enable:"
echo "  systemctl --user enable --now trading-bot.timer"
echo
echo "To check:"
echo "  systemctl --user list-timers trading-bot.timer"
echo "  systemctl --user status trading-bot.timer"
