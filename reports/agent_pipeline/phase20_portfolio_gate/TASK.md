# [AGY] Phase 20 — portfolio backtest gate tests

## Context

Cursor added (do not modify unless tests require it):

- `src/portfolio_backtest_validation.py` — `check_portfolio_backtest_thresholds`, `PortfolioBacktestThresholds`
- `scripts/check_portfolio_backtest_gate.py` — CLI used in post-workflow
- Post-workflow calls gate when `logs/portfolio_backtest/` exists

## Your scope (tests only)

1. Add `tests/test_portfolio_backtest_gate.py`:
   - pass: summary fixture with acceptable DD and benchmark gap
   - fail: max_drawdown worse than floor
   - fail: return vs benchmark below min gap
   - CLI: `check_portfolio_backtest_gate.py` exit 0/1 with tmp dir fixtures

2. Do **not** change production logic in `src/main.py` or trading paths.

## Verify

```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/test_portfolio_backtest_gate.py -q
```

## After commit

Tell user to run in Cursor terminal:

```bash
RUN_ID=phase20_portfolio_gate SKIP_PYTEST=1 bash scripts/run_pass_complete.sh
```

Commit message must include `[agy]`.
