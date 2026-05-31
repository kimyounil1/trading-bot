The new promotion gate is intended to enforce OOS portfolio performance, but it evaluates the challenger on data included in training. This undermines the correctness of the promotion decision.

Review comment:

- [P1] Use a true holdout for the portfolio OOS gate — /home/kimyo/trading-bot/src/train_ai_model.py:657-663
  When `settings.use_ai_score` is enabled, this evaluates the challenger with `training_data` after `bundle` has already been trained on that same full dataset, including the last six months selected inside `_run_retrain_oos_portfolio`. That makes the new portfolio “OOS” gate in-sample for the challenger, so an overfit model can pass promotion based on prices it was trained on; the evaluation window needs to be excluded from challenger training or scored from an actually out-of-sample fold/holdout.
