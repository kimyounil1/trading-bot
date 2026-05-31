# TODO

## Definition of Done (완료 기준)
항목을 `[x]`로 두려면 다음을 **모두** 충족:
1. **코드** — 요구사항 반영, 프로젝트 스타일 준수
2. **테스트** — 관련 pytest 추가·통과
3. **운영** — 필요 시 백테스트/리포트·runbook 반영
4. **리뷰** — `RUN_ID=<pass> SKIP_CODEX=1 bash scripts/run_pass_complete.sh` ([`docs/codex_review_policy.md`](docs/codex_review_policy.md))

---

## Who owns what

| 문서 | 역할 |
|------|------|
| **`TODO.md`** | 활성 로드맵 (다음 Phase만) |
| **`docs/TODO_ARCHIVE.md`** | Phase 0–29 요약 |

---

## Current Status (2026-05-31)

| 영역 | 상태 |
|------|------|
| **ML 백테스트** | **+96.8%** vs B&H **+65.0%** (gap +31.8pp), `beats_benchmark` |
| **LLM** | `llm_advisory_only: true` — 주문 차단 없음, audit만 |
| **Crowding** | `crowding_guard_enabled: false` — paper gate **NO_GO** (Sharpe Δ) |
| **챔피언** | 로컬 `models/`; 승격 시 벤치 이상 필수 |

**Phase 29 완료** → [`docs/TODO_ARCHIVE.md`](docs/TODO_ARCHIVE.md)

---

## Phase 30 — Paper ops (유지보수)

- [ ] 주기: `bash scripts/run_paper_ops_bootstrap.sh` (dry-run + 리포트)
- [ ] paper에서 `execution_audit`·`data/llm_cache.json` 누적 후 `run_llm_advisory_report.sh`로 따름/무시 비교
- [ ] Crowding: `bash scripts/run_crowding_paper_gate.sh` 재실행 후 **GO**일 때만 `config/crowding_paper_proposal.json` 값을 `strategy_config`에 반영

---

## Quick commands

```bash
bash scripts/run_paper_ops_bootstrap.sh
bash scripts/run_alpha_pipeline.sh
bash scripts/warm_llm_cache_from_backtest.sh   # 선택: 캐시 재충전
RUN_ID=phase30 SKIP_CODEX=1 bash scripts/run_pass_complete.sh
```
