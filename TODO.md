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
| **Rank AI (paper)** | buy/add gate ON · **4/14일** rank 이벤트 (`gate_ready=false`) · 일일 timer **active** (다음: 21:45 ET) |
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
