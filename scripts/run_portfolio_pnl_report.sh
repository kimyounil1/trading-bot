#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

.venv/bin/python - <<'PY'
from src.portfolio_pnl_report import build_portfolio_pnl_snapshot, write_portfolio_pnl_artifacts
from src.settings import load_settings

settings = load_settings()
snapshot = build_portfolio_pnl_snapshot(broker_provider=settings.broker_provider)
path = write_portfolio_pnl_artifacts(snapshot)
print(f"Portfolio P&L snapshot written: {path}")
print(f"Total equity: ${snapshot.total_equity:,.2f}")
print(f"Today: ${snapshot.today.pnl_usd:+,.2f} ({snapshot.today.pnl_pct:+.2f}%)")
print(f"1W: ${snapshot.week.pnl_usd:+,.2f} ({snapshot.week.pnl_pct:+.2f}%)")
print(f"1M: ${snapshot.month.pnl_usd:+,.2f} ({snapshot.month.pnl_pct:+.2f}%)")
print(f"All: ${snapshot.all_time.pnl_usd:+,.2f} ({snapshot.all_time.pnl_pct:+.2f}%)")
print(f"Realized total (FIFO): ${snapshot.realized.total_usd:+,.2f}")
print(f"Realized 1W: ${snapshot.realized.week_usd:+,.2f}")
PY
