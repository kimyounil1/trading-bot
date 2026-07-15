# [AGY] Phase 32 — Threshold retune + label sweep tests

## Context (Cursor `[cursor]`)

- `src/threshold_retune_cli.py` — refresh threshold grid without full retrain
- `src/label_challenger_sweep.py` — portfolio-first label candidate comparison
- `src/threshold_promotion_summary.py` — operator summary JSON
- `scripts/run_threshold_promotion_pipeline.sh`

## Your scope (tests only)

1. `tests/test_threshold_retune_cli.py` — mock `_run_threshold_retune`, assert report keys written
2. Extend `tests/test_label_challenger_sweep.py` — legacy path `logs/ml/label_challenger/latest_summary.json` for h20/t0.02
3. `tests/test_threshold_promotion_summary.py` — builds actions from fixture JSON files

Do not edit `src/main.py`, training paths, or `.env`.

## Verify

```bash
PYTHONPATH=. .venv/bin/python -m pytest \
  tests/test_threshold_retune_cli.py \
  tests/test_label_challenger_sweep.py \
  tests/test_threshold_promotion_summary.py \
  -q
```

## Close pass

```bash
RUN_ID=phase32_threshold_promotion AGY_PROMPT=prompts/agy/phase32_threshold_promotion.md \
  bash scripts/run_balanced_pass.sh
```

Commit: `[agy] phase32 threshold promotion tests`
