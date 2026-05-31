# Research experiments (non-production)

Branches for `deep_model.py` and `rl_portfolio.py` only. **Do not merge into `main` without a promotion path.**

## Smoke (local)

```bash
bash scripts/run_research_smoke.sh
```

Runs a tiny Torch forward pass and a short Gymnasium env step — no `main.py`, no model promotion.

## Modules

| Module | Entry | Output |
|--------|-------|--------|
| `src/deep_model.py` | `train_deep_model` | in-memory only |
| `src/rl_portfolio.py` | `train_rl_agent` | `models/rl_portfolio_agent` (gitignored) |

See [`docs/RESEARCH_MODELS.md`](../docs/RESEARCH_MODELS.md).

## Suggested branch workflow

```bash
git checkout -b research/deep-rl-smoke
bash scripts/run_research_smoke.sh
# iterate in src/deep_model.py or src/rl_portfolio.py
```

Production signals remain **LightGBM + XGBoost** (`src/ml_model.py`).
