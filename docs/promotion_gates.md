# Model promotion gates

Champion replacement runs only when `build_promotion_report()` returns `decision: PROMOTE`.  
Champion files (`models/ai_score_model.joblib`) are **local-only** and updated only on `PROMOTE`.

## ML quality (training CV)

| Gate | Default | Code |
|------|---------|------|
| Min avg ROC-AUC | 0.51 | `MlQualityPromotionCriteria.min_avg_roc_auc` |
| Max overall Brier | 0.25 | `max_overall_brier` |
| Reject high fold variance | yes | `reject_high_fold_variance` (ROC-AUC std ≥ 0.05) |

Fold analysis: `python -m src.fold_variance_report`

## Portfolio OOS (holdout backtest)

| Gate | Default | Code |
|------|---------|------|
| Max drawdown floor | -20% | `PortfolioBacktestThresholds.max_drawdown_floor` |
| Min return vs benchmark | -15% pp | `min_return_vs_benchmark` |
| Min Sharpe | (optional) | `min_sharpe` |

Challenger must also **beat** stored champion portfolio OOS on Sharpe → return → drawdown.

## AUC vs champion

Challenger `oos_metrics.avg_roc_auc` must exceed champion when champion metadata exists.

## CLI

```bash
PYTHONPATH=. .venv/bin/python -m src.promotion_summary
PYTHONPATH=. .venv/bin/python -m src.promotion_summary --gates-only
```

Report path: `logs/ml/model_promotion_report.json`
