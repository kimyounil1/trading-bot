# [Research] Phase 4-C — Fold stability regularization sweep

**Mode:** `[Research]` (report-only; no champion promotion)

## Goal

Sweep LGBM/XGB regularization to reduce fold ROC-AUC std below **0.05** (focus BEAR high-variance).

## Run

```bash
bash scripts/run_fold_stability_experiment.sh
```

## Scope

- `src/fold_stability_experiment.py`
- Output: `logs/ml/fold_stability_experiment_report.json`
- pytest: `tests/test_fold_stability_experiment.py`

## Out of scope

- Champion swap, live order paths
