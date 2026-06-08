# Agent Review Packet - Run: phase34_followup

## Implementation Agent
cursor

## Task Description
Phase 34 live foundation + Phase 35 follow-up: broker adapter, live safety, readiness, dust guards, bootstrap health

## Changed Files
- config/execution_lock.json
- logs/crowding_paper/go_no_go_checklist.json
- logs/crowding_paper/reassessment.json
- logs/llm_advisory/latest_summary.json
- logs/paper_validation/history.jsonl
- logs/paper_validation/latest_summary.json
- logs/paper_validation/trend_summary.json
- tests/test_execution_resilience.py

## Git Diff Summary
```
 config/execution_lock.json                  |   4 +-
 logs/crowding_paper/go_no_go_checklist.json |   2 +-
 logs/crowding_paper/reassessment.json       |   6 +-
 logs/llm_advisory/latest_summary.json       | 108 ++++++++-
 logs/paper_validation/history.jsonl         |   4 +
 logs/paper_validation/latest_summary.json   | 339 ++++++++++++++++++----------
 logs/paper_validation/trend_summary.json    |  56 ++++-
 tests/test_execution_resilience.py          |   3 +-
 8 files changed, 375 insertions(+), 147 deletions(-)
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
======================== 45 passed, 1 warning in 3.58s =========================
```

## Git Patch
```diff
diff --git a/config/execution_lock.json b/config/execution_lock.json
index b9286a7..ae36e25 100644
--- a/config/execution_lock.json
+++ b/config/execution_lock.json
@@ -1,5 +1,5 @@
 {
-  "cms_execution_enabled": true,
+  "cms_execution_enabled": false,
   "required_phrase": "ENABLE PAPER EXECUTION",
-  "last_updated": "2026-05-20T17:00:51"
+  "last_updated": "2026-06-01T14:29:59"
 }
\ No newline at end of file
diff --git a/logs/crowding_paper/go_no_go_checklist.json b/logs/crowding_paper/go_no_go_checklist.json
index 601e55f..f994067 100644
--- a/logs/crowding_paper/go_no_go_checklist.json
+++ b/logs/crowding_paper/go_no_go_checklist.json
@@ -22,7 +22,7 @@
     }
   ],
   "decision": "NO_GO",
-  "generated_at": "2026-06-02T09:06:08Z",
+  "generated_at": "2026-06-06T01:46:05Z",
   "guard_impact_path": "logs/guard_impact/latest_summary.json",
   "metrics": {
     "baseline": {
diff --git a/logs/crowding_paper/reassessment.json b/logs/crowding_paper/reassessment.json
index ab48000..30a4c46 100644
--- a/logs/crowding_paper/reassessment.json
+++ b/logs/crowding_paper/reassessment.json
@@ -1,5 +1,5 @@
 {
-  "generated_at": "2026-06-02T09:29:52Z",
+  "generated_at": "2026-06-06T01:46:05Z",
   "go_no_go_path": "logs/crowding_paper/go_no_go_checklist.json",
   "live_impact_path": "logs/crowding_live/latest_summary.json",
   "decision": "NO_GO",
@@ -8,8 +8,8 @@
     "blocked_trades": 0,
     "sharpe_delta": -0.7253,
     "total_return_delta_pct": -58.3771,
-    "live_crowding_skip_count": 287,
-    "live_crowding_skip_rate_of_skips": 0.071
+    "live_crowding_skip_count": 317,
+    "live_crowding_skip_rate_of_skips": 0.0701
   },
   "criteria": {
     "min_live_skip_rate": 0.01,
diff --git a/logs/llm_advisory/latest_summary.json b/logs/llm_advisory/latest_summary.json
index 663eeef..8118a79 100644
--- a/logs/llm_advisory/latest_summary.json
+++ b/logs/llm_advisory/latest_summary.json
@@ -1,12 +1,12 @@
 {
-  "generated_at": "2026-06-02T09:05:50Z",
+  "generated_at": "2026-06-06T01:45:49Z",
   "audit_path": "logs/execution_audit.csv",
   "lookback_days": 90,
-  "rows": 4486,
+  "rows": 6055,
   "advisory_would_reject": 53,
-  "buy_submitted": 44,
+  "buy_submitted": 53,
   "buy_submitted_despite_llm_reject": 0,
-  "buy_blocked_by_llm": 14,
+  "buy_blocked_by_llm": 15,
   "sample_would_reject": [
     {
       "timestamp": "2026-06-01T12:32:18",
@@ -29,6 +29,16 @@
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
       "llm_side": "REJECT"
     },
     {
@@ -52,6 +62,16 @@
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
       "llm_side": "REJECT"
     },
     {
@@ -75,6 +95,16 @@
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
       "llm_side": "REJECT"
     },
     {
@@ -98,6 +128,16 @@
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
       "llm_side": "REJECT"
     },
     {
@@ -121,6 +161,16 @@
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
       "llm_side": "REJECT"
     },
     {
@@ -144,6 +194,16 @@
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
       "llm_side": "REJECT"
     },
     {
@@ -167,6 +227,16 @@
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
       "llm_side": "REJECT"
     },
     {
@@ -190,6 +260,16 @@
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
       "llm_side": "REJECT"
     },
     {
@@ -213,6 +293,16 @@
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
       "llm_side": "REJECT"
     },
     {
@@ -236,6 +326,16 @@
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
       "llm_side": "REJECT"
     }
   ],
diff --git a/logs/paper_validation/history.jsonl b/logs/paper_validation/history.jsonl
index 9db4b3e..8859f31 100644
--- a/logs/paper_validation/history.jsonl
+++ b/logs/paper_validation/history.jsonl
@@ -1 +1,5 @@
 {"agreement_pct": 74.7, "buy_submitted": 44, "date": "2026-06-02", "generated_at": "2026-06-02T09:05:51Z", "rank_calendar_days": 4, "rank_gate_ready": false, "skip_ai_score": 18, "skip_llm_block": 14, "skip_rank_gate": 47}
+{"agreement_pct": 74.7, "buy_submitted": 44, "date": "2026-06-03", "generated_at": "2026-06-03T01:45:39Z", "rank_calendar_days": 4, "rank_gate_ready": false, "skip_ai_score": 18, "skip_llm_block": 14, "skip_rank_gate": 47}
+{"agreement_pct": 69.2, "buy_submitted": 48, "date": "2026-06-04", "generated_at": "2026-06-04T01:45:41Z", "rank_calendar_days": 5, "rank_gate_ready": false, "skip_ai_score": 18, "skip_llm_block": 15, "skip_rank_gate": 67}
+{"agreement_pct": 69.2, "buy_submitted": 48, "date": "2026-06-05", "generated_at": "2026-06-05T01:45:55Z", "rank_calendar_days": 5, "rank_gate_ready": false, "skip_ai_score": 18, "skip_llm_block": 15, "skip_rank_gate": 67}
+{"agreement_pct": 69.2, "buy_submitted": 53, "date": "2026-06-06", "generated_at": "2026-06-06T01:45:48Z", "rank_calendar_days": 6, "rank_gate_ready": false, "skip_ai_score": 18, "skip_llm_block": 15, "skip_rank_gate": 67}
diff --git a/logs/paper_validation/latest_summary.json b/logs/paper_validation/latest_summary.json
index 4e4306b..d0974d5 100644
--- a/logs/paper_validation/latest_summary.json
+++ b/logs/paper_validation/latest_summary.json
@@ -1,21 +1,21 @@
 {
-  "generated_at": "2026-06-02T09:05:51Z",
+  "generated_at": "2026-06-06T01:45:48Z",
   "lookback_days": 90,
   "llm_advisory_only": false,
   "rank_ai_buy_gate_enabled": true,
   "llm_ai_agreement": {
-    "generated_at": "2026-06-02T09:05:51Z",
+    "generated_at": "2026-06-06T01:45:48Z",
     "ai_score_buy_threshold": 0.4,
     "llm_cache_path": "data/llm_cache.json",
-    "llm_cache_entries": 88,
-    "comparable_with_ai_score": 87,
-    "agreement_rate": 0.7471264367816092,
-    "agreement_pct": 74.7,
-    "score_llm_corr": 0.04115883088749699,
+    "llm_cache_entries": 108,
+    "comparable_with_ai_score": 107,
+    "agreement_rate": 0.6915887850467289,
+    "agreement_pct": 69.2,
+    "score_llm_corr": 0.10814771782075211,
     "confusion": {
-      "both_pass": 65,
+      "both_pass": 74,
       "both_fail": 0,
-      "ai_pass_llm_reject": 19,
+      "ai_pass_llm_reject": 30,
       "ai_fail_llm_pass": 3
     },
     "disagreements_sample": [
@@ -64,6 +64,15 @@
         "agree": false,
         "llm_category": "Guidance"
       },
+      {
+        "ticker": "PLD",
+        "date": "2026-06-03",
+        "ai_score": 0.6634,
+        "ai_ok": true,
+        "llm_ok": false,
+        "agree": false,
+        "llm_category": "Guidance"
+      },
       {
         "ticker": "META",
         "date": "2026-06-02",
@@ -91,6 +100,15 @@
         "agree": false,
         "llm_category": "None, Lawsuit, Fraud, Guidance, Financials, Other"
       },
+      {
+        "ticker": "XLE",
+        "date": "2026-06-03",
+        "ai_score": 0.6165,
+        "ai_ok": true,
+        "llm_ok": false,
+        "agree": false,
+        "llm_category": "Other"
+      },
       {
         "ticker": "PATH",
         "date": "2026-06-01",
@@ -100,6 +118,15 @@
         "agree": false,
         "llm_category": "**Guidance** (or Financials, but 'Weak earnings' usually implies guidance in market terms) or **Other** (Sentiment). However, \"Weak earnings\" often translates to poor forward guidance. Let's go with *"
       },
+      {
+        "ticker": "DIS",
+        "date": "2026-06-04",
+        "ai_score": 0.6121,
+        "ai_ok": true,
+        "llm_ok": false,
+        "agree": false,
+        "llm_category": "Financials"
+      },
       {
         "ticker": "SMCI",
         "date": "2026-06-01",
@@ -128,27 +155,27 @@
         "llm_category": "Financials"
       },
       {
-        "ticker": "PLD",
-        "date": "2026-06-02",
-        "ai_score": 0.588,
+        "ticker": "PLTR",
+        "date": "2026-06-03",
+        "ai_score": 0.591,
         "ai_ok": true,
         "llm_ok": false,
         "agree": false,
-        "llm_category": "Guidance"
+        "llm_category": "Lawsuit"
       },
       {
-        "ticker": "ORCL",
-        "date": "2026-06-01",
-        "ai_score": 0.5217,
+        "ticker": "PLD",
+        "date": "2026-06-02",
+        "ai_score": 0.588,
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
+        "date": "2026-06-04",
+        "ai_score": 0.5837,
         "ai_ok": true,
         "llm_ok": false,
         "agree": false,
@@ -156,48 +183,21 @@
       },
       {
         "ticker": "VZ",
-        "date": "2026-06-02",
-        "ai_score": 0.4855,
+        "date": "2026-06-03",
+        "ai_score": 0.5785,
         "ai_ok": true,
         "llm_ok": false,
         "agree": false,
         "llm_category": "Guidance"
       },
-      {
-        "ticker": "AAL",
-        "date": "2026-06-01",
-        "ai_score": 0.4848,
-        "ai_ok": true,
-        "llm_ok": false,
-        "agree": false,
-        "llm_category": "Guidance (as the company is warning about future costs) or Financials. \"Guidance\" fits best as it is a warning about future performance/costs."
-      },
-      {
-        "ticker": "AMT",
-        "date": "2026-06-01",
-        "ai_score": 0.3332,
-        "ai_ok": false,
-        "llm_ok": true,
-        "agree": false,
-        "llm_category": "None, Lawsuit, Fraud, Guidance, Financials, Other"
-      },
       {
         "ticker": "SBUX",
-        "date": "2026-06-01",
-        "ai_score": 0.4612,
+        "date": "2026-06-04",
+        "ai_score": 0.5298,
         "ai_ok": true,
         "llm_ok": false,
         "agree": false,
-        "llm_category": "Financials"
-      },
-      {
-        "ticker": "SNAP",
-        "date": "2026-06-01",
-        "ai_score": 0.4529,
-        "ai_ok": true,
-        "llm_ok": false,
-        "agree": false,
-        "llm_category": "Lawsuit"
+        "llm_category": "Other"
       }
     ],
     "llm_advisory_audit_rows": 53,
@@ -207,69 +207,28 @@
     ],
     "candidate_buy": {
       "path": "logs/candidate_cache/latest_buy.csv",
-      "as_of_date": "2026-06-02",
-      "buy_signal_rows": 47,
-      "in_llm_cache": 8,
-      "agreement_rate": 0.375,
+      "as_of_date": "2026-06-06",
+      "buy_signal_rows": 74,
+      "in_llm_cache": 0,
+      "agreement_rate": null,
       "confusion": {
-        "both_pass": 3,
+        "both_pass": 0,
         "both_fail": 0,
-        "ai_pass_llm_reject": 5,
+        "ai_pass_llm_reject": 0,
         "ai_fail_llm_pass": 0
       },
-      "disagreements": [
-        {
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
-          "ai_ok": true,
-          "llm_ok": false,
-          "agree": false,
-          "in_llm_cache": true
-        }
-      ]
+      "disagreements": []
     }
   },
   "llm_advisory_impact": {
-    "generated_at": "2026-06-02T09:05:51Z",
+    "generated_at": "2026-06-06T01:45:48Z",
     "audit_path": "logs/execution_audit.csv",
     "lookback_days": 90,
-    "rows": 4486,
+    "rows": 6055,
     "advisory_would_reject": 53,
-    "buy_submitted": 44,
+    "buy_submitted": 53,
     "buy_submitted_despite_llm_reject": 0,
-    "buy_blocked_by_llm": 14,
+    "buy_blocked_by_llm": 15,
     "sample_would_reject": [
       {
         "timestamp": "2026-06-01T12:32:18",
@@ -292,6 +251,16 @@
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
         "llm_side": "REJECT"
       },
       {
@@ -315,6 +284,16 @@
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
         "llm_side": "REJECT"
       },
       {
@@ -338,6 +317,16 @@
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
         "llm_side": "REJECT"
       },
       {
@@ -361,6 +350,16 @@
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
         "llm_side": "REJECT"
       },
       {
@@ -384,6 +383,16 @@
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
         "llm_side": "REJECT"
       },
       {
@@ -407,6 +416,16 @@
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
         "llm_side": "REJECT"
       },
       {
@@ -430,6 +449,16 @@
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
         "llm_side": "REJECT"
       },
       {
@@ -453,6 +482,16 @@
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
         "llm_side": "REJECT"
       },
       {
@@ -476,6 +515,16 @@
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
         "llm_side": "REJECT"
       },
       {
@@ -499,6 +548,16 @@
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
         "llm_side": "REJECT"
       }
     ],
@@ -509,39 +568,39 @@
     ]
   },
   "audit_buy_paths": {
-    "rows": 4486,
+    "rows": 6055,
     "llm_advisory_only": false,
     "ai_score_buy_threshold": 0.4,
-    "skip_buy_total": 4043,
+    "skip_buy_total": 5539,
     "skip_by_layer": {
-      "other": 3964,
+      "other": 5439,
       "ai_score": 18,
-      "llm_block": 14,
-      "rank_gate": 47
+      "llm_block": 15,
+      "rank_gate": 67
     },
     "skip_ai_score_layer": 18,
-    "skip_llm_block_layer": 14,
-    "skip_rank_gate_layer": 47,
+    "skip_llm_block_layer": 15,
+    "skip_rank_gate_layer": 67,
     "skip_rank_missing_layer": 0,
-    "skip_other_layer": 3964,
-    "ai_pass_llm_block": 14,
-    "ai_fail_or_low_score": 387,
-    "buy_submitted": 44,
-    "buy_submitted_llm_accept": 36,
+    "skip_other_layer": 5439,
+    "ai_pass_llm_block": 15,
+    "ai_fail_or_low_score": 453,
+    "buy_submitted": 53,
+    "buy_submitted_llm_accept": 40,
     "buy_submitted_llm_reject_verdict": 0,
-    "buy_submitted_no_llm_verdict": 8,
+    "buy_submitted_no_llm_verdict": 13,
     "llm_advisory_would_reject_ai_passed": 53,
     "interpretation": "Blocking mode (llm_advisory_only=false): ai_pass_llm_block counts SKIP_BUY where AI score passed but LLM blocked. submitted_llm_reject_verdict should be ~0."
   },
   "rank_gate_paper_tracker": {
     "min_calendar_days_required": 14,
-    "calendar_days_with_rank_events": 4,
-    "audit_span_calendar_days": 7,
+    "calendar_days_with_rank_events": 6,
+    "audit_span_calendar_days": 11,
     "first_date": "2026-05-27",
-    "last_date": "2026-06-02",
-    "total_skip_buy_rank_blocked": 47,
+    "last_date": "2026-06-06",
+    "total_skip_buy_rank_blocked": 67,
     "total_skip_buy_rank_missing": 0,
-    "total_buy_submitted": 44,
+    "total_buy_submitted": 53,
     "gate_ready": false,
     "daily_tail": [
       {
@@ -586,11 +645,43 @@
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
       }
     ],
     "notes": [
diff --git a/logs/paper_validation/trend_summary.json b/logs/paper_validation/trend_summary.json
index fbcb41f..b945053 100644
--- a/logs/paper_validation/trend_summary.json
+++ b/logs/paper_validation/trend_summary.json
@@ -1,24 +1,24 @@
 {
-  "generated_at": "2026-06-02T09:16:13Z",
+  "generated_at": "2026-06-06T01:45:47Z",
   "history_path": "logs/paper_validation/history.jsonl",
-  "rows": 1,
+  "rows": 5,
   "rolling_days": 7,
   "latest": {
-    "date": "2026-06-02",
-    "agreement_pct": 74.7,
+    "date": "2026-06-06",
+    "agreement_pct": 69.2,
     "skip_ai_score": 18,
-    "skip_llm_block": 14,
-    "skip_rank_gate": 47,
-    "buy_submitted": 44,
-    "rank_calendar_days": 4,
+    "skip_llm_block": 15,
+    "skip_rank_gate": 67,
+    "buy_submitted": 53,
+    "rank_calendar_days": 6,
     "rank_gate_ready": false
   },
   "rolling": {
-    "agreement_pct_mean": 74.7,
+    "agreement_pct_mean": 71.4,
     "skip_ai_score_mean": 18.0,
-    "skip_llm_block_mean": 14.0,
-    "skip_rank_gate_mean": 47.0,
-    "buy_submitted_mean": 44.0
+    "skip_llm_block_mean": 14.6,
+    "skip_rank_gate_mean": 59.0,
+    "buy_submitted_mean": 47.4
   },
   "alerts": [],
   "tail": [
@@ -29,6 +29,38 @@
       "skip_rank_gate": 47,
       "buy_submitted": 44,
       "rank_gate_ready": false
+    },
+    {
+      "date": "2026-06-03",
+      "agreement_pct": 74.7,
+      "skip_llm_block": 14,
+      "skip_rank_gate": 47,
+      "buy_submitted": 44,
+      "rank_gate_ready": false
+    },
+    {
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
     }
   ]
 }
\ No newline at end of file
diff --git a/tests/test_execution_resilience.py b/tests/test_execution_resilience.py
index ba555d1..d739d70 100644
--- a/tests/test_execution_resilience.py
+++ b/tests/test_execution_resilience.py
@@ -3,6 +3,7 @@ from unittest.mock import patch, MagicMock
 from types import SimpleNamespace
 from src.alpaca_client import submit_market_buy_notional_order, close_position_by_symbol
 from src.llm_analyst import evaluate_ticker_consensus
+from src.settings import StrategySettings
 import json
 from pathlib import Path
 
@@ -169,7 +170,7 @@ class TestExecutionResilience(unittest.TestCase):
              patch("src.main.load_settings") as mock_settings:
             
             mock_args.return_value = Namespace(execute=True)
-            mock_settings.return_value = SimpleNamespace(
+            mock_settings.return_value = StrategySettings(
                 tickers=["AAPL"],
                 broker_provider="alpaca",
                 dynamic_universe_enabled=False,
```
