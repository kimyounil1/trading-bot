The added report path exists, but the walk-forward ROC-AUC stability artifact is populated from inner training CV metrics instead of the outer validation folds it is meant to describe.

Review comment:

- [P2] Measure walk-forward ROC-AUC on validation folds — /home/kimyo/trading-bot/src/walk_forward_validation.py:103-109
  In `walk_forward_validation`, `fold_metrics_df` comes from `train_ai_score_model(...)`, which is the model's internal time-series CV over the training window, then it is labeled with the outer walk-forward test period. For walk-forward runs this reports training-window CV ROC-AUC rather than ROC-AUC on the actual `t_start`–`t_end` validation fold, so the new stability report can look stable even when the out-of-sample fold predictions are not.
