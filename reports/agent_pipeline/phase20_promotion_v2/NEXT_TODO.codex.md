The patch excludes the holdout from model fitting, but the promotion portfolio gate still uses thresholds selected on that same holdout window. This undermines the requested OOS evaluation and should be fixed before considering the change correct.

Review comment:

- [P1] Keep threshold retuning off the holdout window — /home/kimyo/trading-bot/src/train_ai_model.py:587-587
  With the new holdout split, the challenger is trained on `training_data_fit`, but the threshold retune later still receives the full `training_data` and internally optimizes over the latest six months. When `settings.use_ai_score` is enabled, the subsequent promotion backtest uses those retuned buy/exit thresholds on the same holdout period, so the claimed OOS portfolio gate is tuned on the evaluation slice rather than held out.
