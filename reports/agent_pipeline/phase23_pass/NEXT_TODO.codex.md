The patch updates the production model artifact even though its recorded performance is below the project's degradation threshold and worse than the prior logged model. That can directly affect trading decisions for any environment using the committed champion artifact.

Review comment:

- [P1] Do not ship a degraded champion model — /home/kimyo/trading-bot/logs/ml/ai_model_metrics.csv:2-6
  With this artifact update, the committed champion model is replaced while the accompanying fold metrics average to ROC-AUC 0.5081, which is below the runbook's documented degradation threshold of 0.51 and below the previous logged champion average of 0.5127. In any deployment that loads `models/ai_score_model.joblib` from the repo, this promotes a known-degraded model into live scoring rather than retaining the prior champion.
