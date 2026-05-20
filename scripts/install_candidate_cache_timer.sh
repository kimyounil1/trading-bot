#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
mkdir -p "$SYSTEMD_USER_DIR"

SERVICE_FILE="$SYSTEMD_USER_DIR/trading-bot-candidate-cache.service"
TIMER_FILE="$SYSTEMD_USER_DIR/trading-bot-candidate-cache.timer"

cat > "$SERVICE_FILE" <<SERVICE
[Unit]
Description=Trading Bot Candidate Cache Generator

[Service]
Type=oneshot
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/scripts/run_candidate_cache.sh
SERVICE

cat > "$TIMER_FILE" <<'TIMER'
[Unit]
Description=Generate Trading Bot Candidate Cache Every 10 Minutes

[Timer]
OnBootSec=2min
OnUnitActiveSec=10min
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
echo "Enable:"
echo "  systemctl --user enable --now trading-bot-candidate-cache.timer"
echo
echo "Check:"
echo "  systemctl --user list-timers trading-bot-candidate-cache.timer"
echo "  systemctl --user status trading-bot-candidate-cache.timer"
