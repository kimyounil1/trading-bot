# Agent Review Packet - Run: phase30

## Implementation Agent
cursor

## Task Description
Pass phase30: Cursor implementation + AGY tests complete. Request Codex review.

## Changed Files
- .gitignore
- TODO.md
- config/strategy_config.json
- docs/TODO_ARCHIVE.md
- docs/runbook.md
- logs/portfolio_backtest/portfolio_summary.csv

## Git Diff Summary
```
 .gitignore                                    | 16 +++++++++
 TODO.md                                       | 48 +++++++++------------------
 config/strategy_config.json                   |  3 +-
 docs/TODO_ARCHIVE.md                          |  2 ++
 docs/runbook.md                               | 15 +++++++++
 logs/portfolio_backtest/portfolio_summary.csv |  2 +-
 6 files changed, 52 insertions(+), 34 deletions(-)
```

## Test Execution Results (runtime_harness.log)
```
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.0.3, pluggy-1.6.0
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
======================== 45 passed, 1 warning in 2.44s =========================
```

## Git Patch
```diff
diff --git a/.gitignore b/.gitignore
index c4cf60c..bd00ba7 100644
--- a/.gitignore
+++ b/.gitignore
@@ -1,4 +1,5 @@
 .env
+.antigravitycli/
 .venv/
 __pycache__/
 *.pyc
@@ -29,6 +30,21 @@ logs/*
 !logs/allocation_compare/*/*summary*.csv
 !logs/portfolio_backtest/
 !logs/portfolio_backtest/*summary*.csv
+!logs/benchmark_gap/
+!logs/benchmark_gap/latest_summary.json
+!logs/operational_alpha/
+!logs/operational_alpha/latest_summary.json
+!logs/llm_cache_warmup/
+!logs/llm_cache_warmup/latest_summary.json
+!logs/llm_advisory/
+!logs/llm_advisory/latest_summary.json
+!logs/guard_impact/
+!logs/guard_impact/latest_summary.json
+!logs/crowding_paper/
+!logs/crowding_paper/go_no_go_checklist.json
+
+# Pytest regenerates these from golden_execution_audit.csv
+tests/fixtures/audit_daily/golden_output/
 
 # Champion model binaries are local-only (retrain + promotion); never commit ad-hoc retrains.
 models/*
diff --git a/TODO.md b/TODO.md
index 607f3e6..70e5dd2 100644
--- a/TODO.md
+++ b/TODO.md
@@ -3,14 +3,9 @@
 ## Definition of Done (완료 기준)
 항목을 `[x]`로 두려면 다음을 **모두** 충족:
 1. **코드** — 요구사항 반영, 프로젝트 스타일 준수
-2. **테스트** — 관련 pytest 추가·통과 (기본: `run_pass_complete.sh` subset 또는 명시한 경로)
+2. **테스트** — 관련 pytest 추가·통과
 3. **운영** — 필요 시 백테스트/리포트·runbook 반영
-4. **리뷰** — pytest 필수; **Codex는 고위험·Phase 마감 시만** ([`docs/codex_review_policy.md`](docs/codex_review_policy.md)):
-
-```bash
-RUN_ID=<pass_id> SKIP_CODEX=1 bash scripts/run_pass_complete.sh
-RUN_ID=phase29_final bash scripts/run_pass_complete.sh "Phase 29 alpha"
-```
+4. **리뷰** — `RUN_ID=<pass> SKIP_CODEX=1 bash scripts/run_pass_complete.sh` ([`docs/codex_review_policy.md`](docs/codex_review_policy.md))
 
 ---
 
@@ -18,10 +13,8 @@ RUN_ID=phase29_final bash scripts/run_pass_complete.sh "Phase 29 alpha"
 
 | 문서 | 역할 |
 |------|------|
-| **`TODO.md`** | 활성 로드맵 |
-| **`docs/TODO_ARCHIVE.md`** | Phase 0–28 + 백로그 요약 |
-
-**루프:** Cursor 구현 → `[AGY]` 테스트 → `SKIP_CODEX=1` pytest → Codex (마감) → 반영.
+| **`TODO.md`** | 활성 로드맵 (다음 Phase만) |
+| **`docs/TODO_ARCHIVE.md`** | Phase 0–29 요약 |
 
 ---
 
@@ -29,37 +22,28 @@ RUN_ID=phase29_final bash scripts/run_pass_complete.sh "Phase 29 alpha"
 
 | 영역 | 상태 |
 |------|------|
-| **알파 목표** | 승격 시 **벤치마크 이상** 필수 (`promotion_portfolio_thresholds`, excess ≥ 0 pp) |
-| **랭킹** | `rank_ai_weight=1.0`, `rank_trend_weight=0.5`, RS 필터 ON |
-| **포트폴리오 백테스트** | **+96.8%** vs equal-weight B&H **+65.0%** (gap **+31.8pp**), MDD **-7.3%**, Sharpe **3.15** |
-| **챔피언** | LGBM+XGB; retrain은 PROMOTE 게이트 통과 시만 교체 |
+| **ML 백테스트** | **+96.8%** vs B&H **+65.0%** (gap +31.8pp), `beats_benchmark` |
+| **LLM** | `llm_advisory_only: true` — 주문 차단 없음, audit만 |
+| **Crowding** | `crowding_guard_enabled: false` — paper gate **NO_GO** (Sharpe Δ) |
+| **챔피언** | 로컬 `models/`; 승격 시 벤치 이상 필수 |
 
-**완료:** Phase 0–28, 백로그 → [`docs/TODO_ARCHIVE.md`](docs/TODO_ARCHIVE.md)
+**Phase 29 완료** → [`docs/TODO_ARCHIVE.md`](docs/TODO_ARCHIVE.md)
 
 ---
 
-## Phase 29 — Beat benchmark (알파) ← **진행 중**
+## Phase 30 — Paper ops (유지보수)
 
-- [x] `[Cursor]` 승격 OOS: `min_return_vs_benchmark=0`, `min_sharpe=1.0` (`src/promotion_thresholds.py`)
-- [x] `[Cursor]` `config/strategy_config.json` — AI 랭킹·RS 필터로 후보 품질 상향
-- [x] `[Cursor]` `benchmark_gap` 리포트 — `beats_benchmark`, `recommendations`
-- [x] `[AGY]` `tests/test_promotion_beat_benchmark.py`
-- [x] `[Cursor]` equal-weight 벤치마크 NaN 버그 수정 (`_build_equal_weight_benchmark_values`)
-- [x] `[Cursor]` `run_portfolio_backtest` ↔ config 정합 (`portfolio_backtest_settings.py`, 손절/익절 전달)
-- [x] `[Cursor]` `volume_filter_enabled=false`, `max_position_pct=0.11`, AI·RS 랭킹 유지
-- [x] `[AGY]` `bash scripts/run_alpha_pipeline.sh` — **+96.8% vs bench +65.0%** (`beats_benchmark=true`, gap +31.8pp)
-- [x] `[AGY]` LLM/뉴스 필터 impact — `python -m src.llm_backtest_impact_report` (`run_alpha_pipeline` 포함)
-- [x] `[Cursor]` in-loop 운영 검증 — `bash scripts/run_operational_alpha_validation.sh` (baseline vs LLM+news)
-- [x] `[Cursor]` 백테스트 진입 141키 `data/llm_cache.json` 워밍업 (`scripts/warm_llm_cache_from_backtest.sh`)
-- [ ] `[Cursor]` paper `main.py`로 캐시·`execution_audit.csv` 운영 중 갱신
-- [ ] `[Cursor]` 벤치 초과 유지 시 paper `crowding_guard_enabled` 점진 활성화 검토
+- [ ] 주기: `bash scripts/run_paper_ops_bootstrap.sh` (dry-run + 리포트)
+- [ ] paper에서 `execution_audit`·`data/llm_cache.json` 누적 후 `run_llm_advisory_report.sh`로 따름/무시 비교
+- [ ] Crowding: `bash scripts/run_crowding_paper_gate.sh` 재실행 후 **GO**일 때만 `config/crowding_paper_proposal.json` 값을 `strategy_config`에 반영
 
 ---
 
 ## Quick commands
 
 ```bash
+bash scripts/run_paper_ops_bootstrap.sh
 bash scripts/run_alpha_pipeline.sh
-bash scripts/run_ops_reports.sh --weekly
-RUN_ID=phase29 SKIP_CODEX=1 bash scripts/run_pass_complete.sh
+bash scripts/warm_llm_cache_from_backtest.sh   # 선택: 캐시 재충전
+RUN_ID=phase30 SKIP_CODEX=1 bash scripts/run_pass_complete.sh
 ```
diff --git a/config/strategy_config.json b/config/strategy_config.json
index 5ae7ecc..050ed83 100644
--- a/config/strategy_config.json
+++ b/config/strategy_config.json
@@ -168,5 +168,6 @@
   "margin_leverage_stress_gate_required": true,
   "trailing_stop_pct": 0.05,
   "rebalance_threshold_pct": 0.20,
-  "sector_rotation_enabled": true
+  "sector_rotation_enabled": true,
+  "crowding_guard_enabled": false
 }
diff --git a/docs/TODO_ARCHIVE.md b/docs/TODO_ARCHIVE.md
index 0893900..63d0699 100644
--- a/docs/TODO_ARCHIVE.md
+++ b/docs/TODO_ARCHIVE.md
@@ -27,6 +27,7 @@
 | 26 | Live alignment (paper) | Crowding go/no-go, execution vs slippage diff, leverage/LLM cache alerts |
 | 27 | Universe + instrument meta | Master CSV, UNIVERSE_PROFILE, leveraged ETF registry and buy gates |
 | 28 | Margin leverage paper | Stress go/no-go gate, proposal caps, main buy block |
+| 29 | Beat benchmark (alpha) | Promotion ≥ bench, EW benchmark fix, alpha/operational pipelines, LLM advisory-only, cache warmup |
 
 **Milestones**
 - **2026-05-27:** Phase 0–19 closed (code + pytest + runbook).
@@ -36,3 +37,4 @@
 - **2026-05-30:** Phase 26 closed; paper crowding gate, execution alignment, stress/cache Telegram alerts.
 - **2026-05-30:** Phase 27 closed; universe master/smoke/research profiles, instrument registry, leverage ETF gates.
 - **2026-05-30:** Phase 28 closed; margin leverage paper gate wired to leverage stress + main.
+- **2026-05-31:** Phase 29 closed; +96.8% vs B&H +65%, LLM advisory (no block), crowding paper gate NO_GO.
diff --git a/docs/runbook.md b/docs/runbook.md
index 10b7eea..61d7e2e 100644
--- a/docs/runbook.md
+++ b/docs/runbook.md
@@ -83,6 +83,21 @@ LIVE_LLM=1 bash scripts/run_operational_alpha_validation.sh   # cache miss 시 G
 산출물: `data/llm_cache.json`, `logs/llm_cache_warmup/latest_summary.json`, `logs/operational_alpha/latest_summary.json`  
 워밍업은 진입일 키(`{티커}_{YYYY-MM-DD}`)로 저장. 당일 yfinance에 기사가 없으면 **현재 헤드라인 fallback**으로 Gemini 호출(완전한 과거 뉴스 아카이브는 아님). paper `main.py` 실행 시 같은 키로 캐시가 계속 쌓임.
 
+```bash
+bash scripts/run_paper_ops_bootstrap.sh   # dry-run + advisory + alpha + operational summaries
+```
+
+### 2.3.2 Crowding guard (paper)
+
+`strategy_config.json` 기본: **`crowding_guard_enabled: false`**. Paper 실험 값은 `config/crowding_paper_proposal.json`만.
+
+```bash
+bash scripts/run_guard_impact_report.sh
+bash scripts/run_crowding_paper_gate.sh   # writes logs/crowding_paper/go_no_go_checklist.json
+```
+
+2026-05-31 gate 결과: **NO_GO** (Sharpe delta below floor). **GO** 전까지 prod config에 crowding 켜지 않음.
+
 ### 2.4 유니버스 프로필 (`UNIVERSE_PROFILE`)
 
 | 프로필 | 스캔 풀 | 용도 |
diff --git a/logs/portfolio_backtest/portfolio_summary.csv b/logs/portfolio_backtest/portfolio_summary.csv
index fcc8c9b..840ffc9 100644
--- a/logs/portfolio_backtest/portfolio_summary.csv
+++ b/logs/portfolio_backtest/portfolio_summary.csv
@@ -1,2 +1,2 @@
 initial_cash,final_equity,total_return,benchmark_return,max_drawdown,sharpe_ratio,trades,win_rate
-10000.0,15072.372552764085,0.5072372552764086,0.5823625689672778,-0.10211053509473034,1.5211408575289322,42,0.5714285714285714
+10000.0,19681.309045199054,0.9681309045199054,0.6504853238288733,-0.0731374832818028,3.1519064349744568,141,0.6028368794326241
```
