The slippage automation mostly works for matched fills, but the no-fill weekly path leaves stale latest artifacts. More importantly, the new model promotion OOS gate does not evaluate the configured portfolio strategy, which can make promotion decisions incorrect.

Full review comments:

- [P1] Pass live exit/allocation settings into OOS gate — /home/kimyo/trading-bot/src/train_ai_model.py:396-420
  When `settings` uses non-default exits or allocation (the project defaults include stop loss, take profit, and trailing stop), this holdout promotion run falls back to `run_portfolio_backtest` defaults (`0` exits and `equal_weight`) because those settings are not forwarded. That means the promotion decision can be based on a materially different portfolio strategy than the configured/live one, so a challenger can be promoted or retained for the wrong OOS P&L/Sharpe.

- [P2] Persist a fresh weekly artifact when there are no fills — /home/kimyo/trading-bot/src/report_performance.py:266-268
  For weeks with no matched paper fills, the scheduled report returns before writing `latest_summary.json`. If a previous report exists, dashboards or runbook checks will continue reading stale slippage data while the timer appears to have completed successfully; write a zero-trade/no-data summary (or clear/update `latest_summary.json`) for this branch.
