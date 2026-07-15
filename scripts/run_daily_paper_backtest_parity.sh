#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHON="${ROOT}/.venv/bin/python"
CONFIG="${ROOT}/config/paper_backtest_parity_config.json"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON=python3
fi

readarray -t VALUES < <("$PYTHON" - <<'PY'
import json
from pathlib import Path
cfg = json.loads(Path("config/paper_backtest_parity_config.json").read_text(encoding="utf-8"))
print(cfg.get("backtest_start", "2026-01-02"))
print(float(cfg.get("initial_cash", 10000.0)))
print(cfg.get("backtest_output_dir", "logs/daily_paper_backtest/latest"))
print(cfg.get("report_output_dir", "logs/paper_backtest_parity"))
PY
)
START_DATE="${VALUES[0]}"
INITIAL_CASH="${VALUES[1]}"
BACKTEST_DIR="${VALUES[2]}"
REPORT_DIR="${VALUES[3]}"
END_DATE="$(date +%F)"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
LOG_DIR="${ROOT}/logs/paper_backtest_parity_runs"
mkdir -p "$LOG_DIR"
LOG_FILE="${LOG_DIR}/parity_${STAMP}.log"

exec > >(tee -a "$LOG_FILE") 2>&1

echo "=== daily paper/backtest parity started ${STAMP} ==="
"$PYTHON" -m src.run_portfolio_backtest \
  --start "$START_DATE" \
  --end "$END_DATE" \
  --initial-cash "$INITIAL_CASH" \
  --outdir "$BACKTEST_DIR"

"$PYTHON" -m src.paper_backtest_parity \
  --config "$CONFIG" \
  --backtest-entries "$BACKTEST_DIR/portfolio_entries.csv" \
  --backtest-equity "$BACKTEST_DIR/portfolio_equity.csv" \
  --output-dir "$REPORT_DIR" \
  --notify-anomalies
echo "=== daily paper/backtest parity complete; log=${LOG_FILE} ==="
