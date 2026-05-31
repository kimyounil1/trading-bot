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

Two threshold profiles (`src/promotion_thresholds.py`):

| Profile | Min return vs benchmark | Max DD | Min Sharpe | Used by |
|---------|-------------------------|--------|------------|---------|
| **Promotion** | **0 pp** (must beat benchmark) | -20% | 1.0 | `train_ai_model` retrain / `build_promotion_report` |
| **CI / post-workflow** | -15 pp | -20% | (none) | `check_portfolio_backtest_gate`, golden regression |

Override promotion via env: `PROMOTION_MIN_RETURN_VS_BENCHMARK`, `PROMOTION_MIN_SHARPE`, `PROMOTION_MAX_DRAWDOWN_FLOOR`.

Challenger must also **beat** stored champion portfolio OOS on Sharpe → return → drawdown.

## AUC vs champion

Challenger `oos_metrics.avg_roc_auc` must exceed champion when champion metadata exists.

## Alpha / benchmark tracking

```bash
bash scripts/run_alpha_pipeline.sh
```

Report: `logs/benchmark_gap/latest_summary.json` (`beats_benchmark`, `recommendations`).

## CLI

```bash
PYTHONPATH=. .venv/bin/python -m src.promotion_summary
PYTHONPATH=. .venv/bin/python -m src.promotion_summary --gates-only
```

Report path: `logs/ml/model_promotion_report.json`
