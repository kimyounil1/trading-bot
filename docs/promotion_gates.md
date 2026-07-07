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
| `logs/regime_stop_backtest/latest_summary.json` | Regime adaptive stops — **not adopted** (baseline wins) |
| `logs/intraday_timing_2w/latest_summary.json` | Intraday schedule — **keep 09:35/15:45** |
| `logs/ml/rank_universe_ab/` | Universe 110→255 expansion (2026-07) — **REJECTED** (Sharpe halved, MDD 3x) |
| `logs/ml/rank_gap_feature_retrain/` · `logs/ml/earnings_feature_retrain/` · `reports/news_feature_ic.json` | gap_vol · earnings · VADER news features — **all REJECTED** |
| `logs/ml/rank_regime_gate/` | Regime-conditional rank cutoff — **REJECTED** (6m pass, 12m fail) |

**2026-06/07 교훈 (게이트 설계 원칙):**
1. **단일 피처 IC 통과 ≠ 모델 게이트 통과** — 6연속 확인. IC 스크린은 필요조건일 뿐, 채택은 반드시 재학습 OOS 포트폴리오 게이트를 거칠 것.
2. **단일 홀드아웃 갭은 시끄러움** — 홀드아웃 시작 1주 이동에 갭이 6%p 출렁 (36%→30%). 승격급 결정은 다중 윈도우(예: 6m + 12m) 검증 필수 — 레짐 게이트가 6m 통과 후 12m에서 뒤집힌 사례.
3. **백테스트 gap ≠ 라이브 기대치** — 동일 윈도우 실측에서 paper(+3.1%)가 무제약 시뮬(+0.2%)을 상회 (`logs/sim_paper_gap/`).

**Paper Rank AI (Tier 1)** — passed OOS, wired in config, champion swap still blocked:

| Field | Value |
|-------|-------|
| Experiment | `rank_label_experiment_h20_top15_q85` |
| OOS gap | +14.4 pp vs equal-weight |
| Sharpe | 1.76 |
| Config | `rank_ai_buy_gate_enabled=true`, model path in `strategy_config.json` |
| Live default | 2주 paper validation **충족 (14/14, 2026-06-16)** — live 기본 ON은 operator sign-off 대기 (`ai_authority_gates.md`) |
