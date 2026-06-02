#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

OUT_DIR="logs/paper_ops"
mkdir -p "$OUT_DIR"
OUT_PATH="${OUT_DIR}/scheduler_health.json"

timer_active="$(systemctl --user is-active trading-bot-daily-paper-ops.timer 2>/dev/null || echo "unknown")"
next_line="$(systemctl --user list-timers trading-bot-daily-paper-ops.timer --no-pager 2>/dev/null | sed -n '2p' || true)"
linger_state="unknown"
if command -v loginctl >/dev/null 2>&1; then
  linger_state="$(loginctl show-user "$USER" -p Linger --value 2>/dev/null || echo "unknown")"
fi

.venv/bin/python - "$OUT_PATH" "$timer_active" "$next_line" "$linger_state" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

out_path = Path(sys.argv[1])
payload = {
    "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "timer_name": "trading-bot-daily-paper-ops.timer",
    "timer_active": sys.argv[2],
    "next_timer_line": sys.argv[3],
    "linger_enabled": sys.argv[4],
    "recommended_action": (
        "run: loginctl enable-linger $USER"
        if sys.argv[4] in {"no", "false", "0"}
        else None
    ),
}
out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Wrote {out_path}")
print(json.dumps(payload, ensure_ascii=False))
PY
