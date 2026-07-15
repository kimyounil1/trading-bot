# [AGY] Phase 32 — Rank AI paper gate tests & harness

## Context (Cursor `[cursor]` — do not modify unless tests require)

Production / reports already landed:

- `src/rank_ai_gate.py` — cross-sectional rank buy/add gate
- `src/rank_ai_gate_impact_report.py` — paper impact from audit + candidate cache
- `src/execution_audit_io.py` — stable audit CSV schema (`rank_ai_score`, `rank_ai_percentile`)
- `src/logger.py` — audit append with schema normalize
- `src/main.py`, `src/candidate_cache.py` — gate wired on buy/add path only (sells unchanged)
- `docs/ai_authority_gates.md` — Tier 0–3 authority rules
- `scripts/run_rank_ai_gate_report.sh`

## Your scope (tests & harness only)

1. **Extend** `tests/test_rank_ai_gate_impact_report.py`:
   - empty audit + empty cache notes
   - audit with rank blocked / passed reason strings
   - candidate cache `risk_allowed` + percentile cutoff logic

2. **Extend** `tests/test_execution_audit_io.py`:
   - normalize rewrites file readable by `pd.read_csv`
   - row with only legacy header (no rank cols) + row with trailing rank fields

3. **Add** `tests/test_paper_ops_summary_rank_gate.py`:
   - `build_paper_ops_summary` includes `rank_ai_gate` block when fixture JSON present

4. Optional harness (no `main.py` edits): `tests/harness/test_rank_gate_report_smoke.py` that calls `build_rank_ai_gate_impact_report` with tmp fixtures only.

## Do not

- Edit `src/main.py`, order paths, `config/strategy_config.json`, or `.env`
- Change rank model artifacts under `logs/ml/`
- Run live/paper `--execute`

## Verify

```bash
PYTHONPATH=. .venv/bin/python -m pytest \
  tests/test_rank_ai_gate_impact_report.py \
  tests/test_execution_audit_io.py \
  tests/test_rank_ai_gate.py \
  tests/test_paper_ops_summary_rank_gate.py \
  -q
```

## After pytest green

Orchestrator (Cursor terminal):

```bash
RUN_ID=phase32_rank_ai AGY_PROMPT=prompts/agy/phase32_rank_ai_paper.md \
  bash scripts/run_balanced_pass.sh
```

Commit message: `[agy] phase32 rank AI paper gate tests`
