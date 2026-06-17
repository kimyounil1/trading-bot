"""Crowding 2->3 A/B gate: apply once rank-gate paper observation completes.

Idempotent. Safe to run daily (e.g. from a timer) or once by hand.

  - default : if rank observation is complete AND not already applied,
              flip config/strategy_config.json crowding_max_positions 2 -> 3,
              back up the config, and record an A/B baseline marker.
  - --status   : print readiness + applied state, do nothing.
  - --rollback : restore crowding_max_positions to the pre-A/B value.

Evidence/queue rationale: TODO §7. crowding->3 alone raised backtest deployment
12->38% with best full-period return, but blocked-name 5d fwd return is still
negative (-3.9%), so this is a MONITORED paper A/B with a rollback rule, not a
permanent guard relaxation.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

CFG = Path("config/strategy_config.json")
PV = Path("logs/paper_validation/latest_summary.json")
PNL = Path("logs/portfolio_pnl/latest_summary.json")
MARKER = Path("logs/crowding_ab/applied.json")
BACKUP = Path("logs/crowding_ab/strategy_config.bak.json")
KEY = "crowding_max_positions"
TARGET = 3
EVAL_DAYS = 14


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rank_ready() -> tuple[bool, dict]:
    if not PV.is_file():
        return False, {"error": "paper_validation latest_summary missing"}
    tr = (json.loads(PV.read_text(encoding="utf-8")).get("rank_gate_paper_tracker") or {})
    ready = bool(tr.get("gate_ready")) or (
        int(tr.get("calendar_days_with_rank_events") or 0)
        >= int(tr.get("min_calendar_days_required") or 14)
    )
    return ready, {
        "gate_ready": tr.get("gate_ready"),
        "calendar_days_with_rank_events": tr.get("calendar_days_with_rank_events"),
        "min_calendar_days_required": tr.get("min_calendar_days_required"),
        "last_date": tr.get("last_date"),
    }


def _current_crowding() -> int | None:
    m = re.search(rf'"{KEY}"\s*:\s*(\d+)', CFG.read_text(encoding="utf-8"))
    return int(m.group(1)) if m else None


def _baseline_cash_pct() -> float | None:
    if not PNL.is_file():
        return None
    d = json.loads(PNL.read_text(encoding="utf-8"))
    for k in ("cash_pct", "cash_weight", "cash_ratio"):
        if isinstance(d.get(k), (int, float)):
            return round(float(d[k]) * (100 if d[k] <= 1 else 1), 1)
    return None


def _set_crowding(value: int) -> int:
    text = CFG.read_text(encoding="utf-8")
    new_text, n = re.subn(rf'("{KEY}"\s*:\s*)\d+', rf"\g<1>{value}", text, count=1)
    if n != 1:
        raise SystemExit(f"expected exactly one '{KEY}' line, found {n}")
    tmp = CFG.with_suffix(".json.tmp")
    tmp.write_text(new_text, encoding="utf-8")
    tmp.replace(CFG)
    return n


def cmd_status() -> None:
    ready, info = _rank_ready()
    print(f"rank observation ready: {ready}  {info}")
    print(f"current {KEY}: {_current_crowding()}")
    print(f"applied marker: {'YES ' + MARKER.read_text() if MARKER.is_file() else 'no'}")


def cmd_rollback() -> None:
    if not MARKER.is_file():
        raise SystemExit("no A/B marker — nothing to roll back")
    marker = json.loads(MARKER.read_text(encoding="utf-8"))
    prev = int(marker.get("prev_value", 2))
    _set_crowding(prev)
    marker["rolled_back_at"] = _now()
    MARKER.write_text(json.dumps(marker, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"ROLLED BACK {KEY} -> {prev}. Restart bot to pick up: systemctl --user restart trading-bot")


def cmd_apply() -> None:
    if MARKER.is_file() and "rolled_back_at" not in json.loads(MARKER.read_text(encoding="utf-8")):
        print("already applied (marker present) — no-op")
        return
    ready, info = _rank_ready()
    if not ready:
        print(f"rank observation NOT complete — no-op  {info}")
        return
    prev = _current_crowding()
    if prev == TARGET:
        print(f"{KEY} already {TARGET}; writing marker only")
    else:
        BACKUP.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(CFG, BACKUP)
        _set_crowding(TARGET)
    applied_at = datetime.now(timezone.utc)
    marker = {
        "applied_at": _now(),
        "key": KEY,
        "prev_value": prev,
        "new_value": TARGET,
        "rank_readiness": info,
        "baseline_cash_pct": _baseline_cash_pct(),
        "eval_until": (applied_at + timedelta(days=EVAL_DAYS)).strftime("%Y-%m-%d"),
        "rollback_rule": (
            "Roll back (scripts/crowding_ab_gate.py --rollback) if after ~14d MDD "
            "worsens materially without a deployment/return gain, or if blocked-name "
            "forward returns stay negative. See TODO §7 / logs/guard_scenario_2w."
        ),
        "config_backup": str(BACKUP),
    }
    MARKER.parent.mkdir(parents=True, exist_ok=True)
    MARKER.write_text(json.dumps(marker, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"APPLIED {KEY} {prev} -> {TARGET}. A/B eval until {marker['eval_until']}.")
    print("Takes effect on the next scheduled bot run (or: systemctl --user restart trading-bot).")


def main() -> None:
    ap = argparse.ArgumentParser(description="Crowding 2->3 A/B gate")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--rollback", action="store_true")
    args = ap.parse_args()
    if args.status:
        cmd_status()
    elif args.rollback:
        cmd_rollback()
    else:
        cmd_apply()


if __name__ == "__main__":
    main()
