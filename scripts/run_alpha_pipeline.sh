#!/usr/bin/env bash
# Refresh portfolio backtest, benchmark gap, and promotion gate summary.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHON="${ROOT}/.venv/bin/python"
export PYTHONPATH=.

echo "=== portfolio backtest ==="
"$PYTHON" -m src.run_portfolio_backtest

echo "=== benchmark gap ==="
"$PYTHON" -m src.benchmark_gap_report

echo "=== LLM / news filter impact (cache replay) ==="
LLM_EXTRA=()
if [[ "${LIVE_LLM:-}" == "1" ]]; then
  LLM_EXTRA+=(--live-llm)
fi
if [[ "${LIVE_NEWS:-}" == "1" ]]; then
  LLM_EXTRA+=(--live-news)
fi
"$PYTHON" -m src.llm_backtest_impact_report "${LLM_EXTRA[@]}"

IMPACT="$("$PYTHON" - <<'PY'
import json
from pathlib import Path
p = Path("logs/llm_backtest_impact/latest_summary.json")
if not p.is_file():
    print("missing")
else:
    r = json.loads(p.read_text())
    adj = r["with_live_filters"]
    print(
        f"approx_return={adj.get('approx_strategy_return_pct')}% "
        f"blocked={adj.get('blocked_trades')} beats≈{adj.get('beats_benchmark_approx')}"
    )
PY
)"
echo "LLM impact: $IMPACT"

echo "=== promotion gates (metadata only) ==="
"$PYTHON" -m src.promotion_summary --gates-only

GAP="$("$PYTHON" - <<'PY'
import json
from pathlib import Path
p = Path("logs/benchmark_gap/latest_summary.json")
if not p.is_file():
    print("missing")
else:
    r = json.loads(p.read_text())
    print(f"gap_pp={r.get('gap_pct')} beats={r.get('beats_benchmark')}")
PY
)"
echo "Result: $GAP"
echo "=== alpha pipeline complete ==="
