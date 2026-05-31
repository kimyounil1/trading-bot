The patch only contains generated retraining/log artifacts and does not deliver the requested portfolio backtest gate test changes. It should not be considered correct until the accidental artifacts are removed and the intended tests are included.

Review comment:

- [P1] Revert accidental retraining artifacts — /home/kimyo/trading-bot/logs/retrain_history.csv:5-5
  For this tests-only portfolio gate slice, this new retrain-history row and the paired metrics/model artifact changes appear to come from a local retraining run rather than the requested gate tests. Merging this would replace the checked-in model state and logs without any production or test rationale, while the requested test changes are not part of this patch.
