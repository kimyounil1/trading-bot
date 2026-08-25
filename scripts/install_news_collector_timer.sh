#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
mkdir -p "$SYSTEMD_USER_DIR"

SERVICE_FILE="$SYSTEMD_USER_DIR/trading-bot-news-collector.service"
TIMER_FILE="$SYSTEMD_USER_DIR/trading-bot-news-collector.timer"

cat > "$SERVICE_FILE" <<SERVICE
[Unit]
Description=Trading Bot Alpaca News Collector

[Service]
Type=oneshot
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/scripts/run_news_collector.sh
SERVICE

cat > "$TIMER_FILE" <<'TIMER'
[Unit]
Description=Collect Trading Bot News Every 10 Minutes

[Timer]
OnBootSec=1min
OnUnitInactiveSec=10min
Persistent=true
AccuracySec=30s

[Install]
WantedBy=timers.target
TIMER

systemctl --user daemon-reload

echo "Created:"
echo "  $SERVICE_FILE"
echo "  $TIMER_FILE"
echo
echo "Enable:"
echo "  systemctl --user enable --now trading-bot-news-collector.timer"
echo
echo "Check:"
echo "  systemctl --user list-timers trading-bot-news-collector.timer"
echo "  systemctl --user status trading-bot-news-collector.timer"
