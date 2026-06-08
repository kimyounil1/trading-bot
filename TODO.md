# TODO

## Definition of Done (완료 기준)
항목을 `[x]`로 두려면 다음을 **모두** 충족:
1. **코드** — 요구사항 반영, 프로젝트 스타일 준수
2. **테스트** — 관련 pytest 추가·통과
3. **운영** — 필요 시 백테스트/리포트·runbook 반영
4. **리뷰** — `RUN_ID=<phase> bash scripts/run_pass_complete.sh` ([`docs/codex_review_policy.md`](docs/codex_review_policy.md))

---

## Who owns what

| 문서 | 역할 |
|------|------|
| **`TODO.md`** | 활성 로드맵 (지금 할 일만) |
| **`docs/TODO_ARCHIVE.md`** | Phase 0–31 요약 |

---

## Current Status (2026-06-02)

| 영역 | 상태 |
|------|------|
| **Alpha** | trailing 20% · 전략 **+76.1%** vs EW **+67.1%** (gap **+9.0pp**) · SPY **+28.9pp** (`logs/benchmark_gap/latest_summary.json`) |
| **Crowding** | config **ON** · 최근 paper gate run **NO_GO** (blocked_trades=0) — impact 재평가 시 `run_guard_impact_report.sh` |
| **Paper ops** | `logs/paper_ops/latest_summary.json` · audit ~18k rows |
| **LLM (paper)** | blocking mode (`llm_advisory_only: false`) · 캐시 일치 ~**75%** |
| **Rank AI (paper)** | buy/add gate ON · **6/14일** rank 이벤트 (`gate_ready=false`) · 일일 timer **active** |
| **Champion AI** | **유지** — promotion gate 실패 (AUC/Brier/fold/OOS). Rank label research만 paper gate |

**Phase 31** → [`docs/TODO_ARCHIVE.md`](docs/TODO_ARCHIVE.md)

---

## Active — Phase 32 (남은 작업만)

우선순위 순. **Toss(32-A)는 API 키 전까지 보류.**

1. [ ] **Rank AI paper 2주** — 매일 dry-run/bootstrap → `logs/paper_validation` · `rank_gate_ready=true` (현재 **4/14** calendar days)
2. [ ] **Paper validation 추세** — 2주+ `agreement_pct` · SKIP(AI/LLM/rank) 레이어 관찰 (`bash scripts/run_paper_buy_validation.sh` → `logs/paper_validation/history.jsonl` 일별 upsert)
3. [x] **Codex scoped review** — `RUN_ID=phase32_retry` 완료 (`NEXT_TODO.codex.md`: `history.jsonl` gitignore whitelist 반영함)

**하지 말 것 (문서: [`docs/ai_authority_gates.md`](docs/ai_authority_gates.md))**
- `models/ai_score_model.joblib` 교체 / champion 승격 (label sweep 전 후보 portfolio gate 실패)
- Rank gate **live** 기본 ON (Tier-1 paper 2주 전)

---

## Phase 33 — 고도화 (backlog)

검증·신뢰도 우선. **모델 교체/live 권한 확대는 paper 근거가 쌓인 뒤**에만. DoD는 상단 기준 따름.

### A. 신호 검증 (먼저 — 근거 없이는 권한 확대 금지)
1. [x] **Rank gate forward-return 귀속** — rank-blocked vs rank-passed 후보의 20일 forward return 분포 비교.
   - 신규: `src/rank_gate_forward_return.py` (audit `rank_ai_score`/`rank_ai_percentile` + `data/raw` 종가 조인)
   - 산출: `logs/rank_ai_gate/forward_return.json` (blocked mean/median, passed mean/median, hit-rate, n)
   - 목적: 게이트가 "거른 게 실제로 못했나"를 수치로 — Tier-1 승인 근거
   - 현재 상태: 90d 실행 결과 usable 표본 0건(`other=47`) → 다음 2주 누적 후 재평가
2. [x] **LLM block precision** — LLM이 REJECT한 매수의 forward return이 ACCEPT 대비 낮은지 측정.
   - `score_llm_corr≈0.04` (무상관) → LLM이 alpha를 더하는지/노이즈인지 판정
   - 산출: `logs/llm_advisory/precision.json` (reject hit-rate, avg fwd return Δ)
   - 현재 상태: 90d 실행에서 parsed ACCEPT/REJECT 표본 부족 시 n=0 가능 → 누적 관찰 필요
3. [x] **Paper validation 추세 리포트** — `history.jsonl` 위에 rolling(7d) agreement·SKIP율·회귀 감지.
   - 신규: `src/paper_validation_trend.py` → `logs/paper_validation/trend_summary.json`
   - `rank_gate_ready` flip / agreement 급락 / llm_block spike alert 키 생성
   - 현재 상태: history 누적 1일이라 rolling 해석은 제한적(관측 지속 필요)

### B. 모델 품질 (champion 교체 아님 — overlay 개선)
4. [x] **ai_score 캘리브레이션 overlay** — Brier 열위 → isotonic/Platt 후처리로 conviction sizing 신뢰도↑.
   - champion joblib 미변경, 예측 후처리 레이어만. `logs/ml/model_calibration_report.json` 전후 비교
   - 현재 적용: `ai_score_calibration_enabled=true`일 때만 bin 기반 보정(기본 OFF, fail-open)
5. [x] **Regime별 약점 진단** — OOS AUC BULL 0.495 / NEUTRAL 0.48 (랜덤 이하) 원인 분석.
   - feature importance × regime, 후보 feature(섹터 상대강도·breadth) 실험 리포트만 (승격 X)
   - 신규: `src/regime_weakness_report.py` → `logs/ml/regime_weakness_report.json` (weak/high-variance regime 자동 플래그)

### C. 운영/리스크
6. [x] **Crowding gate 재평가** — 최근 NO_GO(blocked_trades=0). live impact로 keep/tune/disable 결정 후 문서화.
   - 신규: `src/crowding_gate_reassessment.py` → `logs/crowding_paper/reassessment.json`
   - 현재 상태: `NO_GO` + blocked_trades=0, recommendation=`DISABLE_OR_KEEP_OFF`
7. [x] **Daily scheduler 안정화** — `loginctl enable-linger $USER` (WSL/서버 로그아웃 후 timer 유지) + 실패 시 알림.
   - `scripts/run_daily_paper_ops.sh`: bootstrap 실패 시 Telegram `notify_error` 알림 추가
   - `scripts/check_paper_daily_timer.sh`: timer active/next + linger 상태 점검(`logs/paper_ops/scheduler_health.json`)

### Toss(32-A) — blocked
- [ ] Toss Open API adapter · CMS execute path (API 키 필요)

---

## Phase 34 — Live foundation (paper 14일·Toss API·live 전환 **대기 중** 병렬 작업)

**목표:** 수익률 실험보다 **운영·검증·확장성** — Rank/Toss/Live가 열렸을 때 바로 안전하게 붙일 바닥.
**전제:** Phase 32 관측(2주)·Tier-1 live·champion 승격은 **여전히 금지** ([`docs/ai_authority_gates.md`](docs/ai_authority_gates.md)).

**이미 있음 (중복 작업 금지):** `src/broker_adapter.py` — submit buy/sell + Toss stub. `main.py`·CMS는 여전히 `alpaca_client` 직접 호출.

**Phase 34에 넣지 않음 (이유):**
- Toss **실 API** 구현 — API 키·스펙 대기 (stub·readiness 차단만)
- Champion 승격 / rank **live** 기본 ON — paper 근거 후
- DL/RL live (`docs/RESEARCH_MODELS.md`)
- 대규모 `main.py` 일괄 리팩터 한 방 — Sprint별 점진 이전

### Sprint 1 — Broker + safety
1. [x] **Broker adapter v2** — `src/brokers/` + account/positions/orders/cancel; `main`·`candidate_cache`·CMS·CLI·dust sell adapter 경유
2. [x] **FakeBroker** — `PaperBrokerAdapter` (`broker_provider=paper`); `tests/test_paper_broker.py`
3. [x] **LiveSafetyGuard** — `src/risk/live_safety.py`; kill switch 항상·limits는 `live_safety_enabled`; `main` BUY 전 검사

### Sprint 2 — Config + readiness
4. [x] **Paper / live / research 프로필 + schema** — `config/profiles/` + `config/schema/trading_config.schema.json`; `validate_trading_config` on `main` startup
5. [x] **Live deploy guard** — `TRADING_ENV=live` + `CONFIRM_LIVE_TRADING=YES_I_UNDERSTAND` or `ALLOW_LIVE_TRADING=true` before `--execute`
6. [x] **LiveReadinessGate** — `bash scripts/run_live_readiness.sh` → `logs/live_readiness/latest_summary.json`; live `--execute` requires `safe_to_execute_live`

### Sprint 3 — Execution traceability
7. [x] **OrderIntent 레이어 (점진)** — `src/order_intent.py`; BUY path + `AuditContext`; full main migration follow-up
8. [x] **Execution audit v2** — extended `EXECUTION_AUDIT_COLUMNS` + `logger.log_execution_audit` v2 fields
9. [x] **Data health check** — `bash scripts/run_data_health_check.sh` → `logs/data_health/latest_summary.json`

### Sprint 4 — Operator UX (paper 기간에도 유용)
10. [x] **CMS operator view** — overview: live readiness, scheduler, candidates, blocked audit tail

**Codex:** Phase 34 슬라이스마다 1회 (`RUN_ID=phase34_<slice>`). Sprint 1 완료 후 FakeBroker E2E(duplicate `client_order_id`·kill switch·daily loss·broker fail-safe)는 Sprint 1 DoD에 포함.

---

## Phase 35 — Follow-up (병렬)

1. [x] **Dust guard parity** — `meaningful_open_symbols` / cache `positions_count` dust 제외
2. [x] **FakeBroker order-path tests** — `tests/test_broker_order_path.py`
3. [x] **Bootstrap wiring** — data health + live readiness in `run_paper_ops_bootstrap.sh`
4. [x] **`load_settings` profile merge** — environment overlay 자동 적용
5. [x] **Audit v2 full migration** — all SKIP/SELL paths via `_audit_log`
6. [x] **Codex pass** — `RUN_ID=phase34_followup bash scripts/run_pass_complete.sh`
7. [x] **Alpaca order board** — CMS extended-hours paths via adapter (optional)

---

## Phase 36 — Portfolio sleeves & alpha-seeking model track

**목표:** 계좌 전체를 단일 전략이 점유하지 않고, 사용자가 비중을 정해 `core / tournament / cash` 슬리브로 나눠 운용한다. 기존 안정형 전략은 유지하되, AYC·AI trading competition류의 고수익 모델은 별도 `tournament_paper` 슬리브에서만 검증한다.

**핵심 원칙**

* 기본값은 보수적으로 `core=50%`, `tournament=30%`, `cash=20%`.
* 사용자는 CMS 또는 config에서 슬리브 비중을 조정할 수 있어야 한다.
* `tournament` 슬리브는 paper 전용으로 시작하며, live 기본 ON 금지.
* 슬리브 간 현금·포지션·주문한도·성과를 분리해 audit한다.
* 전체 계좌 레벨의 kill switch, daily loss limit, max drawdown limit은 슬리브보다 우선한다.
* 기존 champion AI 교체와 Rank gate live 확대는 여전히 Phase 32/AI authority gate 조건을 따른다.

### A. Portfolio sleeve allocator

1. [x] **Sleeve config 추가** — `config/profiles/*.json` 및 schema에 슬리브 비중 추가.

   * 예시:

     ```json
     {
       "portfolio_sleeves_enabled": true,
       "sleeves": {
         "core": {
           "enabled": true,
           "target_weight": 0.50,
           "profile": "paper",
           "strategy": "current_core"
         },
         "tournament": {
           "enabled": true,
           "target_weight": 0.30,
           "profile": "tournament_paper",
           "strategy": "alpha_tournament",
           "paper_only": true
         },
         "cash": {
           "enabled": true,
           "target_weight": 0.20,
           "strategy": "cash_reserve"
         }
       }
     }
     ```
   * 검증:

     * enabled sleeve의 `target_weight` 합계는 1.0 이하여야 함.
     * `cash` 포함 합계가 1.0 미만이면 잔여 비중은 자동 cash로 간주.
     * `tournament.paper_only=true`이면 live execute에서 주문 제출 금지.
   * 테스트: `tests/test_portfolio_sleeve_config.py`

2. [x] **PortfolioSleeveAllocator 구현** — `src/portfolio_sleeves.py`

   * 입력: account, positions, open orders, settings
   * 출력:

     * `sleeve_target_notional`
     * `sleeve_current_notional`
     * `sleeve_available_cash`
     * `sleeve_order_budget`
     * `sleeve_rebalance_needed`
   * open order가 점유 중인 buying power를 슬리브별로 차감.
   * dust position은 기존 dust guard 기준과 일관되게 제외.
   * 테스트: `tests/test_portfolio_sleeves.py`

3. [x] **OrderIntent에 sleeve 필드 추가**

   * `sleeve_id`
   * `sleeve_strategy`
   * `sleeve_target_weight`
   * `sleeve_budget_before`
   * `sleeve_budget_after`
   * `sleeve_risk_mode`
   * 모든 BUY/SELL/SKIP audit에 sleeve 정보를 남긴다.
   * 테스트: `tests/test_order_intent_sleeves.py`

### B. Core / tournament / cash execution split

4. [x] **기존 방식은 core sleeve로 고정**

   * 현재 `main.py`의 기존 BUY 후보 생성·risk gate·rank gate 흐름은 `core` 슬리브에서 먼저 유지.
   * core는 기존 `paper/live/research` 프로필을 그대로 사용.
   * core 주문은 `core` 슬리브 예산을 초과할 수 없음.

5. [x] **Tournament paper profile 추가**

   * 신규 파일: `config/profiles/tournament_paper.json`
   * 목적: 21일 rolling 수익률을 높이는 공격형 paper 실험.
   * 기본 정책:

     * max positions: 3~7
     * top conviction 집중
     * 짧은 holding period
     * aggressive rank/AI threshold 실험 허용
     * LLM은 초기에 advisory only 또는 별도 실험 플래그
     * 전체 계좌 kill switch와 sleeve drawdown limit은 항상 적용
   * live에서는 `tournament_paper` 주문 제출 금지.
   * 테스트: `tests/test_tournament_profile_guard.py`

6. [x] **Cash sleeve 운영 방식 추가**

   * `cash` 슬리브는 신규 매수에 쓰지 않는 대기자금.
   * 사용자가 지정한 cash 비중은 core/tournament가 침범할 수 없음.
   * 단, 강제 청산/리스크 축소/수수료·잔고 오차 처리는 예외로 허용.
   * CMS에 현재 cash sleeve 비중과 사용 가능 현금 표시.
   * 테스트: `tests/test_cash_sleeve_guard.py`

### C. Alpha-seeking model plug-in track

7. [x] **Model registry 도입** — `src/model_registry.py`

   * 모델을 champion 하나로만 보지 않고, 전략 슬리브별 모델을 등록.
   * 예시:

     * `core_ai_score_model`
     * `rank_ai_gate_model`
     * `tournament_alpha_model`
     * `crypto_or_competition_model` 단, paper only
   * 모델별 metadata:

     * `model_id`
     * `model_type`
     * `trained_at`
     * `feature_set`
     * `allowed_sleeves`
     * `allowed_environments`
     * `promotion_status`
     * `paper_only`
   * 테스트: `tests/test_model_registry.py`

8. [x] **Tournament alpha model adapter**

   * 신규: `src/tournament_alpha_model.py`
   * 초기 버전은 기존 feature/rank output을 재활용해 고 conviction 후보를 더 집중 선택.
   * 이후 AYC·대회형 모델 구조를 실험할 수 있도록 adapter 인터페이스만 먼저 고정.
   * 출력:

     * `alpha_score`
     * `confidence`
     * `target_holding_days`
     * `max_position_pct`
     * `stop_policy`
     * `reason`
   * 테스트: `tests/test_tournament_alpha_model.py`

9. [x] **모델 권한 게이트 확장**

   * `docs/ai_authority_gates.md`에 sleeve별 권한 추가.
   * `tournament_alpha_model`은 초기 권한:

     * research: ON 가능
     * paper: ON 가능
     * live: OFF 고정
   * live 승격 조건:

     * 최소 30 calendar days paper
     * 21일 rolling return이 QQQ/MTUM/EW 중 최강 벤치 대비 우위
     * max drawdown 한도 통과
     * turnover와 slippage 반영 후에도 우위
     * Codex review 통과
   * 기존 champion 교체 조건과 분리해 관리.

### D. Sleeve-level reporting

10. [x] **Sleeve performance report**

* 신규: `src/sleeve_performance_report.py`
* 산출:

  * `logs/sleeves/latest_summary.json`
  * `logs/sleeves/history.jsonl`
* 필드:

  * sleeve별 NAV
  * sleeve별 return
  * sleeve별 benchmark return
  * sleeve별 excess return
  * sleeve별 max drawdown
  * sleeve별 turnover
  * sleeve별 win rate
  * sleeve별 open orders
  * sleeve별 blocked orders
* 테스트: `tests/test_sleeve_performance_report.py`

11. [x] **Tournament leaderboard report**

* 신규: `src/tournament_score_report.py`
* 산출:

  * `logs/tournament/latest_summary.json`
  * `logs/tournament/history.jsonl`
* 21일 rolling 기준:

  * tournament sleeve return
  * SPY return
  * QQQ return
  * MTUM return
  * EW universe return
  * best benchmark 대비 excess return
  * max drawdown
  * profit factor
  * turnover
* 목적: AYC/AI trading competition류 성과와 비교 가능한 내부 리더보드.
* 테스트: `tests/test_tournament_score_report.py`

12. [x] **CMS sleeve control panel**

* CMS에서 사용자가 슬리브 비중을 확인·수정할 수 있게 한다.
* 최소 표시:

  * core / tournament / cash target weight
  * current weight
  * drift
  * available budget
  * last 21d return
  * readiness status
* 안전장치:

  * tournament live enable 버튼 없음
  * cash weight를 0으로 낮추면 경고
  * target weight 합계가 100% 초과하면 저장 금지
* 테스트: CMS helper import + unit test

### E. Execution integration

13. [x] **main.py 주문 예산을 sleeve allocator 경유로 변경**

* 기존 `account["portfolio_value"]`, `cash`, `buying_power` 직접 사용을 점진적으로 줄이고, BUY 후보별 `sleeve_order_budget`을 사용.
* core 후보는 core budget만 사용.
* tournament 후보는 tournament budget만 사용.
* cash sleeve는 주문 후보를 만들지 않음.
* 테스트: `tests/test_sleeve_order_budget_integration.py`

14. [x] **Open order reconciliation에 sleeve 반영**

* open order가 어느 슬리브 예산을 점유하는지 추적.
* stale order가 있으면 해당 슬리브 신규 주문 차단.
* 전체 계좌 buying power와 sleeve budget 불일치 시 `NO_GO`.
* 테스트: `tests/test_sleeve_order_reconciliation.py`

15. [x] **Paper ops bootstrap에 sleeve 리포트 추가**

* `scripts/run_paper_ops_bootstrap.sh`에 아래 리포트 추가:

  * `run_sleeve_performance_report.sh`
  * `run_tournament_score_report.sh`
* CMS operator view에 latest summary 연결.
* 실패 시 Telegram notify_error.

### F. Definition of Done

16. [x] **Phase 36 Codex pass**

* `RUN_ID=phase36_sleeves bash scripts/run_pass_complete.sh`
* 필수 확인:

  * pytest green
  * config schema green
  * paper bootstrap green
  * `logs/sleeves/latest_summary.json` 생성
  * `logs/tournament/latest_summary.json` 생성
  * live readiness에서 tournament live 차단 확인

**하지 말 것**

* `tournament` 슬리브를 live 기본 ON 하지 말 것.
* champion 모델 교체와 sleeve 모델 추가를 혼동하지 말 것.
* core 전략의 기존 audit/리포트 호환성을 깨지 말 것.
* cash sleeve를 다른 슬리브가 임의로 침범하게 하지 말 것.
* 21일 수익률만 보고 live 승격하지 말 것. MDD, turnover, slippage, benchmark 대비 초과수익을 함께 봐야 함.

---

## Phase 37 — CMS sleeve UX + main.py trading pipeline split

**목표:** 슬리브는 CMS에서 저장·조작하고, `main.py`는 orchestration만 담당하도록 trading path를 모듈화한다.

### A. CMS sleeve control (done in branch)

1. [x] **대시보드 슬리브 저장** — Overview 패널에서 ON/OFF·비중·enabled 저장 → `strategy_config.json` + config history
2. [x] **`sleeve_runtime.py` 분리** — allocator init, pre-gate, trim, submit budget (`SleeveRunContext`)

### B. main.py pipeline split (next)

3. [x] **`src/trading/run_context.py`** — account, audit_ctx, regime, ticker_data, sleeve_ctx 한 묶음
4. [x] **`src/trading/buy_pipeline.py`** — 후보 scan → risk/guards → MVO → submit (sleeve budget 경유)
5. [x] **`src/trading/exit_pipeline.py`** — SELL, trailing stop, dust cleanup, rebalance trim
6. [x] **`main.py` slim** — parse args, load settings, `run_context` + exit + buy 순 호출 (61 lines)
7. [x] **회귀 테스트** — dry-run smoke + sleeve budget integration + 기존 broker path tests green (394 passed)

### C. Definition of Done

8. [ ] **Phase 37 Codex pass** — `RUN_ID=phase37_main_split bash scripts/run_pass_complete.sh`

**하지 말 것**

* buy/exit 동작 변경 없이 rename-only 리팩터 금지 — 테스트로 동작 동일성 확인
* CMS 슬리브 저장 시 tournament `paper_only` 우회 UI 추가 금지


## Phase 32 — shipped (요약)

코드·테스트·리포트 경로는 반영됨. 상세 실험 수치는 `logs/model_quality/`, `logs/ml/` 참고.

| 슬라이스 | 완료 내용 |
|----------|-----------|
| **32-B LLM** | `google.genai`, vLLM 폴백 |
| **32-C Crowding** | GO paper apply, live impact, bootstrap step |
| **32-D Paper** | LLM block, `llm_ai_agreement`, `paper_buy_validation`, CMS 카드, `universe_meta.json` race fix |
| **32-E Alpha** | trailing 20%, SPY 벤치, CMS alpha metrics |
| **32-F AI quality** | model_quality summary, calibration/label/rank experiments, rank **paper buy gate**, threshold/label sweep, dust P2, `execution_audit_io` |

**Rank research (paper only):** 20d/top15%/q85 OOS gate 통과 → `rank_ai_buy_gate_enabled` paper config. Champion absolute-label 승격은 **없음**.

---

## Quick commands

```bash
# 일일 paper (수동)
bash scripts/run_daily_paper_ops.sh

# 일일 paper (스케줄러 — 평일 21:45 ET)
bash scripts/install_paper_daily_timer.sh
systemctl --user enable --now trading-bot-daily-paper-ops.timer
systemctl --user list-timers trading-bot-daily-paper-ops.timer

# 리포트
bash scripts/run_model_quality_report.sh
bash scripts/run_rank_ai_gate_report.sh
REFRESH_CANDIDATE_CACHE=1 bash scripts/run_rank_ai_gate_report.sh
bash scripts/run_rank_gate_forward_return.sh
bash scripts/run_llm_block_precision.sh
bash scripts/run_paper_validation_trend.sh
bash scripts/run_regime_weakness_report.sh
bash scripts/run_crowding_gate_reassessment.sh
bash scripts/check_paper_daily_timer.sh
bash scripts/run_live_readiness.sh
bash scripts/run_data_health_check.sh

# 모델 실험 (무거움)
bash scripts/run_threshold_promotion_pipeline.sh
LABEL_SWEEP_ONLY=h20_t0p02 bash scripts/run_threshold_promotion_pipeline.sh

# AGY + Codex
AGY_TEST_PATHS="tests/test_paper_buy_validation_report.py tests/test_rank_ai_gate.py tests/test_execution_audit_io.py" \
  bash scripts/run_agy_slice.sh
RUN_ID=phase32_retry SKIP_PYTEST=1 bash scripts/run_pass_complete.sh

bash scripts/run_cms.sh
```
