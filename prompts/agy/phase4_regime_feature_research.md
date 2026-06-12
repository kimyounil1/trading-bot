# [Research] Phase 4-B — Weak regime feature experiment

**Mode:** `[Research]` (report-only; no champion promotion)

## Goal

Evaluate feature bundles for weak regimes flagged in `logs/ml/regime_weakness_report.json`. Gate: per-regime mean ROC-AUC ≥ **0.52**.

## Run

```bash
bash scripts/run_regime_feature_experiment.sh
```

## Scope

- `src/regime_feature_experiment.py` — bundles: baseline, watchlist, macro_stress, momentum_breadth
- Output: `logs/ml/regime_feature_experiment_report.json`
- pytest: `tests/test_regime_feature_experiment.py`

## Out of scope

- Champion swap, `main.py`, paper config changes
