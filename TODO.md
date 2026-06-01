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
| **`TODO.md`** | 활성 로드맵 (다음 Phase만) |
| **`docs/TODO_ARCHIVE.md`** | Phase 0–31 요약 |

---

## Current Status (2026-06-01)

| 영역 | 상태 |
|------|------|
| **ML 백테스트** | **+96.8%** vs B&H **+65.0%** (gap +31.8pp) |
| **Extended hours / CMS** | broker_adapter, buy_guards parity, Alpaca order board, CMS reconcile |
| **CI/CD** | GitHub Actions green — **257** pytest (`main`) |
| **Crowding** | gate **GO_PAPER** (리포트) · config **`crowding_guard_enabled: false`** (운영 정책) |
| **Paper ops** | `logs/paper_ops/latest_summary.json` + extended fill report |
| **LLM SDK** | `google-genai` (`src/llm_analyst.py`) — legacy `google-generativeai` 제거 |

**Phase 31 완료** → [`docs/TODO_ARCHIVE.md`](docs/TODO_ARCHIVE.md) · Codex `RUN_ID=phase31`

---

## Phase 32 — Integrations & deprecations

### 32-A Toss (KR day market)
- [ ] Toss Open API adapter (`broker_provider: toss`) — 주문 제출 (현재: `trading_session` day_market stub only)
- [ ] CMS/bot execute path for Toss paper

### 32-B LLM SDK
- [x] `google.generativeai` → `google.genai` (`llm_analyst.py`, `google-genai` in requirements, tests)
- [x] 로컬 vLLM 서브모델 폴백 (`192.168.219.116:11434`, `gemma4-26B`) — Gemini quota/5xx 시

### 32-C Ops
- [ ] Crowding **GO** 재평가 후 `APPLY_CROWDING_CONFIG=1` bootstrap으로 proposal 반영 여부 결정

---

## Quick commands

```bash
bash scripts/run_paper_ops_bootstrap.sh
SKIP_ALPHA=1 bash scripts/run_paper_ops_bootstrap.sh
APPLY_CROWDING_CONFIG=1 bash scripts/run_paper_ops_bootstrap.sh   # GO + 명시적 merge만
bash scripts/run_cms.sh
.venv/bin/python -m pytest tests/ -q
RUN_ID=phase32 bash scripts/run_pass_complete.sh
```
