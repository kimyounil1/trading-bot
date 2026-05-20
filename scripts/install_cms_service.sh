#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
mkdir -p "$SYSTEMD_USER_DIR"

SERVICE_FILE="$SYSTEMD_USER_DIR/trading-bot-cms.service"

cat > "$SERVICE_FILE" <<SERVICE
[Unit]
Description=Trading Bot Streamlit CMS
After=network-online.target

[Service]
Type=simple
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/scripts/run_cms.sh
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
SERVICE

systemctl --user daemon-reload

echo "Created: $SERVICE_FILE"
echo
echo "Enable and start:"
echo "  systemctl --user enable --now trading-bot-cms.service"
echo
echo "Check status:"
echo "  systemctl --user status trading-bot-cms.service"
echo
echo "View logs:"
echo "  journalctl --user -u trading-bot-cms.service -f"
