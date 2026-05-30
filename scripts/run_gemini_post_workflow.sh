#!/bin/bash

# RUN_ID is set by the orchestrator or caller. If not set, use a timestamp.
# IMPLEMENTATION_AGENT labels the review packet (cursor, gemini, manual, etc.).
if [ -z "$RUN_ID" ]; then
  RUN_ID=$(date +%Y%m%dT%H%M%S)
fi
IMPLEMENTATION_AGENT="${IMPLEMENTATION_AGENT:-manual}"

OUT_DIR="reports/agent_pipeline/$RUN_ID"
mkdir -p "$OUT_DIR"

echo "Collecting git status..."
git status -- ':!reports' > "$OUT_DIR/git_status.txt" 2>&1 || true

echo "Collecting changed files..."
if git diff --quiet -- ':!reports'; then
  git diff --name-only origin/main -- ':!reports' > "$OUT_DIR/changed_files.txt" 2>/dev/null || git show --name-only --format="" HEAD -- ':!reports' > "$OUT_DIR/changed_files.txt"
else
  git diff --name-only -- ':!reports' > "$OUT_DIR/changed_files.txt"
fi

echo "Collecting git diff stat..."
if git diff --quiet -- ':!reports'; then
  git diff --stat origin/main -- ':!reports' > "$OUT_DIR/git_diff_stat.txt" 2>/dev/null || git show --stat HEAD -- ':!reports' > "$OUT_DIR/git_diff_stat.txt"
else
  git diff --stat -- ':!reports' > "$OUT_DIR/git_diff_stat.txt"
fi

echo "Collecting git diff patch..."
if git diff --quiet -- ':!reports'; then
  git diff origin/main -- ':!reports' > "$OUT_DIR/git_diff.patch" 2>/dev/null || git show HEAD -- ':!reports' > "$OUT_DIR/git_diff.patch"
else
  git diff -- ':!reports' > "$OUT_DIR/git_diff.patch"
fi

echo "Running review harness checks..."
.venv/bin/python -m compileall -q src/ > "$OUT_DIR/review_harness.log" 2>&1
HARNESS_EXIT=$?
cp "$OUT_DIR/review_harness.log" "$OUT_DIR/gemini_review_harness.log" 2>/dev/null || true

echo "Running runtime tests..."
.venv/bin/python -m pytest \
  tests/test_report_performance.py \
  tests/test_reappraise_regime.py \
  tests/test_portfolio_backtest_golden.py \
  tests/test_portfolio_backtest_gate.py \
  tests/test_daily_audit_summary.py \
  tests/test_daily_audit_summary_schema.py \
  tests/test_retrain_notifications.py \
  tests/test_llm_cache_report_schema.py \
  tests/test_leverage_stress_report.py \
  tests/test_guard_impact_report.py \
  tests/test_check_audit_daily_summary.py \
  tests/test_fold_variance_report.py \
  tests/test_promotion_summary.py \
  tests/test_benchmark_gap_report.py \
  tests/test_champion_promotion_governance.py \
  > "$OUT_DIR/runtime_harness.log" 2>&1
RUNTIME_EXIT=$?

echo "Running portfolio backtest gate (if outputs exist)..."
GATE_EXIT=0
if [ -f logs/portfolio_backtest/portfolio_summary.csv ]; then
  PYTHONPATH=. .venv/bin/python scripts/check_portfolio_backtest_gate.py \
    >> "$OUT_DIR/review_harness.log" 2>&1 || GATE_EXIT=$?
else
  echo "skip: logs/portfolio_backtest/portfolio_summary.csv not found" \
    >> "$OUT_DIR/review_harness.log"
fi

echo "Running audit daily summary smoke (if output exists)..."
AUDIT_GATE_EXIT=0
if [ -f logs/audit_daily/latest_summary.json ]; then
  PYTHONPATH=. .venv/bin/python scripts/check_audit_daily_summary.py \
    >> "$OUT_DIR/review_harness.log" 2>&1 || AUDIT_GATE_EXIT=$?
else
  echo "skip: logs/audit_daily/latest_summary.json not found" \
    >> "$OUT_DIR/review_harness.log"
fi

echo "Generating review packet..."
cat <<EOF > "$OUT_DIR/review_packet.md"
# Agent Review Packet - Run: $RUN_ID

## Implementation Agent
$IMPLEMENTATION_AGENT

## Task Description
$(cat "$OUT_DIR/TASK.md" 2>/dev/null || echo "Task details not found")

## Changed Files
$(cat "$OUT_DIR/changed_files.txt" | sed 's/^/- /')

## Git Diff Summary
\`\`\`
$(cat "$OUT_DIR/git_diff_stat.txt")
\`\`\`

## Test Execution Results (runtime_harness.log)
\`\`\`
$(cat "$OUT_DIR/runtime_harness.log")
\`\`\`

## Git Patch
\`\`\`diff
$(cat "$OUT_DIR/git_diff.patch")
\`\`\`
EOF

echo "Creating draft NEXT_TODO.md..."
echo -e "# NEXT_TODO\n\n- [ ] Codex review pending for implementation agent: $IMPLEMENTATION_AGENT\n- [ ] Review completed. No follow-ups drafted yet." > "$OUT_DIR/NEXT_TODO.md"

echo "Creating summary.json..."
cat <<EOF > "$OUT_DIR/summary.json"
{
  "overall_status": "$([ $HARNESS_EXIT -eq 0 ] && [ $RUNTIME_EXIT -eq 0 ] && [ $GATE_EXIT -eq 0 ] && [ $AUDIT_GATE_EXIT -eq 0 ] && echo "pass" || echo "fail")",
  "gemini_review_harness_exit_code": $HARNESS_EXIT,
  "runtime_harness_exit_code": $RUNTIME_EXIT,
  "portfolio_gate_exit_code": $GATE_EXIT,
  "audit_daily_gate_exit_code": $AUDIT_GATE_EXIT
}
EOF

echo "Post-workflow complete."
