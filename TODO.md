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
| **Paper ops** | `logs/paper_ops/latest_summary.json` (bootstrap 2026-06-01 01:32 UTC) |
| **Extended hours** | Alpaca pre/after/overnight limit orders wired; CMS 주문 현황 패널 |
| **CMS** | `trading-bot-cms.service` @8502, candidate-cache timer 10m |
| **CI/CD** | GitHub Actions **green** on `main` (`03ef071`) — pytest 248, cms-import, deploy-gate |

**Phase 30 완료** → [`docs/TODO_ARCHIVE.md`](docs/TODO_ARCHIVE.md)  
**Phase 31 진행 중** — 아래 체크리스트 (커밋·CI 완료, dry-run parity·리포트·AGY 테스트 남음)

---

## Phase 31 — Extended-hours paper ops & CMS parity

### 31-A Execution & monitoring
- [x] Alpaca extended/overnight limit buy/sell via `broker_adapter`
- [x] CMS **Alpaca 주문 현황** (미체결 / 체결 / 취소 탭) + unit tests
- [x] `candidate_cache` AI feature history (`2y`) + SPY/^VIX/macro context
- [x] Overnight·extended **limit 체결률** 리포트 (`src/extended_hours_fill_report.py` → `logs/paper_ops/`)
- [x] CMS execute 결과와 Alpaca OPEN 주문 **대조 알림** (`reconcile_cms_execute_with_alpaca`)

### 31-B Dry-run parity
- [x] `build_candidate_cache` ↔ `main.py` dry-run **동일 가드** (`src/buy_guards.py` shared pipeline)
- [x] 캐시 `execution_label` 일일 한도 소진 시 **`SKIP_DAILY_LIMIT`** / cooldown 라벨
- [x] `run_frequency_simulation` 결과 runbook/README 한 줄 요약

### 31-C Tests & hardening
- [x] 전체 pytest green — **248 passed** 로컬 + CI (`tests/`, 2026-06-01)
- [x] CMS dashboard 회귀 테스트 (`tests/test_cms_dashboard.py`, `src/cms_helpers.py`)
- [x] CI: `nltk` in `requirements.txt` + VADER download step
- [x] CI: `test_execution_resilience` LLM mocks (`GEMINI_API_KEY` empty 시에도 API 경로 검증)
- [x] `tests/test_broker_adapter.py`, `tests/test_trading_session.py`, `tests/test_alpaca_order_board.py`
- [x] `crowding_paper_gate --apply-config` invalid proposal **pytest** (`crowding_lookback_days` 등)
- [x] candidate_cache extended-hours meta **단위** 회귀 (`tests/test_buy_guards.py`)

### 31-D Ops & commit
- [x] Extended-hours + CMS + CI slice **커밋/푸시** (`b33d5ad`, `892263d`, `03ef071` → `main`)
- [x] GitHub Actions `.github/workflows/ci.yml` (push/PR → test, cms-import, deploy-gate)
- [ ] `RUN_ID=phase31 bash scripts/run_pass_complete.sh` (Codex scoped review — Definition of Done #4)
- [x] `bash scripts/run_paper_ops_bootstrap.sh` 재실행 + extended fill report (`scripts/run_paper_ops_bootstrap.sh` 6/7)
- [x] Crowding gate **NO_GO** — proposal 미적용 유지 (`latest_summary.json` `crowding_config_applied: false`)

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
# CI와 동일: https://github.com/kimyounil1/trading-bot/actions
RUN_ID=phase31 bash scripts/run_pass_complete.sh # Phase 31 Codex 리뷰 (미실행)
```
