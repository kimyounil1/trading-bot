# [Research] Phase 4-A — Calibration experiment & reports

**Mode:** `[Research]` (AGY implements; no `main.py` or order paths)

## Goal

Fix calibration data pipeline and produce isotonic/Platt comparison artifacts. Target: path to **Brier ≤ 0.25** (from 0.337). Runtime overlay wiring is **`[Cursor]`** slice 4-A-C — do not connect `calibrate_ai_score` to live score path in this pass.

## Scope

1. `bash scripts/run_retrain.sh` (or minimal repro) — ensure `src/ml_quality_report.py` writes `logs/ml/model_calibration_rows.csv` (currently `calibration_experiment_report.json` reports `missing_data`).
2. `python -m src.calibration_experiment` — isotonic vs Platt; output `logs/ml/model_calibration_bins.csv` and summary JSON.
3. Add/extend pytest for calibration CSV schemas and report outputs.
4. Document blockers for Brier gate in task summary (no champion swap).

## Out of scope

- `src/ai_score_calibration.py` runtime integration (`[Cursor]` 4-A-C)
- `config/strategy_config.json` changes
- `models/ai_score_model.joblib` champion replacement

## Verify

```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/ -k calibration -q
ls -la logs/ml/model_calibration_rows.csv logs/ml/model_calibration_bins.csv
```

## Handoff

Commit `[research]`. Cursor picks up 4-A-C. Then `[AGY-test]` on integration + `RUN_ID=phase4_cal bash scripts/run_pass_complete.sh`.
