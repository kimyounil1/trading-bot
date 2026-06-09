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

## Current Status (2026-06-09)

| 영역 | 상태 |
|------|------|
| **Alpha** | trailing 20% · 전략 **+76.1%** vs EW **+67.1%** (gap **+9.0pp**) · SPY **+28.9pp** (`logs/benchmark_gap/latest_summary.json`) |
| **Crowding** | config **ON** · reassessment `DISABLE_OR_KEEP_OFF` (blocked_trades=0) |
| **Paper ops** | daily timer active · `logs/paper_ops/latest_summary.json` |
| **LLM (paper)** | blocking mode · Gemini free-tier quota 이슈 간헐 (429) |
| **Rank AI (paper)** | buy/add gate ON · `rank_gate_ready` 아직 false — **2주 관측 진행 중** |
| **Champion AI** | **유지** — promotion gate 미통과. Rank label research만 paper gate |
| **Portfolio sleeves** | ON (core 50 / tournament 30 / cash 20) · registry + drift trim + **allocation rebalance** (Phase 39, 로컬) · `trading-bot` / `trading-bot-cms` 별도 서비스 |
| **Trading pipeline** | `main.py` orchestration · exit → sleeve_rebalance → buy (+ tournament) |

**Shipped (요약):** Phase 32 코드·Phase 33 검증·Phase 34–38 broker/sleeves — 상세는 아래 **Shipped** 절.

---

## Active — 지금 할 일

우선순위 순.

### 1. Phase 32 — Rank AI paper 관측 (남은 핵심)

**Toss(32-A)는 API 키 전까지 보류.**

| # | 항목 | 상태 |
|---|------|------|
| 1 | **Rank AI paper 2주** — 매일 bootstrap → `logs/paper_validation` · `rank_gate_ready=true` | [ ] 진행 중 (~4/14 calendar days) |
| 2 | **Paper validation 추세** — rolling agreement · SKIP 레이어 관찰 (`run_paper_buy_validation.sh`) | [ ] |
| 3 | Codex scoped review `phase32_retry` | [x] |

**하지 말 것** ([`docs/ai_authority_gates.md`](docs/ai_authority_gates.md))

- `models/ai_score_model.joblib` champion 교체
- Rank gate **live** 기본 ON (Tier-1 paper 2주 전)

---

### 2. Phase 39 — Sleeve allocation rebalance

**목표:** 슬리브 ON 시 보유 포지션·registry·trim이 **target weight에 맞게** 재배치된다 (일회/드리프트).

| # | 항목 | 상태 |
|---|------|------|
| 1 | **`build_sleeve_retag_actions`** — core-only 보유를 investable book 비율로 tournament 재태깅 | [x] |
| 2 | **`build_sleeve_allocation_rebalance_plan`** — retag + allocation-mode trim | [x] |
| 3 | **`src/sleeve_rebalance_state.py`** — pending / drift≥5% 자동 트리거 | [x] |
| 4 | **Pipeline** — `run_sleeve_rebalance_pipeline` retag→refresh→sell + Telegram 요약 | [x] |
| 5 | **CMS** — drift 표시 · 「슬리브 재배치 요청」 버튼 · 저장 시 pending | [x] |
| 6 | **테스트** — `tests/test_sleeve_rebalance.py`, `tests/test_sleeve_rebalance_state.py` | [x] |
| 7 | **Phase 39 Codex pass** — `RUN_ID=phase39_sleeve_alloc bash scripts/run_pass_complete.sh` | [ ] |
| 8 | **운영 확인** — CMS에서 재배치 요청 → 다음 `trading-bot` execute 로그에 `SLEEVE_ALLOCATION_REBALANCE` | [ ] |

**알려진 한계 (follow-up backlog)**

- [ ] 현금 과다(cash>target) 시 **강제 배분 매수** 없음 — buy/tournament pipeline + guard에 의존
- [ ] Telegram 전송 실패 시 로그 미기록 (silent fail) — `notifier` 로깅 개선
- [ ] Dust close `qty must be positive after truncation` — exit pipeline 별도 수정

**하지 말 것**

- cash sleeve 목표 초과 현금을 **강제 매도**하지 말 것
- allocation rebalance가 exit/stop 우선순위를 덮어쓰지 말 것

---

### 3. Backlog (차단·대기)

| 항목 | 상태 | 비고 |
|------|------|------|
| **Toss Open API** (Phase 33) | [ ] blocked | API 키·스펙 대기 |
| **Live 전환** (Phase 34 foundation 완료) | [ ] blocked | Rank 2주 + readiness + operator sign-off |
| **Champion / rank live 승격** | [ ] blocked | AI authority gates |

---

## Shipped — Phase 33 (고도화 검증)

코드·리포트 경로 반영됨. 수치는 `logs/ml/`, `logs/paper_validation/` 참고.

| 슬라이스 | 완료 |
|----------|------|
| **A. 신호 검증** | rank forward-return, LLM block precision, paper validation trend |
| **B. 모델 품질** | calibration overlay, regime weakness report |
| **C. 운영** | crowding reassessment, daily scheduler + Telegram fail alert |

---

## Shipped — Phase 34–35 (Live foundation)

| Phase | 핵심 |
|-------|------|
| **34** | Broker v2 · FakeBroker · LiveSafetyGuard · profiles/schema · live deploy guard · LiveReadinessGate · OrderIntent · audit v2 · data health · CMS operator view |
| **35** | Dust parity · broker order tests · bootstrap wiring · profile merge · audit full migration · Alpaca order board |

---

## Shipped — Phase 36–38 (Portfolio sleeves)

| Phase | 핵심 |
|-------|------|
| **36** | Sleeve config · allocator · OrderIntent sleeve fields · tournament profile · model registry · alpha adapter · sleeve/tournament reports · CMS panel · reconciliation · paper ops reports |
| **37** | CMS sleeve save · `sleeve_runtime` · `main.py` split (`run_context`, buy/exit pipeline) |
| **38** | `sleeve_position_registry` · drift trim pipeline · tournament buy path · Codex `phase38_sleeves_exec` |

**Phase 36 #13** (main 주문 예산 sleeve 경유): Phase 37–38에서 core/tournament/태깅/리밸런스까지 완료 → **[x]**

---

## Shipped — Phase 32 (코드·리포트)

| 슬라이스 | 완료 내용 |
|----------|-----------|
| **32-B LLM** | `google.genai`, vLLM 폴백 |
| **32-C Crowding** | GO paper apply, live impact, bootstrap step |
| **32-D Paper** | LLM block, `paper_buy_validation`, CMS 카드 |
| **32-E Alpha** | trailing 20%, SPY 벤치, CMS alpha metrics |
| **32-F AI quality** | model_quality, rank paper buy gate, threshold/label sweep |

Rank research: 20d/top15%/q85 OOS gate → paper config only. Champion 승격 **없음**.

---

## Quick commands

```bash
# 봇 / CMS
systemctl --user restart trading-bot trading-bot-cms
systemctl --user list-timers trading-bot.timer

# 일일 paper
bash scripts/run_daily_paper_ops.sh
bash scripts/check_paper_daily_timer.sh

# Rank / validation
bash scripts/run_paper_buy_validation.sh
bash scripts/run_paper_validation_trend.sh
bash scripts/run_rank_ai_gate_report.sh
bash scripts/run_rank_gate_forward_return.sh

# Sleeves
bash scripts/run_sleeve_rebalance_once.sh   # 즉시 allocation rebalance (retag + trim)
bash scripts/run_sleeve_performance_report.sh
bash scripts/run_tournament_score_report.sh

# Readiness
bash scripts/run_live_readiness.sh
bash scripts/run_data_health_check.sh

# Phase pass (Codex)
RUN_ID=phase39_sleeve_alloc bash scripts/run_pass_complete.sh
SKIP_CODEX=1 RUN_ID=phase39_sleeve_alloc bash scripts/run_pass_light.sh

bash scripts/run_cms.sh
```

---

## Archive pointer

Phase 0–31 → [`docs/TODO_ARCHIVE.md`](docs/TODO_ARCHIVE.md)

Phase 36–38 상세 체크리스트(과거 DoD)는 git history `TODO.md` @ `944c4d4` 또는 `reports/agent_pipeline/phase36_sleeves*/` 참고.
