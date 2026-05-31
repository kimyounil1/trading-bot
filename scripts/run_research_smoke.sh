#!/usr/bin/env bash
# Smoke-test research-only modules (no production imports).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHON="${ROOT}/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON=python3
fi

echo "=== deep_model smoke ==="
if ! "$PYTHON" -c "import torch" 2>/dev/null; then
  echo "SKIP deep_model: torch not installed (research optional)"
else
  "$PYTHON" - <<'PY'
import numpy as np
import pandas as pd

from src.deep_model import prepare_deep_training_data, train_deep_model

df = pd.DataFrame(np.random.randn(80, 24).astype(np.float32))
X, y = prepare_deep_training_data(df, seq_len=10)
if len(X) < 2:
    raise SystemExit("insufficient synthetic windows")
train_deep_model(X[:2], y[:2])
print("deep_model: OK", tuple(X.shape))
PY
fi

echo "=== rl_portfolio smoke ==="
if ! "$PYTHON" -c "import gymnasium" 2>/dev/null; then
  echo "SKIP rl_portfolio: gymnasium not installed (research optional)"
else
  "$PYTHON" - <<'PY'
import numpy as np
import pandas as pd

from src.rl_portfolio import TradingEnv

df = pd.DataFrame({"close": np.linspace(100, 110, 50)})
env = TradingEnv(df)
obs, _ = env.reset()
obs, reward, done, truncated, info = env.step(np.array([0.5], dtype=np.float32))
print("rl_portfolio: OK", float(reward), done, truncated)
PY
fi

echo "=== research smoke complete ==="
