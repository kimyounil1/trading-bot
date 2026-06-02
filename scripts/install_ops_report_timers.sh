#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_FILE="$PROJECT_DIR/config/ops_reports_config.json"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
mkdir -p "$SYSTEMD_USER_DIR"

read_calendar() {
  local key="$1"
  "$PROJECT_DIR/.venv/bin/python" - <<PY
import json
from pathlib import Path
config = json.loads(Path("$CONFIG_FILE").read_text(encoding="utf-8"))
timezone = str(config.get("timezone", "")).strip()
block = config.get("$key", {})
value = str(block.get("on_calendar", "")).strip()
if not value:
    raise SystemExit(f"Missing on_calendar for $key in $CONFIG_FILE")
if timezone and "/" not in value:
    value = f"{value} {timezone}"
print(value)
PY
}

AUDIT_CALENDAR="$(read_calendar daily_audit)"
LLM_CALENDAR="$(read_calendar weekly_llm_cache)"

chmod +x "$PROJECT_DIR/scripts/run_ops_reports.sh"
chmod +x "$PROJECT_DIR/scripts/run_daily_audit_summary.sh"
chmod +x "$PROJECT_DIR/scripts/run_llm_cache_report.sh"

AUDIT_SERVICE="$SYSTEMD_USER_DIR/trading-bot-daily-audit.service"
AUDIT_TIMER="$SYSTEMD_USER_DIR/trading-bot-daily-audit.timer"
LLM_SERVICE="$SYSTEMD_USER_DIR/trading-bot-llm-cache-report.service"
LLM_TIMER="$SYSTEMD_USER_DIR/trading-bot-llm-cache-report.timer"

cat > "$AUDIT_SERVICE" <<SERVICE
[Unit]
Description=Trading Bot daily execution audit summary

[Service]
Type=oneshot
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/scripts/run_daily_audit_summary.sh
SERVICE

cat > "$AUDIT_TIMER" <<TIMER
[Unit]
Description=Daily execution audit summary

[Timer]
OnCalendar=$AUDIT_CALENDAR
Persistent=true
AccuracySec=1min

[Install]
WantedBy=timers.target
TIMER

cat > "$LLM_SERVICE" <<SERVICE
[Unit]
Description=Trading Bot LLM cache monitoring report

[Service]
Type=oneshot
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/scripts/run_llm_cache_report.sh
SERVICE

cat > "$LLM_TIMER" <<TIMER
[Unit]
Description=Weekly LLM cache hit-rate report

[Timer]
OnCalendar=$LLM_CALENDAR
Persistent=true
AccuracySec=1min

[Install]
WantedBy=timers.target
TIMER

systemctl --user daemon-reload

echo "Created timers:"
echo "  $AUDIT_TIMER"
echo "  $LLM_TIMER"
echo
echo "Schedules:"
echo "  daily audit:  OnCalendar=$AUDIT_CALENDAR"
echo "  llm cache:    OnCalendar=$LLM_CALENDAR"
echo
echo "Enable:"
echo "  systemctl --user enable --now trading-bot-daily-audit.timer"
echo "  systemctl --user enable --now trading-bot-llm-cache-report.timer"
echo
echo "Daily paper ops (rank/LLM validation):"
echo "  bash scripts/install_paper_daily_timer.sh"
echo
echo "Weekly slippage (separate config):"
echo "  bash scripts/install_slippage_report_timer.sh"
echo
echo "Manual batch:"
echo "  bash scripts/run_ops_reports.sh"
echo "  bash scripts/run_ops_reports.sh --weekly"
echo "  bash scripts/run_ops_reports.sh --heavy"
