# TODO

## Definition of Done (완료 기준)
항목을 `[x]`로 두려면 다음을 **모두** 충족:
1. **코드** — 요구사항 반영, 프로젝트 스타일 준수
2. **테스트** — 관련 pytest 추가·통과, 전체 suite green
3. **운영** — 필요 시 백테스트/리포트 확인; 구현 후 `bash scripts/run_cursor_post_workflow.sh` → Codex scoped review에서 blocking 이슈 없음

---

## Who owns what (TODO 담당)

| 문서 | 역할 | 누가 쓰나 |
|------|------|-----------|
| **`TODO.md`** (이 파일) | 중기 로드맵·Phase | **사용자 + Cursor**가 Phase/우선순위 갱신. 대규모 방향은 **AGY**(선택) 검토 |
| **`reports/.../NEXT_TODO.md`** | 이번 PR/패스 직후 작업 큐 | `run_cursor_post_workflow.sh`가 **초안** 생성 |
| **`NEXT_TODO.codex.md`** | 리뷰 후 다음 구현 큐 | **Codex**가 리뷰 끝에 작성 (`# NEXT_TODO for Cursor`) |
| **완료 Phase 기록** | 토큰 절약용 요약 | **`docs/TODO_ARCHIVE.md`** — Phase 0–19 요약만 유지 |

**루프:** Cursor 구현 → post-workflow → Codex 리뷰·`NEXT_TODO` → Cursor가 다음 슬라이스. 장기 Phase는 Codex 출력을 보고 **사용자가 `TODO.md`에 반영**하는 것이 기본(자동 merge 아님).

---

## Agent Workflow (Cursor-First)

| 역할 | 담당 |
|------|------|
| **Cursor** | 메인 구현 (`CURSOR.md`) |
| **Codex** | read-only 리뷰, `NEXT_TODO` (`AGENTS.md`) |
| **AGY** | (선택) 전략·리스크·아키텍처 |
| **Gemini CLI** | (선택) `[Gemini]` 슬라이스 |

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

## Phase 20 — Portfolio validation & 벤치마크 정합성 `[Cursor]`

- [ ] 포트폴리오 백테스트 결과를 CI 또는 post-workflow에서 주기 실행·`portfolio_summary.csv` 임계값(벤치마크 대비, max DD) 체크
- [ ] `walk_forward_validation` / retrain 후 **포트폴리오 수준** 승격 기준을 AUC 단독이 아닌 OOS P&L·Sharpe와 연동
- [ ] `report_performance.py` paper vs signal 슬리피지를 주간 runbook 항목으로 자동화(스크립트 또는 timer 문서화)

---

## Phase 21 — 신호·모델 품질 (fold 안정화) `[Cursor]` / `[Gemini]` 피처 실험

- [ ] Walk-forward fold별 ROC-AUC 편차 원인 분석 및 레짐/기간별 calibration 리포트 고정 경로
- [ ] 챔피언 승격 시 `train_ai_model` 메트릭 + 포트폴리오 백테스트 **둘 다** 통과해야 교체
- [ ] (선택) Transformer / RL: live 연동 **또는** README·TODO에 “research-only”로 명시하고 `main.py` 경로에서 제외 유지

---

## Phase 22 — 운영 관측 & 실행 품질 `[Cursor]`

- [ ] 일별 audit 요약(스킵 사유, API 오류, stale bar) 대시보드 또는 `logs/` 집계 스크립트
- [ ] Retrain 실패·부분 성공 시 Telegram/runbook 알림 경로 점검
- [ ] Macro/earnings 이벤트 전후 실제 스킵 비율 로그 기반 검증

---

## Phase 23 — (백로그) 전략·리스크 `[AGY]` 검토 후 착수

- [ ] Factor/crowding guard 실거래 영향도 백테스트
- [ ] Leverage 사용 시 stress scenario (gap down, correlation spike)
- [ ] LLM consensus 비용·캐시 hit rate 모니터링
