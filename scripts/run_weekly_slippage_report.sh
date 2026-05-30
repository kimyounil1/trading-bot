#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
LOG_DIR="$PROJECT_DIR/logs/slippage_report_runs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/slippage_${TIMESTAMP}.log"

LOOKBACK_DAYS="$("$PROJECT_DIR/.venv/bin/python" - <<'PY'
import json
from pathlib import Path
path = Path("config/slippage_report_config.json")
if path.is_file():
    print(int(json.loads(path.read_text()).get("lookback_days", 7)))
else:
    print(7)
PY
)"

TELEGRAM_FLAG=""
if "$PROJECT_DIR/.venv/bin/python" - <<'PY'
import json
from pathlib import Path
path = Path("config/slippage_report_config.json")
if path.is_file() and json.loads(path.read_text()).get("notify_telegram"):
    raise SystemExit(0)
raise SystemExit(1)
PY
then
  TELEGRAM_FLAG="--telegram"
fi

{
  echo "timestamp=$TIMESTAMP"
  echo "lookback_days=$LOOKBACK_DAYS"
  echo "--------------------------------------------------------------------------------"
  PYTHONPATH=. "$PROJECT_DIR/.venv/bin/python" -m src.report_performance \
    --weekly \
    --days "$LOOKBACK_DAYS" \
    $TELEGRAM_FLAG
} >"$LOG_FILE" 2>&1

echo "Weekly slippage report completed: $LOG_FILE"
