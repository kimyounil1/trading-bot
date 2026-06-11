# Model promotion gates

For **what AI is allowed to control** (filter vs rank buy gate vs full buy/sell), see [`ai_authority_gates.md`](ai_authority_gates.md).

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

## Research artifacts (rank / guard / exit-timing)

Champion promotion is separate from **paper-only** research gates. Consolidated report:

```bash
bash scripts/run_research_promotion_gates.sh
# or
PYTHONPATH=. .venv/bin/python -m src.promotion_summary --research
```

Output: `logs/research_promotion_gates/latest_summary.json`

| Source | Role |
|--------|------|
| `logs/ml/rank_label_experiment*/latest_summary.json` | Rank-label OOS sweep; gate = gap ≥ 0 pp, Sharpe ≥ 1.0, MDD ≥ −20%, turnover ≤ 1.2 |
| `data/research/guard_regime_policy.json` | Sector/crowding limits by bull/bear; **do not relax** during Rank AI paper observation |
| `logs/regime_stop_backtest/latest_summary.json` | Regime adaptive stops — **not adopted** (baseline 5%/20% wins) |
| `logs/intraday_timing_2w/latest_summary.json` | Intraday schedule — **keep 09:35/15:45** |

**Paper Rank AI (Tier 1)** — passed OOS, wired in config, champion swap still blocked:

| Field | Value |
|-------|-------|
| Experiment | `rank_label_experiment_h20_top15_q85` |
| OOS gap | +14.4 pp vs equal-weight |
| Sharpe | 1.76 |
| Config | `rank_ai_buy_gate_enabled=true`, model path in `strategy_config.json` |
| Live default | Blocked until ≥ 2 weeks paper validation (`ai_authority_gates.md`) |
