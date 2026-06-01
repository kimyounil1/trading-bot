# TODO

## Definition of Done (완료 기준)
항목을 `[x]`로 두려면 다음을 **모두** 충족:
1. **코드** — 요구사항 반영, 프로젝트 스타일 준수
2. **테스트** — 관련 pytest 추가·통과
3. **운영** — 필요 시 백테스트/리포트·runbook 반영
4. **리뷰** — `RUN_ID=phase31 bash scripts/run_pass_complete.sh` ([`docs/codex_review_policy.md`](docs/codex_review_policy.md))

---

## Who owns what

| 문서 | 역할 |
|------|------|
| **`TODO.md`** | 활성 로드맵 (다음 Phase만) |
| **`docs/TODO_ARCHIVE.md`** | Phase 0–30 요약 |

---

## Current Status (2026-06-01)

| 영역 | 상태 |
|------|------|
| **ML 백테스트** | **+96.8%** vs B&H **+65.0%** (gap +31.8pp), `beats_benchmark` |
| **LLM** | `llm_advisory_only: true` — audit 1667 rows, advisory report 갱신 |
| **Crowding** | gate **NO_GO** — `crowding_guard_enabled: false` 유지 (proposal 미적용) |
| **Paper ops** | `logs/paper_ops/latest_summary.json` (bootstrap 2026-06-01) |
| **Extended hours** | Alpaca pre/after/overnight limit orders wired; CMS 주문 현황 패널 |
| **CMS** | `trading-bot-cms.service` @8502, candidate-cache timer 10m |

**Phase 30 완료** → [`docs/TODO_ARCHIVE.md`](docs/TODO_ARCHIVE.md)

---

## Phase 31 — Extended-hours paper ops & CMS parity

### 31-A Execution & monitoring
- [x] Alpaca extended/overnight limit buy/sell via `broker_adapter`
- [x] CMS **Alpaca 주문 현황** (미체결 / 체결 / 취소 탭) + unit tests
- [x] `candidate_cache` AI feature history (`2y`) + SPY/^VIX/macro context
- [ ] Overnight·extended **limit 체결률** 리포트 (`report_performance` 또는 paper_ops 연동)
- [ ] CMS execute 결과와 Alpaca OPEN 주문 **대조 알림** (제출됐는데 OPEN 없음 / OPEN만 있고 로그 없음)

### 31-B Dry-run parity
- [ ] `build_candidate_cache` ↔ `main.py` dry-run **동일 가드** (news, sector, LLM cache_only, earnings 등)
- [ ] 캐시 `execution_label`이 일일 한도 소진 시 **SKIP_DAILY_LIMIT** 등 명시적 라벨 사용
- [ ] `run_frequency_simulation` 결과 runbook/README 한 줄 요약

### 31-C Tests & hardening
- [x] 전체 pytest green (feature_drift import, execution_resilience LLM, pre_qlib broker mock) — **248 passed** (2026-06-01)
- [x] CMS dashboard 회귀 테스트 (`tests/test_cms_dashboard.py`, `src/cms_helpers.py`)
- [ ] `crowding_paper_gate --apply-config` merged JSON **validate_settings** 선검증 (Codex P2)
- [ ] `[AGY]` candidate_cache extended-hours meta 회귀 테스트

### 31-D Ops & commit
- [ ] uncommitted extended-hours + CMS slice **커밋/PR**
- [ ] `bash scripts/run_paper_ops_bootstrap.sh` 재실행 후 `latest_summary.json` 갱신
- [ ] Crowding gate **GO** 재평가 전까지 proposal 미적용 유지

### 31-E Future (본 Phase 블로커 아님)
- [ ] Toss Open API day-market (`broker_provider: toss`)
- [ ] `google.genai` 마이그레이션 (deprecated `google.generativeai`)

---

## Quick commands

```bash
bash scripts/run_paper_ops_bootstrap.sh              # full (model 필요 시 guard refresh)
SKIP_ALPHA=1 bash scripts/run_paper_ops_bootstrap.sh # paper audit/advisory/crowding only
bash scripts/run_alpha_pipeline.sh
bash scripts/warm_llm_cache_from_backtest.sh   # 선택: 캐시 재충전
bash scripts/run_cms.sh                          # CMS http://localhost:8502
.venv/bin/python -m pytest tests/ -q             # 전체 테스트
```
