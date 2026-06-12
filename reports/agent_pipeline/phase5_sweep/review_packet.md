# Agent Review Packet - Run: phase5_sweep

## Implementation Agent
cursor

## Task Description
Pass phase5_sweep: Cursor implementation + AGY tests complete. Request Codex review.

## Changed Files
- TODO.md
- logs/crowding_paper/go_no_go_checklist.json
- logs/crowding_paper/reassessment.json
- logs/llm_advisory/latest_summary.json
- logs/llm_advisory/precision.json
- logs/ml/regime_weakness_report.json
- logs/paper_validation/history.jsonl
- logs/paper_validation/latest_summary.json
- logs/paper_validation/trend_summary.json
- src/portfolio_backtest_settings.py
- src/portfolio_backtester.py
- tests/fixtures/ml_quality/golden_fold_stability_report.json
- tests/fixtures/ml_quality/golden_model_calibration_report.json

## Git Diff Summary
```
 TODO.md                                            |  15 +-
 logs/crowding_paper/go_no_go_checklist.json        |   2 +-
 logs/crowding_paper/reassessment.json              |   6 +-
 logs/llm_advisory/latest_summary.json              | 168 ++++++-
 logs/llm_advisory/precision.json                   |  42 +-
 logs/ml/regime_weakness_report.json                |  23 +-
 logs/paper_validation/history.jsonl                |   8 +
 logs/paper_validation/latest_summary.json          | 513 ++++++++++++++-------
 logs/paper_validation/trend_summary.json           |  91 +++-
 src/portfolio_backtest_settings.py                 |   1 +
 src/portfolio_backtester.py                        |   9 +
 .../ml_quality/golden_fold_stability_report.json   |   2 +-
 .../golden_model_calibration_report.json           |   2 +-
 13 files changed, 666 insertions(+), 216 deletions(-)
```

## Test Execution Results (runtime_harness.log)
```
============================= test session starts ==============================
platform linux -- Python 3.12.8, pytest-9.0.3, pluggy-1.6.0
rootdir: /home/kimyo/trading-bot
plugins: anyio-4.13.0
collected 45 items

tests/test_report_performance.py .....                                   [ 11%]
tests/test_reappraise_regime.py ...                                      [ 17%]
tests/test_portfolio_backtest_golden.py ...                              [ 24%]
tests/test_portfolio_backtest_gate.py .....                              [ 35%]
tests/test_daily_audit_summary.py ....                                   [ 44%]
tests/test_daily_audit_summary_schema.py ....                            [ 53%]
tests/test_retrain_notifications.py ....                                 [ 62%]
tests/test_llm_cache_report_schema.py ..                                 [ 66%]
tests/test_leverage_stress_report.py ...                                 [ 73%]
tests/test_guard_impact_report.py ..                                     [ 77%]
tests/test_check_audit_daily_summary.py ...                              [ 84%]
tests/test_fold_variance_report.py .                                     [ 86%]
tests/test_promotion_summary.py ..                                       [ 91%]
tests/test_benchmark_gap_report.py .                                     [ 93%]
tests/test_champion_promotion_governance.py ...                          [100%]

=============================== warnings summary ===============================
.venv/lib/python3.12/site-packages/websockets/legacy/__init__.py:6
  /home/kimyo/trading-bot/.venv/lib/python3.12/site-packages/websockets/legacy/__init__.py:6: DeprecationWarning: websockets.legacy is deprecated; see https://websockets.readthedocs.io/en/stable/howto/upgrade.html for upgrade instructions
    warnings.warn(  # deprecated in 14.0 - 2024-11-09

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 45 passed, 1 warning in 4.26s =========================
```

## Git Patch
```diff
diff --git a/TODO.md b/TODO.md
index 214118c..66b2e1f 100644
--- a/TODO.md
+++ b/TODO.md
@@ -33,9 +33,9 @@
 | **Alpha** | trailing 20% · 전략 **+76.1%** vs EW **+67.1%** (gap **+9.0pp**) · SPY **+28.9pp** (`logs/benchmark_gap/latest_summary.json`) |
 | **Crowding** | config **ON** · reassessment `DISABLE_OR_KEEP_OFF` (blocked_trades=0) |
 | **Paper ops** | daily timer active · `logs/paper_ops/latest_summary.json` |
-| **LLM (paper)** | blocking mode · Gemini 429 간헐 · **precision 리포트 stale** (`precision.json` 6/2 이후 미갱신, `llm_reject n=0` 오탐) |
-| **Rank AI (paper)** | buy/add gate ON · `rank_gate_ready` false — **~10/14일 · ~4일 남음** |
-| **Live readiness** | **블로커 3건** — LLM precision · data_health ^VIX 오탐 · (연쇄) LLM verdict 파싱 |
+| **LLM (paper)** | blocking mode · Gemini 429 간헐 · precision 리포트 §1-A 수리 완료 (일일 bootstrap) |
+| **Rank AI (paper)** | buy/add gate ON · `rank_gate_ready` false — **~11/14일 · ~3일 남음** (`run_live_readiness.sh`) |
+| **Live readiness** | **시간 조건 2건만** — rank 14d · paper_validation 14d (코드 블로커 해소됨) |
 | **Champion AI** | **유지** — promotion gate 미통과. **모델 품질:** Brier **0.323** (CV rebuild) · isotonic OOF **0.244** (`calibration_experiment` ok) · fold std 0.0695 · champion 승격은 여전히 블로커 |
 | **Portfolio sleeves** | ON (core 50 / tournament 30 / cash 20) · registry + drift trim + allocation rebalance |
 | **Research (shipped)** | regime/intraday/guard/rank gates 결론 반영 (`b9f4f6c`) · stop5_trail10 paper trial **대기** · **전략 레이어 연구 소진 → 다음 헤드룸은 모델 품질 (Active §4)** |
@@ -66,7 +66,7 @@
 
 | # | 항목 | 상태 |
 |---|------|------|
-| 1 | **Rank AI paper 2주** — 매일 bootstrap → `logs/paper_validation` · `rank_gate_ready=true` | [ ] 진행 중 (~10/14 calendar days, **~4일 남음**) |
+| 1 | **Rank AI paper 2주** — 매일 bootstrap → `logs/paper_validation` · `rank_gate_ready=true` | [ ] 진행 중 (~11/14 calendar days, **~3일 남음**) |
 | 2 | **Paper validation 추세** — rolling agreement · SKIP 레이어 관찰 · rank/LLM spike alerts | [x] |
 | 3 | Codex scoped review `phase32_retry` | [x] |
 
@@ -110,9 +110,9 @@
 
 | # | Owner | 항목 | 상태 | 작업 내용 |
 |---|-------|------|------|----------|
-| **5-A** | `[Research]` | **진입 시그널 스윕** | [ ] | `ma_fast`(5–30) × `ma_slow`(30–100) × `rsi_buy_limit`(40–75) 그리드 — `research_promotion_gates.py` OOS 기준(gap≥0pp·Sharpe≥1.0) + 채택 임계 **+0.5pp**. train/OOS 분리 필수 |
-| **5-B** | `[Research]` | **사이징·익절 스윕** | [ ] | `conviction_position_mult_max`(1.0–1.5) · `take_profit_partial_pct`(0.10–0.25) · `partial_exit_ratio` · `max_holding_days`(20–60) — 동일 백테스터·동일 채택 기준 |
-| **5-adopt** | `[Cursor]` | **채택 시 config 반영** | [ ] | 스윕 pass 시에만 — `run_research_promotion_gates.sh` 경로로 paper config 반영 (자동 반영 금지) |
+| **5-A** | `[Research]` | **진입 시그널 스윕** | [x] | entry — **17/48 pass** · best OOS **ma5/ma50/rsi75** gap **+21.5pp** (holdout) · `logs/strategy_parameter_sweep/entry_signal_sweep_report.json` |
+| **5-B** | `[Research]` | **사이징·익절 스윕** | [x] | sizing — **32/64 pass** (baseline OOS gap -18pp) · best **pos0.15/tp0.10/hold45** · backtester `max_holding_days` 추가 · `sizing_exit_sweep_report.json` |
+| **5-adopt** | `[Cursor]` | **채택 시 config 반영** | [ ] | 스윕 후보 **수동 검토** — holdout 과최적화 의심 시 보류 · `run_research_promotion_gates.sh` 경로만 (자동 반영 금지) |
 
 **주의:** 5-A/5-B는 AGY `[Research]` 세션. 채택은 5-adopt `[Cursor]`만.
 
@@ -264,6 +264,7 @@ PYTHONPATH=. .venv/bin/python -m src.ml_quality_report --rebuild-calibration-row
 bash scripts/run_model_quality_report.sh   # calibration experiment + model_quality summary
 bash scripts/run_regime_feature_experiment.sh   # §4-B
 bash scripts/run_fold_stability_experiment.sh   # §4-C
+bash scripts/run_strategy_parameter_sweep.sh all  # §5 entry + sizing
 
 # Phase pass (Codex)
 RUN_ID=phase39_sleeve_alloc bash scripts/run_pass_complete.sh
diff --git a/logs/crowding_paper/go_no_go_checklist.json b/logs/crowding_paper/go_no_go_checklist.json
index 601e55f..201a788 100644
--- a/logs/crowding_paper/go_no_go_checklist.json
+++ b/logs/crowding_paper/go_no_go_checklist.json
@@ -22,7 +22,7 @@
     }
   ],
   "decision": "NO_GO",
-  "generated_at": "2026-06-02T09:06:08Z",
+  "generated_at": "2026-06-12T01:47:21Z",
   "guard_impact_path": "logs/guard_impact/latest_summary.json",
   "metrics": {
     "baseline": {
diff --git a/logs/crowding_paper/reassessment.json b/logs/crowding_paper/reassessment.json
index ab48000..4146181 100644
--- a/logs/crowding_paper/reassessment.json
+++ b/logs/crowding_paper/reassessment.json
@@ -1,5 +1,5 @@
 {
-  "generated_at": "2026-06-02T09:29:52Z",
+  "generated_at": "2026-06-12T01:47:21Z",
   "go_no_go_path": "logs/crowding_paper/go_no_go_checklist.json",
   "live_impact_path": "logs/crowding_live/latest_summary.json",
   "decision": "NO_GO",
@@ -8,8 +8,8 @@
     "blocked_trades": 0,
     "sharpe_delta": -0.7253,
     "total_return_delta_pct": -58.3771,
-    "live_crowding_skip_count": 287,
-    "live_crowding_skip_rate_of_skips": 0.071
+    "live_crowding_skip_count": 347,
+    "live_crowding_skip_rate_of_skips": 0.1318
   },
   "criteria": {
     "min_live_skip_rate": 0.01,
diff --git a/logs/llm_advisory/latest_summary.json b/logs/llm_advisory/latest_summary.json
index 663eeef..3c5bf1a 100644
--- a/logs/llm_advisory/latest_summary.json
+++ b/logs/llm_advisory/latest_summary.json
@@ -1,12 +1,12 @@
 {
-  "generated_at": "2026-06-02T09:05:50Z",
+  "generated_at": "2026-06-12T01:46:11Z",
   "audit_path": "logs/execution_audit.csv",
   "lookback_days": 90,
-  "rows": 4486,
+  "rows": 8268,
   "advisory_would_reject": 53,
-  "buy_submitted": 44,
+  "buy_submitted": 69,
   "buy_submitted_despite_llm_reject": 0,
-  "buy_blocked_by_llm": 14,
+  "buy_blocked_by_llm": 44,
   "sample_would_reject": [
     {
       "timestamp": "2026-06-01T12:32:18",
@@ -29,6 +29,22 @@
       "quantity": NaN,
       "filled_qty": NaN,
       "filled_avg_price": NaN,
+      "decision_id": NaN,
+      "run_id": NaN,
+      "broker": NaN,
+      "environment": NaN,
+      "config_hash": NaN,
+      "model_version": NaN,
+      "rank_model_version": NaN,
+      "risk_block_reason": NaN,
+      "order_intent_id": NaN,
+      "broker_order_id": NaN,
+      "sleeve_id": NaN,
+      "sleeve_strategy": NaN,
+      "sleeve_target_weight": NaN,
+      "sleeve_budget_before": NaN,
+      "sleeve_budget_after": NaN,
+      "sleeve_risk_mode": NaN,
       "llm_side": "REJECT"
     },
     {
@@ -52,6 +68,22 @@
       "quantity": NaN,
       "filled_qty": NaN,
       "filled_avg_price": NaN,
+      "decision_id": NaN,
+      "run_id": NaN,
+      "broker": NaN,
+      "environment": NaN,
+      "config_hash": NaN,
+      "model_version": NaN,
+      "rank_model_version": NaN,
+      "risk_block_reason": NaN,
+      "order_intent_id": NaN,
+      "broker_order_id": NaN,
+      "sleeve_id": NaN,
+      "sleeve_strategy": NaN,
+      "sleeve_target_weight": NaN,
+      "sleeve_budget_before": NaN,
+      "sleeve_budget_after": NaN,
+      "sleeve_risk_mode": NaN,
       "llm_side": "REJECT"
     },
     {
@@ -75,6 +107,22 @@
       "quantity": NaN,
       "filled_qty": NaN,
       "filled_avg_price": NaN,
+      "decision_id": NaN,
+      "run_id": NaN,
+      "broker": NaN,
+      "environment": NaN,
+      "config_hash": NaN,
+      "model_version": NaN,
+      "rank_model_version": NaN,
+      "risk_block_reason": NaN,
+      "order_intent_id": NaN,
+      "broker_order_id": NaN,
+      "sleeve_id": NaN,
+      "sleeve_strategy": NaN,
+      "sleeve_target_weight": NaN,
+      "sleeve_budget_before": NaN,
+      "sleeve_budget_after": NaN,
+      "sleeve_risk_mode": NaN,
       "llm_side": "REJECT"
     },
     {
@@ -98,6 +146,22 @@
       "quantity": NaN,
       "filled_qty": NaN,
       "filled_avg_price": NaN,
+      "decision_id": NaN,
+      "run_id": NaN,
+      "broker": NaN,
+      "environment": NaN,
+      "config_hash": NaN,
+      "model_version": NaN,
+      "rank_model_version": NaN,
+      "risk_block_reason": NaN,
+      "order_intent_id": NaN,
+      "broker_order_id": NaN,
+      "sleeve_id": NaN,
+      "sleeve_strategy": NaN,
+      "sleeve_target_weight": NaN,
+      "sleeve_budget_before": NaN,
+      "sleeve_budget_after": NaN,
+      "sleeve_risk_mode": NaN,
       "llm_side": "REJECT"
     },
     {
@@ -121,6 +185,22 @@
       "quantity": NaN,
       "filled_qty": NaN,
       "filled_avg_price": NaN,
+      "decision_id": NaN,
+      "run_id": NaN,
+      "broker": NaN,
+      "environment": NaN,
+      "config_hash": NaN,
+      "model_version": NaN,
+      "rank_model_version": NaN,
+      "risk_block_reason": NaN,
+      "order_intent_id": NaN,
+      "broker_order_id": NaN,
+      "sleeve_id": NaN,
+      "sleeve_strategy": NaN,
+      "sleeve_target_weight": NaN,
+      "sleeve_budget_before": NaN,
+      "sleeve_budget_after": NaN,
+      "sleeve_risk_mode": NaN,
       "llm_side": "REJECT"
     },
     {
@@ -144,6 +224,22 @@
       "quantity": NaN,
       "filled_qty": NaN,
       "filled_avg_price": NaN,
+      "decision_id": NaN,
+      "run_id": NaN,
+      "broker": NaN,
+      "environment": NaN,
+      "config_hash": NaN,
+      "model_version": NaN,
+      "rank_model_version": NaN,
+      "risk_block_reason": NaN,
+      "order_intent_id": NaN,
+      "broker_order_id": NaN,
+      "sleeve_id": NaN,
+      "sleeve_strategy": NaN,
+      "sleeve_target_weight": NaN,
+      "sleeve_budget_before": NaN,
+      "sleeve_budget_after": NaN,
+      "sleeve_risk_mode": NaN,
       "llm_side": "REJECT"
     },
     {
@@ -167,6 +263,22 @@
       "quantity": NaN,
       "filled_qty": NaN,
       "filled_avg_price": NaN,
+      "decision_id": NaN,
+      "run_id": NaN,
+      "broker": NaN,
+      "environment": NaN,
+      "config_hash": NaN,
+      "model_version": NaN,
+      "rank_model_version": NaN,
+      "risk_block_reason": NaN,
+      "order_intent_id": NaN,
+      "broker_order_id": NaN,
+      "sleeve_id": NaN,
+      "sleeve_strategy": NaN,
+      "sleeve_target_weight": NaN,
+      "sleeve_budget_before": NaN,
+      "sleeve_budget_after": NaN,
+      "sleeve_risk_mode": NaN,
       "llm_side": "REJECT"
     },
     {
@@ -190,6 +302,22 @@
       "quantity": NaN,
       "filled_qty": NaN,
       "filled_avg_price": NaN,
+      "decision_id": NaN,
+      "run_id": NaN,
+      "broker": NaN,
+      "environment": NaN,
+      "config_hash": NaN,
+      "model_version": NaN,
+      "rank_model_version": NaN,
+      "risk_block_reason": NaN,
+      "order_intent_id": NaN,
+      "broker_order_id": NaN,
+      "sleeve_id": NaN,
+      "sleeve_strategy": NaN,
+      "sleeve_target_weight": NaN,
+      "sleeve_budget_before": NaN,
+      "sleeve_budget_after": NaN,
+      "sleeve_risk_mode": NaN,
       "llm_side": "REJECT"
     },
     {
@@ -213,6 +341,22 @@
       "quantity": NaN,
       "filled_qty": NaN,
       "filled_avg_price": NaN,
+      "decision_id": NaN,
+      "run_id": NaN,
+      "broker": NaN,
+      "environment": NaN,
+      "config_hash": NaN,
+      "model_version": NaN,
+      "rank_model_version": NaN,
+      "risk_block_reason": NaN,
+      "order_intent_id": NaN,
+      "broker_order_id": NaN,
+      "sleeve_id": NaN,
+      "sleeve_strategy": NaN,
+      "sleeve_target_weight": NaN,
+      "sleeve_budget_before": NaN,
+      "sleeve_budget_after": NaN,
+      "sleeve_risk_mode": NaN,
       "llm_side": "REJECT"
     },
     {
@@ -236,6 +380,22 @@
       "quantity": NaN,
       "filled_qty": NaN,
       "filled_avg_price": NaN,
+      "decision_id": NaN,
+      "run_id": NaN,
+      "broker": NaN,
+      "environment": NaN,
+      "config_hash": NaN,
+      "model_version": NaN,
+      "rank_model_version": NaN,
+      "risk_block_reason": NaN,
+      "order_intent_id": NaN,
+      "broker_order_id": NaN,
+      "sleeve_id": NaN,
+      "sleeve_strategy": NaN,
+      "sleeve_target_weight": NaN,
+      "sleeve_budget_before": NaN,
+      "sleeve_budget_after": NaN,
+      "sleeve_risk_mode": NaN,
       "llm_side": "REJECT"
     }
   ],
diff --git a/logs/llm_advisory/precision.json b/logs/llm_advisory/precision.json
index c575d64..2ec8688 100644
--- a/logs/llm_advisory/precision.json
+++ b/logs/llm_advisory/precision.json
@@ -1,12 +1,18 @@
 {
-  "generated_at": "2026-06-02T09:14:58Z",
+  "generated_at": "2026-06-12T01:46:13Z",
   "lookback_days": 90,
   "horizon_days": 20,
+  "short_horizon_days": 5,
   "price_period": "2y",
-  "audit_rows": 4486,
+  "audit_rows": 8268,
   "events_used": {
-    "llm_reject": 0,
-    "llm_accept": 0
+    "llm_reject": 16,
+    "llm_accept": 96
+  },
+  "events_by_type": {
+    "SKIP_BUY": 220,
+    "BUY_SUBMITTED": 12,
+    "LLM_ADVISORY": 9
   },
   "forward_return": {
     "llm_reject": {
@@ -24,13 +30,35 @@
     "delta_mean_accept_minus_reject": null,
     "delta_hit_rate_accept_minus_reject": null
   },
+  "forward_return_short": {
+    "llm_reject": {
+      "n": 16,
+      "mean_return": -0.021341407105715297,
+      "median_return": -0.028863523192168672,
+      "hit_rate": 0.4375
+    },
+    "llm_accept": {
+      "n": 96,
+      "mean_return": -0.012157764027584275,
+      "median_return": 0.007641977086173868,
+      "hit_rate": 0.5729166666666666
+    },
+    "delta_mean_accept_minus_reject": 0.009183643078131022,
+    "delta_hit_rate_accept_minus_reject": 0.13541666666666663
+  },
   "excluded_rows": {
     "missing_price_data": 0,
-    "insufficient_forward_bars": 29,
-    "other": 7
+    "insufficient_forward_bars": 217,
+    "other": 24
+  },
+  "excluded_rows_short": {
+    "missing_price_data": 0,
+    "insufficient_forward_bars": 105,
+    "other": 24
   },
   "sample": [],
   "notes": [
-    "One side has zero usable forward returns; increase lookback or accumulate more advisory decisions."
+    "events_used counts matured forward returns at the 5d horizon (shortest configured); primary-horizon stats fill in as events age.",
+    "One side has zero usable forward returns at the primary horizon; increase lookback or accumulate more advisory decisions."
   ]
 }
\ No newline at end of file
diff --git a/logs/ml/regime_weakness_report.json b/logs/ml/regime_weakness_report.json
index ace2fbe..d267f7e 100644
--- a/logs/ml/regime_weakness_report.json
+++ b/logs/ml/regime_weakness_report.json
@@ -1,5 +1,5 @@
 {
-  "generated_at": "2026-06-02T09:22:38Z",
+  "generated_at": "2026-06-12T03:45:41Z",
   "status": "ok",
   "fold_metrics_path": "logs/ml/fold_metrics.csv",
   "feature_stats_path": "models/ai_feature_stats.json",
@@ -10,29 +10,28 @@
   "regimes": {
     "BEAR": {
       "folds": 3,
-      "roc_auc_mean": 0.5499764837112684,
-      "roc_auc_std": 0.08657682235613834,
+      "roc_auc_mean": 0.6122289559280844,
+      "roc_auc_std": 0.04885579717813042,
       "weak_regime": false,
-      "high_variance": true
+      "high_variance": false
     },
     "BULL": {
       "folds": 3,
-      "roc_auc_mean": 0.49286740953770564,
-      "roc_auc_std": 0.006372584802194666,
+      "roc_auc_mean": 0.49450231510807613,
+      "roc_auc_std": 0.01212611455788044,
       "weak_regime": true,
       "high_variance": false
     },
     "NEUTRAL": {
       "folds": 3,
-      "roc_auc_mean": 0.48545624682795846,
-      "roc_auc_std": 0.08139948457214617,
-      "weak_regime": true,
+      "roc_auc_mean": 0.5504258608274127,
+      "roc_auc_std": 0.07096264760609076,
+      "weak_regime": false,
       "high_variance": true
     }
   },
   "weak_regimes": [
-    "BULL",
-    "NEUTRAL"
+    "BULL"
   ],
   "feature_watchlist": [
     "spy_rel_return_20d",
@@ -84,7 +83,7 @@
     }
   },
   "recommendations": [
-    "Weak regimes detected: BULL, NEUTRAL (mean ROC-AUC < 0.50).",
+    "Weak regimes detected: BULL (mean ROC-AUC < 0.50).",
     "Run targeted feature experiments for weak regimes only (report-only; do not promote champion).",
     "Fold variance is high in at least one regime; prioritize stability before any authority expansion."
   ]
diff --git a/logs/paper_validation/history.jsonl b/logs/paper_validation/history.jsonl
index 9db4b3e..6f3a5db 100644
--- a/logs/paper_validation/history.jsonl
+++ b/logs/paper_validation/history.jsonl
@@ -1 +1,9 @@
 {"agreement_pct": 74.7, "buy_submitted": 44, "date": "2026-06-02", "generated_at": "2026-06-02T09:05:51Z", "rank_calendar_days": 4, "rank_gate_ready": false, "skip_ai_score": 18, "skip_llm_block": 14, "skip_rank_gate": 47}
+{"agreement_pct": 74.7, "buy_submitted": 44, "date": "2026-06-03", "generated_at": "2026-06-03T01:45:39Z", "rank_calendar_days": 4, "rank_gate_ready": false, "skip_ai_score": 18, "skip_llm_block": 14, "skip_rank_gate": 47}
+{"agreement_pct": 69.2, "buy_submitted": 48, "date": "2026-06-04", "generated_at": "2026-06-04T01:45:41Z", "rank_calendar_days": 5, "rank_gate_ready": false, "skip_ai_score": 18, "skip_llm_block": 15, "skip_rank_gate": 67}
+{"agreement_pct": 69.2, "buy_submitted": 48, "date": "2026-06-05", "generated_at": "2026-06-05T01:45:55Z", "rank_calendar_days": 5, "rank_gate_ready": false, "skip_ai_score": 18, "skip_llm_block": 15, "skip_rank_gate": 67}
+{"agreement_pct": 69.2, "buy_submitted": 53, "date": "2026-06-06", "generated_at": "2026-06-06T01:45:48Z", "rank_calendar_days": 6, "rank_gate_ready": false, "skip_ai_score": 18, "skip_llm_block": 15, "skip_rank_gate": 67}
+{"agreement_pct": 64.5, "buy_submitted": 61, "date": "2026-06-09", "generated_at": "2026-06-09T05:27:02Z", "rank_calendar_days": 8, "rank_gate_ready": false, "skip_ai_score": 26, "skip_llm_block": 34, "skip_rank_gate": 175}
+{"agreement_pct": 64.4, "buy_submitted": 61, "date": "2026-06-10", "generated_at": "2026-06-10T01:46:08Z", "rank_calendar_days": 9, "rank_gate_ready": false, "skip_ai_score": 28, "skip_llm_block": 34, "skip_rank_gate": 241}
+{"agreement_pct": 64.5, "buy_submitted": 61, "date": "2026-06-11", "generated_at": "2026-06-11T01:46:24Z", "rank_calendar_days": 10, "rank_gate_ready": false, "skip_ai_score": 58, "skip_llm_block": 36, "skip_rank_gate": 304}
+{"agreement_pct": 62.0, "buy_submitted": 69, "date": "2026-06-12", "generated_at": "2026-06-12T01:46:14Z", "rank_calendar_days": 11, "rank_gate_ready": false, "skip_ai_score": 80, "skip_llm_block": 44, "skip_rank_gate": 363}
diff --git a/logs/paper_validation/latest_summary.json b/logs/paper_validation/latest_summary.json
index 4e4306b..abf5a57 100644
--- a/logs/paper_validation/latest_summary.json
+++ b/logs/paper_validation/latest_summary.json
@@ -1,199 +1,199 @@
 {
-  "generated_at": "2026-06-02T09:05:51Z",
+  "generated_at": "2026-06-12T01:46:14Z",
   "lookback_days": 90,
   "llm_advisory_only": false,
   "rank_ai_buy_gate_enabled": true,
   "llm_ai_agreement": {
-    "generated_at": "2026-06-02T09:05:51Z",
+    "generated_at": "2026-06-12T01:46:14Z",
     "ai_score_buy_threshold": 0.4,
     "llm_cache_path": "data/llm_cache.json",
-    "llm_cache_entries": 88,
-    "comparable_with_ai_score": 87,
-    "agreement_rate": 0.7471264367816092,
-    "agreement_pct": 74.7,
-    "score_llm_corr": 0.04115883088749699,
+    "llm_cache_entries": 186,
+    "comparable_with_ai_score": 184,
+    "agreement_rate": 0.6195652173913043,
+    "agreement_pct": 62.0,
+    "score_llm_corr": -0.09841380779514758,
     "confusion": {
-      "both_pass": 65,
+      "both_pass": 114,
       "both_fail": 0,
-      "ai_pass_llm_reject": 19,
-      "ai_fail_llm_pass": 3
+      "ai_pass_llm_reject": 66,
+      "ai_fail_llm_pass": 4
     },
     "disagreements_sample": [
       {
-        "ticker": "UNH",
-        "date": "2026-06-01",
-        "ai_score": 0.9256,
+        "ticker": "WFC",
+        "date": "2026-06-11",
+        "ai_score": 0.9918,
         "ai_ok": true,
         "llm_ok": false,
         "agree": false,
-        "llm_category": "Fraud"
+        "llm_category": "Lawsuit"
       },
       {
-        "ticker": "MRK",
-        "date": "2026-06-02",
-        "ai_score": 0.7978,
+        "ticker": "ONDS",
+        "date": "2026-06-08",
+        "ai_score": 0.98,
         "ai_ok": true,
         "llm_ok": false,
         "agree": false,
-        "llm_category": "Other"
+        "llm_category": "Guidance"
       },
       {
-        "ticker": "QQQ",
-        "date": "2026-06-01",
-        "ai_score": 0.7855,
+        "ticker": "SMR",
+        "date": "2026-06-08",
+        "ai_score": 0.945,
         "ai_ok": true,
         "llm_ok": false,
         "agree": false,
-        "llm_category": "Other (Concentration risk/Correlation)."
+        "llm_category": "Guidance"
       },
       {
-        "ticker": "CVS",
+        "ticker": "UNH",
         "date": "2026-06-01",
-        "ai_score": 0.6722,
+        "ai_score": 0.9256,
         "ai_ok": true,
         "llm_ok": false,
         "agree": false,
-        "llm_category": "None, Lawsuit, Fraud, Guidance, Financials, Other"
+        "llm_category": "Fraud"
       },
       {
-        "ticker": "DIS",
-        "date": "2026-06-02",
-        "ai_score": 0.6674,
+        "ticker": "CRM",
+        "date": "2026-06-11",
+        "ai_score": 0.921,
         "ai_ok": true,
         "llm_ok": false,
         "agree": false,
         "llm_category": "Guidance"
       },
       {
-        "ticker": "META",
-        "date": "2026-06-02",
-        "ai_score": 0.6615,
+        "ticker": "UPS",
+        "date": "2026-06-11",
+        "ai_score": 0.9161,
         "ai_ok": true,
         "llm_ok": false,
         "agree": false,
-        "llm_category": "Financials"
+        "llm_category": "Guidance"
       },
       {
-        "ticker": "GM",
-        "date": "2026-06-01",
-        "ai_score": 0.6414,
+        "ticker": "ANET",
+        "date": "2026-06-11",
+        "ai_score": 0.8941,
         "ai_ok": true,
         "llm_ok": false,
         "agree": false,
-        "llm_category": "* Financials (the most direct impact mentioned is the loss of money from a product line). Alternatively, \"Other\" for the strike. Let's go with \"Financials\" as the underperforming SUV and labor issues "
+        "llm_category": "Other (Operational/Supply Chain)"
       },
       {
-        "ticker": "HOOD",
-        "date": "2026-06-01",
-        "ai_score": 0.6369,
+        "ticker": "PLTR",
+        "date": "2026-06-11",
+        "ai_score": 0.8854,
         "ai_ok": true,
         "llm_ok": false,
         "agree": false,
-        "llm_category": "None, Lawsuit, Fraud, Guidance, Financials, Other"
+        "llm_category": "Product Failure"
       },
       {
-        "ticker": "PATH",
-        "date": "2026-06-01",
-        "ai_score": 0.6153,
+        "ticker": "FCX",
+        "date": "2026-06-08",
+        "ai_score": 0.8854,
         "ai_ok": true,
         "llm_ok": false,
         "agree": false,
-        "llm_category": "**Guidance** (or Financials, but 'Weak earnings' usually implies guidance in market terms) or **Other** (Sentiment). However, \"Weak earnings\" often translates to poor forward guidance. Let's go with *"
+        "llm_category": "Guidance"
       },
       {
-        "ticker": "SMCI",
-        "date": "2026-06-01",
-        "ai_score": 0.612,
+        "ticker": "HD",
+        "date": "2026-06-08",
+        "ai_score": 0.8846,
         "ai_ok": true,
         "llm_ok": false,
         "agree": false,
-        "llm_category": "* Other (specifically regulatory/governance risk). *Note: While \"Fraud\" is a possibility, the headline doesn't prove fraud, it just suggests a need for better regulation/compliance. \"Other\" or \"Guidan"
+        "llm_category": "Guidance"
       },
       {
-        "ticker": "NKE",
-        "date": "2026-06-01",
-        "ai_score": 0.6085,
+        "ticker": "WFC",
+        "date": "2026-06-08",
+        "ai_score": 0.8623,
         "ai_ok": true,
         "llm_ok": false,
         "agree": false,
-        "llm_category": "* Other (Tariffs/Geopolitical risk doesn't fit Lawsuit, Fraud, Guidance, or Financials perfectly, though \"Other\" covers it. Actually, \"Guidance\" is about what the company says, \"Financials\" is about t"
+        "llm_category": "Other"
       },
       {
         "ticker": "NKE",
-        "date": "2026-06-02",
-        "ai_score": 0.6085,
+        "date": "2026-06-11",
+        "ai_score": 0.8124,
         "ai_ok": true,
         "llm_ok": false,
         "agree": false,
-        "llm_category": "Financials"
+        "llm_category": "Guidance"
       },
       {
-        "ticker": "PLD",
+        "ticker": "MRK",
         "date": "2026-06-02",
-        "ai_score": 0.588,
+        "ai_score": 0.7978,
         "ai_ok": true,
         "llm_ok": false,
         "agree": false,
-        "llm_category": "Guidance"
+        "llm_category": "Other"
       },
       {
-        "ticker": "ORCL",
-        "date": "2026-06-01",
-        "ai_score": 0.5217,
+        "ticker": "TSLA",
+        "date": "2026-06-11",
+        "ai_score": 0.795,
         "ai_ok": true,
         "llm_ok": false,
         "agree": false,
-        "llm_category": "* Other (or Financials/Guidance, but \"Other\" fits the combination of competitive risk and CapEx risk better). Let's look at \"Other\" for general sentiment/competitive/macro-sector risks. Actually, the "
+        "llm_category": "Guidance"
       },
       {
-        "ticker": "UNP",
-        "date": "2026-06-02",
-        "ai_score": 0.5191,
+        "ticker": "TGT",
+        "date": "2026-06-08",
+        "ai_score": 0.7943,
         "ai_ok": true,
         "llm_ok": false,
         "agree": false,
         "llm_category": "Other"
       },
       {
-        "ticker": "VZ",
-        "date": "2026-06-02",
-        "ai_score": 0.4855,
+        "ticker": "ONDS",
+        "date": "2026-06-10",
+        "ai_score": 0.7864,
         "ai_ok": true,
         "llm_ok": false,
         "agree": false,
-        "llm_category": "Guidance"
+        "llm_category": "Financials"
       },
       {
-        "ticker": "AAL",
+        "ticker": "QQQ",
         "date": "2026-06-01",
-        "ai_score": 0.4848,
+        "ai_score": 0.7855,
         "ai_ok": true,
         "llm_ok": false,
         "agree": false,
-        "llm_category": "Guidance (as the company is warning about future costs) or Financials. \"Guidance\" fits best as it is a warning about future performance/costs."
+        "llm_category": "Other (Concentration risk/Correlation)."
       },
       {
-        "ticker": "AMT",
-        "date": "2026-06-01",
-        "ai_score": 0.3332,
-        "ai_ok": false,
-        "llm_ok": true,
+        "ticker": "LYG",
+        "date": "2026-06-11",
+        "ai_score": 0.7827,
+        "ai_ok": true,
+        "llm_ok": false,
         "agree": false,
-        "llm_category": "None, Lawsuit, Fraud, Guidance, Financials, Other"
+        "llm_category": "Other"
       },
       {
-        "ticker": "SBUX",
-        "date": "2026-06-01",
-        "ai_score": 0.4612,
+        "ticker": "IWM",
+        "date": "2026-06-08",
+        "ai_score": 0.7476,
         "ai_ok": true,
         "llm_ok": false,
         "agree": false,
-        "llm_category": "Financials"
+        "llm_category": "Other"
       },
       {
-        "ticker": "SNAP",
-        "date": "2026-06-01",
-        "ai_score": 0.4529,
+        "ticker": "SOFI",
+        "date": "2026-06-08",
+        "ai_score": 0.7474,
         "ai_ok": true,
         "llm_ok": false,
         "agree": false,
@@ -207,52 +207,20 @@
     ],
     "candidate_buy": {
       "path": "logs/candidate_cache/latest_buy.csv",
-      "as_of_date": "2026-06-02",
-      "buy_signal_rows": 47,
-      "in_llm_cache": 8,
-      "agreement_rate": 0.375,
+      "as_of_date": "2026-06-12",
+      "buy_signal_rows": 74,
+      "in_llm_cache": 4,
+      "agreement_rate": 0.75,
       "confusion": {
         "both_pass": 3,
         "both_fail": 0,
-        "ai_pass_llm_reject": 5,
+        "ai_pass_llm_reject": 1,
         "ai_fail_llm_pass": 0
       },
       "disagreements": [
         {
-          "ticker": "VZ",
-          "ai_score": 0.4855356898045359,
-          "ai_ok": true,
-          "llm_ok": false,
-          "agree": false,
-          "in_llm_cache": true
-        },
-        {
-          "ticker": "UNP",
-          "ai_score": 0.4585588340252279,
-          "ai_ok": true,
-          "llm_ok": false,
-          "agree": false,
-          "in_llm_cache": true
-        },
-        {
-          "ticker": "MRK",
-          "ai_score": 0.6360055686297328,
-          "ai_ok": true,
-          "llm_ok": false,
-          "agree": false,
-          "in_llm_cache": true
-        },
-        {
-          "ticker": "DIS",
-          "ai_score": 0.5716816403618814,
-          "ai_ok": true,
-          "llm_ok": false,
-          "agree": false,
-          "in_llm_cache": true
-        },
-        {
-          "ticker": "PLD",
-          "ai_score": 0.5473124393095616,
+          "ticker": "LYG",
+          "ai_score": 0.6569835277327515,
           "ai_ok": true,
           "llm_ok": false,
           "agree": false,
@@ -262,14 +230,14 @@
     }
   },
   "llm_advisory_impact": {
-    "generated_at": "2026-06-02T09:05:51Z",
+    "generated_at": "2026-06-12T01:46:14Z",
     "audit_path": "logs/execution_audit.csv",
     "lookback_days": 90,
-    "rows": 4486,
+    "rows": 8268,
     "advisory_would_reject": 53,
-    "buy_submitted": 44,
+    "buy_submitted": 69,
     "buy_submitted_despite_llm_reject": 0,
-    "buy_blocked_by_llm": 14,
+    "buy_blocked_by_llm": 44,
     "sample_would_reject": [
       {
         "timestamp": "2026-06-01T12:32:18",
@@ -292,6 +260,22 @@
         "quantity": NaN,
         "filled_qty": NaN,
         "filled_avg_price": NaN,
+        "decision_id": NaN,
+        "run_id": NaN,
+        "broker": NaN,
+        "environment": NaN,
+        "config_hash": NaN,
+        "model_version": NaN,
+        "rank_model_version": NaN,
+        "risk_block_reason": NaN,
+        "order_intent_id": NaN,
+        "broker_order_id": NaN,
+        "sleeve_id": NaN,
+        "sleeve_strategy": NaN,
+        "sleeve_target_weight": NaN,
+        "sleeve_budget_before": NaN,
+        "sleeve_budget_after": NaN,
+        "sleeve_risk_mode": NaN,
         "llm_side": "REJECT"
       },
       {
@@ -315,6 +299,22 @@
         "quantity": NaN,
         "filled_qty": NaN,
         "filled_avg_price": NaN,
+        "decision_id": NaN,
+        "run_id": NaN,
+        "broker": NaN,
+        "environment": NaN,
+        "config_hash": NaN,
+        "model_version": NaN,
+        "rank_model_version": NaN,
+        "risk_block_reason": NaN,
+        "order_intent_id": NaN,
+        "broker_order_id": NaN,
+        "sleeve_id": NaN,
+        "sleeve_strategy": NaN,
+        "sleeve_target_weight": NaN,
+        "sleeve_budget_before": NaN,
+        "sleeve_budget_after": NaN,
+        "sleeve_risk_mode": NaN,
         "llm_side": "REJECT"
       },
       {
@@ -338,6 +338,22 @@
         "quantity": NaN,
         "filled_qty": NaN,
         "filled_avg_price": NaN,
+        "decision_id": NaN,
+        "run_id": NaN,
+        "broker": NaN,
+        "environment": NaN,
+        "config_hash": NaN,
+        "model_version": NaN,
+        "rank_model_version": NaN,
+        "risk_block_reason": NaN,
+        "order_intent_id": NaN,
+        "broker_order_id": NaN,
+        "sleeve_id": NaN,
+        "sleeve_strategy": NaN,
+        "sleeve_target_weight": NaN,
+        "sleeve_budget_before": NaN,
+        "sleeve_budget_after": NaN,
+        "sleeve_risk_mode": NaN,
         "llm_side": "REJECT"
       },
       {
@@ -361,6 +377,22 @@
         "quantity": NaN,
         "filled_qty": NaN,
         "filled_avg_price": NaN,
+        "decision_id": NaN,
+        "run_id": NaN,
+        "broker": NaN,
+        "environment": NaN,
+        "config_hash": NaN,
+        "model_version": NaN,
+        "rank_model_version": NaN,
+        "risk_block_reason": NaN,
+        "order_intent_id": NaN,
+        "broker_order_id": NaN,
+        "sleeve_id": NaN,
+        "sleeve_strategy": NaN,
+        "sleeve_target_weight": NaN,
+        "sleeve_budget_before": NaN,
+        "sleeve_budget_after": NaN,
+        "sleeve_risk_mode": NaN,
         "llm_side": "REJECT"
       },
       {
@@ -384,6 +416,22 @@
         "quantity": NaN,
         "filled_qty": NaN,
         "filled_avg_price": NaN,
+        "decision_id": NaN,
+        "run_id": NaN,
+        "broker": NaN,
+        "environment": NaN,
+        "config_hash": NaN,
+        "model_version": NaN,
+        "rank_model_version": NaN,
+        "risk_block_reason": NaN,
+        "order_intent_id": NaN,
+        "broker_order_id": NaN,
+        "sleeve_id": NaN,
+        "sleeve_strategy": NaN,
+        "sleeve_target_weight": NaN,
+        "sleeve_budget_before": NaN,
+        "sleeve_budget_after": NaN,
+        "sleeve_risk_mode": NaN,
         "llm_side": "REJECT"
       },
       {
@@ -407,6 +455,22 @@
         "quantity": NaN,
         "filled_qty": NaN,
         "filled_avg_price": NaN,
+        "decision_id": NaN,
+        "run_id": NaN,
+        "broker": NaN,
+        "environment": NaN,
+        "config_hash": NaN,
+        "model_version": NaN,
+        "rank_model_version": NaN,
+        "risk_block_reason": NaN,
+        "order_intent_id": NaN,
+        "broker_order_id": NaN,
+        "sleeve_id": NaN,
+        "sleeve_strategy": NaN,
+        "sleeve_target_weight": NaN,
+        "sleeve_budget_before": NaN,
+        "sleeve_budget_after": NaN,
+        "sleeve_risk_mode": NaN,
         "llm_side": "REJECT"
       },
       {
@@ -430,6 +494,22 @@
         "quantity": NaN,
         "filled_qty": NaN,
         "filled_avg_price": NaN,
+        "decision_id": NaN,
+        "run_id": NaN,
+        "broker": NaN,
+        "environment": NaN,
+        "config_hash": NaN,
+        "model_version": NaN,
+        "rank_model_version": NaN,
+        "risk_block_reason": NaN,
+        "order_intent_id": NaN,
+        "broker_order_id": NaN,
+        "sleeve_id": NaN,
+        "sleeve_strategy": NaN,
+        "sleeve_target_weight": NaN,
+        "sleeve_budget_before": NaN,
+        "sleeve_budget_after": NaN,
+        "sleeve_risk_mode": NaN,
         "llm_side": "REJECT"
       },
       {
@@ -453,6 +533,22 @@
         "quantity": NaN,
         "filled_qty": NaN,
         "filled_avg_price": NaN,
+        "decision_id": NaN,
+        "run_id": NaN,
+        "broker": NaN,
+        "environment": NaN,
+        "config_hash": NaN,
+        "model_version": NaN,
+        "rank_model_version": NaN,
+        "risk_block_reason": NaN,
+        "order_intent_id": NaN,
+        "broker_order_id": NaN,
+        "sleeve_id": NaN,
+        "sleeve_strategy": NaN,
+        "sleeve_target_weight": NaN,
+        "sleeve_budget_before": NaN,
+        "sleeve_budget_after": NaN,
+        "sleeve_risk_mode": NaN,
         "llm_side": "REJECT"
       },
       {
@@ -476,6 +572,22 @@
         "quantity": NaN,
         "filled_qty": NaN,
         "filled_avg_price": NaN,
+        "decision_id": NaN,
+        "run_id": NaN,
+        "broker": NaN,
+        "environment": NaN,
+        "config_hash": NaN,
+        "model_version": NaN,
+        "rank_model_version": NaN,
+        "risk_block_reason": NaN,
+        "order_intent_id": NaN,
+        "broker_order_id": NaN,
+        "sleeve_id": NaN,
+        "sleeve_strategy": NaN,
+        "sleeve_target_weight": NaN,
+        "sleeve_budget_before": NaN,
+        "sleeve_budget_after": NaN,
+        "sleeve_risk_mode": NaN,
         "llm_side": "REJECT"
       },
       {
@@ -499,6 +611,22 @@
         "quantity": NaN,
         "filled_qty": NaN,
         "filled_avg_price": NaN,
+        "decision_id": NaN,
+        "run_id": NaN,
+        "broker": NaN,
+        "environment": NaN,
+        "config_hash": NaN,
+        "model_version": NaN,
+        "rank_model_version": NaN,
+        "risk_block_reason": NaN,
+        "order_intent_id": NaN,
+        "broker_order_id": NaN,
+        "sleeve_id": NaN,
+        "sleeve_strategy": NaN,
+        "sleeve_target_weight": NaN,
+        "sleeve_budget_before": NaN,
+        "sleeve_budget_after": NaN,
+        "sleeve_risk_mode": NaN,
         "llm_side": "REJECT"
       }
     ],
@@ -509,49 +637,42 @@
     ]
   },
   "audit_buy_paths": {
-    "rows": 4486,
+    "rows": 8268,
     "llm_advisory_only": false,
     "ai_score_buy_threshold": 0.4,
-    "skip_buy_total": 4043,
+    "skip_buy_total": 7544,
     "skip_by_layer": {
-      "other": 3964,
-      "ai_score": 18,
-      "llm_block": 14,
-      "rank_gate": 47
+      "other": 7056,
+      "ai_score": 80,
+      "llm_block": 44,
+      "rank_gate": 363,
+      "rank_missing": 1
     },
-    "skip_ai_score_layer": 18,
-    "skip_llm_block_layer": 14,
-    "skip_rank_gate_layer": 47,
-    "skip_rank_missing_layer": 0,
-    "skip_other_layer": 3964,
-    "ai_pass_llm_block": 14,
-    "ai_fail_or_low_score": 387,
-    "buy_submitted": 44,
-    "buy_submitted_llm_accept": 36,
+    "skip_ai_score_layer": 80,
+    "skip_llm_block_layer": 44,
+    "skip_rank_gate_layer": 363,
+    "skip_rank_missing_layer": 1,
+    "skip_other_layer": 7056,
+    "ai_pass_llm_block": 44,
+    "ai_fail_or_low_score": 595,
+    "buy_submitted": 69,
+    "buy_submitted_llm_accept": 40,
     "buy_submitted_llm_reject_verdict": 0,
-    "buy_submitted_no_llm_verdict": 8,
+    "buy_submitted_no_llm_verdict": 29,
     "llm_advisory_would_reject_ai_passed": 53,
     "interpretation": "Blocking mode (llm_advisory_only=false): ai_pass_llm_block counts SKIP_BUY where AI score passed but LLM blocked. submitted_llm_reject_verdict should be ~0."
   },
   "rank_gate_paper_tracker": {
     "min_calendar_days_required": 14,
-    "calendar_days_with_rank_events": 4,
-    "audit_span_calendar_days": 7,
+    "calendar_days_with_rank_events": 11,
+    "audit_span_calendar_days": 17,
     "first_date": "2026-05-27",
-    "last_date": "2026-06-02",
-    "total_skip_buy_rank_blocked": 47,
-    "total_skip_buy_rank_missing": 0,
-    "total_buy_submitted": 44,
+    "last_date": "2026-06-12",
+    "total_skip_buy_rank_blocked": 363,
+    "total_skip_buy_rank_missing": 1,
+    "total_buy_submitted": 69,
     "gate_ready": false,
     "daily_tail": [
-      {
-        "date": "2026-05-27",
-        "events": 152,
-        "skip_buy": 125,
-        "rank_blocked": 0,
-        "rank_missing": 0,
-        "buy_submitted": 2
-      },
       {
         "date": "2026-05-28",
         "events": 652,
@@ -586,11 +707,83 @@
       },
       {
         "date": "2026-06-02",
-        "events": 837,
-        "skip_buy": 764,
+        "events": 961,
+        "skip_buy": 883,
         "rank_blocked": 47,
         "rank_missing": 0,
         "buy_submitted": 15
+      },
+      {
+        "date": "2026-06-03",
+        "events": 390,
+        "skip_buy": 380,
+        "rank_blocked": 0,
+        "rank_missing": 0,
+        "buy_submitted": 0
+      },
+      {
+        "date": "2026-06-04",
+        "events": 382,
+        "skip_buy": 370,
+        "rank_blocked": 20,
+        "rank_missing": 0,
+        "buy_submitted": 4
+      },
+      {
+        "date": "2026-06-05",
+        "events": 411,
+        "skip_buy": 373,
+        "rank_blocked": 0,
+        "rank_missing": 0,
+        "buy_submitted": 5
+      },
+      {
+        "date": "2026-06-06",
+        "events": 262,
+        "skip_buy": 254,
+        "rank_blocked": 0,
+        "rank_missing": 0,
+        "buy_submitted": 0
+      },
+      {
+        "date": "2026-06-08",
+        "events": 612,
+        "skip_buy": 511,
+        "rank_blocked": 35,
+        "rank_missing": 0,
+        "buy_submitted": 8
+      },
+      {
+        "date": "2026-06-09",
+        "events": 523,
+        "skip_buy": 495,
+        "rank_blocked": 92,
+        "rank_missing": 0,
+        "buy_submitted": 0
+      },
+      {
+        "date": "2026-06-10",
+        "events": 372,
+        "skip_buy": 371,
+        "rank_blocked": 67,
+        "rank_missing": 0,
+        "buy_submitted": 0
+      },
+      {
+        "date": "2026-06-11",
+        "events": 439,
+        "skip_buy": 371,
+        "rank_blocked": 53,
+        "rank_missing": 1,
+        "buy_submitted": 7
+      },
+      {
+        "date": "2026-06-12",
+        "events": 267,
+        "skip_buy": 257,
+        "rank_blocked": 49,
+        "rank_missing": 0,
+        "buy_submitted": 1
       }
     ],
     "notes": [
diff --git a/logs/paper_validation/trend_summary.json b/logs/paper_validation/trend_summary.json
index fbcb41f..7df39a9 100644
--- a/logs/paper_validation/trend_summary.json
+++ b/logs/paper_validation/trend_summary.json
@@ -1,33 +1,84 @@
 {
-  "generated_at": "2026-06-02T09:16:13Z",
+  "generated_at": "2026-06-12T03:58:39Z",
   "history_path": "logs/paper_validation/history.jsonl",
-  "rows": 1,
+  "rows": 9,
   "rolling_days": 7,
   "latest": {
-    "date": "2026-06-02",
-    "agreement_pct": 74.7,
-    "skip_ai_score": 18,
-    "skip_llm_block": 14,
-    "skip_rank_gate": 47,
-    "buy_submitted": 44,
-    "rank_calendar_days": 4,
+    "date": "2026-06-12",
+    "agreement_pct": 62.0,
+    "skip_ai_score": 80,
+    "skip_llm_block": 44,
+    "skip_rank_gate": 363,
+    "buy_submitted": 69,
+    "rank_calendar_days": 11,
     "rank_gate_ready": false
   },
   "rolling": {
-    "agreement_pct_mean": 74.7,
-    "skip_ai_score_mean": 18.0,
-    "skip_llm_block_mean": 14.0,
-    "skip_rank_gate_mean": 47.0,
-    "buy_submitted_mean": 44.0
+    "agreement_pct_mean": 66.14285714285714,
+    "skip_ai_score_mean": 35.142857142857146,
+    "skip_llm_block_mean": 27.571428571428573,
+    "skip_rank_gate_mean": 183.42857142857142,
+    "buy_submitted_mean": 57.285714285714285
   },
-  "alerts": [],
+  "alerts": [
+    "skip_llm_block_spike",
+    "skip_rank_gate_spike"
+  ],
   "tail": [
     {
-      "date": "2026-06-02",
-      "agreement_pct": 74.7,
-      "skip_llm_block": 14,
-      "skip_rank_gate": 47,
-      "buy_submitted": 44,
+      "date": "2026-06-04",
+      "agreement_pct": 69.2,
+      "skip_llm_block": 15,
+      "skip_rank_gate": 67,
+      "buy_submitted": 48,
+      "rank_gate_ready": false
+    },
+    {
+      "date": "2026-06-05",
+      "agreement_pct": 69.2,
+      "skip_llm_block": 15,
+      "skip_rank_gate": 67,
+      "buy_submitted": 48,
+      "rank_gate_ready": false
+    },
+    {
+      "date": "2026-06-06",
+      "agreement_pct": 69.2,
+      "skip_llm_block": 15,
+      "skip_rank_gate": 67,
+      "buy_submitted": 53,
+      "rank_gate_ready": false
+    },
+    {
+      "date": "2026-06-09",
+      "agreement_pct": 64.5,
+      "skip_llm_block": 34,
+      "skip_rank_gate": 175,
+      "buy_submitted": 61,
+      "rank_gate_ready": false
+    },
+    {
+      "date": "2026-06-10",
+      "agreement_pct": 64.4,
+      "skip_llm_block": 34,
+      "skip_rank_gate": 241,
+      "buy_submitted": 61,
+      "rank_gate_ready": false
+    },
+    {
+      "date": "2026-06-11",
+      "agreement_pct": 64.5,
+      "skip_llm_block": 36,
+      "skip_rank_gate": 304,
+      "buy_submitted": 61,
+      "rank_gate_ready": false
+    },
+    {
+      "date": "2026-06-12",
+      "agreement_pct": 62.0,
+      "skip_llm_block": 44,
+      "skip_rank_gate": 363,
+      "buy_submitted": 69,
       "rank_gate_ready": false
     }
   ]
diff --git a/src/portfolio_backtest_settings.py b/src/portfolio_backtest_settings.py
index 144d2e7..d3a64e4 100644
--- a/src/portfolio_backtest_settings.py
+++ b/src/portfolio_backtest_settings.py
@@ -55,6 +55,7 @@ def portfolio_backtest_kwargs(
         "stop_loss_pct": settings.stop_loss_pct,
         "take_profit_pct": settings.take_profit_pct,
         "trailing_stop_pct": settings.trailing_stop_pct,
+        "max_holding_days": getattr(settings, "max_holding_days", 0),
         "allocation_method": allocation_method or getattr(settings, "allocation_method", "equal_weight"),
         "ai_exit_enabled": getattr(settings, "ai_exit_enabled", False),
         "ai_exit_threshold": settings.ai_exit_threshold,
diff --git a/src/portfolio_backtester.py b/src/portfolio_backtester.py
index c0ee1b8..05564c5 100644
--- a/src/portfolio_backtester.py
+++ b/src/portfolio_backtester.py
@@ -288,6 +288,7 @@ def run_portfolio_backtest(
     stop_loss_pct: float = 0.0,
     take_profit_pct: float = 0.0,
     trailing_stop_pct: float = 0.0,
+    max_holding_days: int = 0,
     rank_trend_weight: float = 1.0,
     rank_ai_weight: float = 0.0,
     rank_momentum_weight: float = 0.0,
@@ -344,6 +345,8 @@ def run_portfolio_backtest(
         raise ValueError("take_profit_pct must be non-negative")
     if not 0 <= trailing_stop_pct < 1:
         raise ValueError("trailing_stop_pct must be between 0 and 1")
+    if max_holding_days < 0:
+        raise ValueError("max_holding_days must be non-negative")
 
     ai_model_bundle = None
     if use_ai_score:
@@ -498,6 +501,12 @@ def run_portfolio_backtest(
                 exit_reason = "STOP_LOSS"
             elif day_trailing_stop_pct > 0 and drawdown_from_high <= -day_trailing_stop_pct:
                 exit_reason = "TRAILING_STOP"
+            elif max_holding_days > 0:
+                held_days = (
+                    pd.Timestamp(current_date) - pd.Timestamp(position["entry_date"])
+                ).days
+                if held_days >= max_holding_days:
+                    exit_reason = "MAX_HOLDING"
             elif ai_exit_triggered:
                 exit_reason = "AI_EXIT"
             elif bool(row["sell_signal"]):
diff --git a/tests/fixtures/ml_quality/golden_fold_stability_report.json b/tests/fixtures/ml_quality/golden_fold_stability_report.json
index 3a47525..d93d150 100644
--- a/tests/fixtures/ml_quality/golden_fold_stability_report.json
+++ b/tests/fixtures/ml_quality/golden_fold_stability_report.json
@@ -20,7 +20,7 @@
     }
   },
   "fold_count": 4,
-  "generated_at": "2026-06-02T07:21:26Z",
+  "generated_at": "2026-06-12T00:42:07Z",
   "high_variance_warning": false,
   "roc_auc": {
     "coefficient_of_variation": 0.01359820733051054,
diff --git a/tests/fixtures/ml_quality/golden_model_calibration_report.json b/tests/fixtures/ml_quality/golden_model_calibration_report.json
index 77681b3..f67b779 100644
--- a/tests/fixtures/ml_quality/golden_model_calibration_report.json
+++ b/tests/fixtures/ml_quality/golden_model_calibration_report.json
@@ -1,6 +1,6 @@
 {
   "bin_count": 20,
-  "generated_at": "2026-06-02T07:21:26Z",
+  "generated_at": "2026-06-12T00:42:07Z",
   "overall_avg_brier_score": 0.25,
   "regimes": {
     "BEAR": {
```
