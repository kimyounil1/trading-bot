The patch wires a new pytest target into the default workflow without including that target in the tracked changes, so the workflow breaks on a clean checkout. The implementation also does not match the requested tests-only scope.

Review comment:

- [P1] Include the new gate test before invoking it — /home/kimyo/trading-bot/scripts/run_pass_complete.sh:40-40
  As submitted in the tracked patch, `run_pass_complete.sh` now always asks pytest to collect `tests/test_portfolio_backtest_gate.py`, but that test file is not part of the tracked diff/review packet. In a clean checkout of this patch, the default pass-complete command will fail immediately with `file or directory not found` instead of running the harness.
