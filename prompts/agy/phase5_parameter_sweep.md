# [Research] Phase 5 — Entry signal & sizing sweeps

**Mode:** `[Research]` (report-only)

## Run

```bash
bash scripts/run_strategy_parameter_sweep.sh all
```

Outputs: `logs/strategy_parameter_sweep/entry_signal_sweep_report.json`, `sizing_exit_sweep_report.json`

## Gate

OOS holdout: gap ≥ 0pp · Sharpe ≥ 1.0 · beats baseline OOS gap by **+0.5pp**

## Out of scope

Paper config adopt (`[Cursor]` 5-adopt) without explicit pass review.
