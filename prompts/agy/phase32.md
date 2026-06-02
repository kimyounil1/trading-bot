# [AGY] Phase 32 — paper validation + rank gate

## Tests

```bash
AGY_TEST_PATHS="tests/test_paper_buy_validation_report.py tests/test_ops_report_paper_validation.py tests/test_rank_ai_gate.py tests/test_rank_ai_gate_impact_report.py tests/test_execution_audit_io.py tests/test_paper_ops_summary_rank_gate.py" \
  bash scripts/run_agy_slice.sh
```

Do not edit production `src/main.py` unless fixing test failures from AGY-owned harness only.

## Close

```bash
RUN_ID=phase32 AGY_PROMPT=prompts/agy/phase32.md bash scripts/run_balanced_pass.sh
```
