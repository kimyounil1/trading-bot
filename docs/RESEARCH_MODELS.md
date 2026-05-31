# Research-only models (not live)

`src/deep_model.py` (Transformer/GRU) and `src/rl_portfolio.py` (PPO) are **experimental infrastructure only**.

| Module | Status | Live path |
|--------|--------|-----------|
| `deep_model.py` | PyTorch prototype | **Not imported** by `main.py`, `train_ai_model.py`, or promotion |
| `rl_portfolio.py` | Gymnasium/PPO prototype | **Not imported** by production entrypoints |

Production signals use regime-aware **LightGBM + XGBoost** (`src/ml_model.py`). Do not enable deep/RL modules in `config/strategy_config.json` until a dedicated promotion path exists.

## Experiment branch

```bash
git checkout -b research/<topic>
bash scripts/run_research_smoke.sh
```

Details: [`experiments/README.md`](../experiments/README.md).
