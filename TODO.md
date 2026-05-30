# TODO

## Definition of Done (완료 기준)
항목을 `[x]`로 두려면 다음을 **모두** 충족:
1. **코드** — 요구사항 반영, 프로젝트 스타일 준수
2. **테스트** — 관련 pytest 추가·통과, 전체 suite green
3. **운영** — 필요 시 백테스트/리포트 확인
4. **Codex 리뷰 (필수)** — Cursor 구현 + `[AGY]` 테스트까지 끝난 뒤 **반드시** 패스 마감:

```bash
RUN_ID=<pass_id> bash scripts/run_pass_complete.sh "무엇을 했는지 한 줄"
# → review_packet.md 생성 → Codex scoped review → NEXT_TODO.codex.md 확인
# blocking 이슈 없을 때만 [x]. 실패 시 Codex 지적 반영 후 재실행.
```

---

## Who owns what (TODO 담당)

| 문서 | 역할 | 누가 쓰나 |
|------|------|-----------|
| **`TODO.md`** (이 파일) | 중기 로드맵·Phase | **사용자 + Cursor**가 Phase/우선순위 갱신. 전략·리스크는 **AGY** 검토, **테스트는 `[AGY]`** |
| **`reports/.../NEXT_TODO.md`** | 이번 PR/패스 직후 작업 큐 | `run_cursor_post_workflow.sh`가 **초안** 생성 |
| **`NEXT_TODO.codex.md`** | 리뷰 후 다음 구현 큐 | **Codex**가 리뷰 끝에 작성 (`# NEXT_TODO for Cursor`) |
| **완료 Phase 기록** | 토큰 절약용 요약 | **`docs/TODO_ARCHIVE.md`** — Phase 0–19 요약만 유지 |

**루프:** Cursor 구현 → post-workflow → Codex 리뷰·`NEXT_TODO` → Cursor가 다음 슬라이스. 장기 Phase는 Codex 출력을 보고 **사용자가 `TODO.md`에 반영**하는 것이 기본(자동 merge 아님).

---

## Agent Workflow (Cursor-First)

| 역할 | 담당 |
|------|------|
| **Cursor** | 메인 구현 (`CURSOR.md`) |
| **Codex** | read-only 리뷰, `NEXT_TODO` (~15–20%) |
| **AGY** | **`[AGY]` 테스트·하네스** + (선택) 전략·리스크 검토 (~15–25%) |
| **Gemini CLI** | 레거시·문서만 (~0–5%, Flash급 — 테스트 금지) |

### 멀티 계정·토큰 균형 (운영 의도)

Cursor / AGY / Codex를 **서로 다른 구독·계정**으로 쓰는 경우, 작업을 고르게 나누는 것이 맞습니다.

| 계정 | 패스당 역할 | 토큰을 쓰는 타이밍 |
|------|-------------|-------------------|
| **Cursor** | `src/` 구현·통합·설정·리뷰 반영 | 기능 개발 턴 |
| **AGY** | `[AGY]` pytest·fixture·harness만 | Cursor 커밋 직후 **별도 AGY 세션** |
| **Codex** | scoped 리뷰·`NEXT_TODO` | `run_pass_complete.sh` 1~2회/패스 |

**균형 목표 (주간, `agent_workload_report.py`):** 구현 라인 ~**55–65% Cursor**, 테스트 라인 ~**20–30% AGY**, 리뷰 ~**15–20% Codex** (Codex는 커밋 수보다 **호출 횟수**로 보면 됨).

**AGY 세션 생략 가능:** `main.py`/주문 경로 변경 없음, 테스트 추가 ≤2파일, harness만 — 단, **이번 주 AGY 비중이 목표보다 10%p 이상 낮으면** 다음 `[AGY]` 항목은 AGY 세션으로 처리.

**중복 금지:** 같은 테스트를 Cursor·AGY **둘 다** 작성하지 않음 (한 패스 = 한 구현 계정 + 한 테스트 계정).

**패스 마감 (필수):** Cursor 구현 → **AGY 테스트** → `bash scripts/run_pass_complete.sh` → **`NEXT_TODO.codex.md` 확인** → Cursor 수정.

**작업량 집계:** `PYTHONPATH=. .venv/bin/python scripts/agent_workload_report.py --record`  
커밋 메시지에 `[cursor]` / `[agy]` / `[codex]` 태그 → `logs/agent_workload_history.csv`에 스냅샷 누적.

```bash
RUN_ID=phase20_a bash scripts/run_cursor_post_workflow.sh
.venv/bin/python scripts/agent_orchestrator.py --run-id phase20_a --run-codex-review --scoped-review
```

---

## Current Status (2026-05-30)

- **Tickers:** 110 (`config/strategy_config.json`) + dynamic universe
- **Models:** Regime-aware LGBM+XGB ensemble; last retrain `logs/retrain_history.csv` (ROC-AUC ~0.51)
- **Walk-forward (5-fold):** ROC-AUC 0.45–0.55 — fold 간 편차 큼 (`logs/ml/ai_model_metrics.csv`)
- **Portfolio backtest (recent):** total return **+50.7%**, benchmark **+58.2%**, max DD **-10.2%**, 42 trades (`logs/portfolio_backtest/`)
- **Not in live path:** `deep_model.py`, `rl_portfolio.py` (Phase 12 infra only)

**Completed roadmap:** Phase 0–19 → [`docs/TODO_ARCHIVE.md`](docs/TODO_ARCHIVE.md)

---

## Phase 20 — Portfolio validation & 벤치마크 정합성

- [x] `[Cursor]` post-workflow/CI 훅에서 `portfolio_summary.csv` 임계값(벤치마크 대비, max DD) 체크 연동
- [ ] `[AGY]` `tests/test_portfolio_backtest_gate.py` — `prompts/agy/phase20_portfolio_gate.md`
- [ ] `[Cursor]` retrain 후 **포트폴리오 수준** 승격 기준을 AUC 단독이 아닌 OOS P&L·Sharpe와 연동
- [ ] `[Cursor]` `report_performance.py` paper vs signal 슬리피지 주간 자동화(스크립트 또는 timer)
- [x] `[AGY]` portfolio backtest golden test: fixture equity/trades vs `logs/portfolio_backtest/` 스키마·핵심 메트릭 회귀

---

## Phase 21 — 신호·모델 품질 (fold 안정화)

- [ ] `[Cursor]` Walk-forward fold별 ROC-AUC 편차 분석 및 calibration 리포트 **생성 경로** 구현
- [ ] `[AGY]` calibration/Brier 리포트 출력에 대한 pytest + fold별 메트릭 CSV 스키마 회귀 테스트
- [ ] `[Cursor]` 챔피언 승격: `train_ai_model` 메트릭 + 포트폴리오 백테스트 **둘 다** 통과해야 교체
- [ ] `[AGY]` 승격/롤백 decision path mock 테스트 (챌린저 거절·롤백 시나리오)
- [ ] `[Cursor]` (선택) Transformer / RL: live 연동 **또는** “research-only” 명시

---

## Phase 22 — 운영 관측 & 실행 품질

- [ ] `[Cursor]` 일별 audit 요약(스킵 사유, API 오류, stale bar) 집계 스크립트 또는 대시보드
- [ ] `[AGY]` audit 집계 출력·스키마에 대한 단위 테스트 + 샘플 로그 fixture
- [ ] `[Cursor]` Retrain 실패·부분 성공 시 Telegram/runbook 알림 경로 점검
- [ ] `[AGY]` macro/earnings 스킵 비율: 로그 fixture 기반 회귀 테스트

---

## Phase 23 — (백로그) 전략·리스크 `[AGY]` 검토 후 착수

- [ ] Factor/crowding guard 실거래 영향도 백테스트
- [ ] Leverage 사용 시 stress scenario (gap down, correlation spike)
- [ ] LLM consensus 비용·캐시 hit rate 모니터링
