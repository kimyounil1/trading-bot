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

## Backlog — Phase 32-A Toss (blocked)

- [ ] Toss Open API adapter · CMS execute path (API 키 필요)

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

# 모델 실험 (무거움)
bash scripts/run_threshold_promotion_pipeline.sh
LABEL_SWEEP_ONLY=h20_t0p02 bash scripts/run_threshold_promotion_pipeline.sh

# AGY + Codex
AGY_TEST_PATHS="tests/test_paper_buy_validation_report.py tests/test_rank_ai_gate.py tests/test_execution_audit_io.py" \
  bash scripts/run_agy_slice.sh
RUN_ID=phase32_retry SKIP_PYTEST=1 bash scripts/run_pass_complete.sh

bash scripts/run_cms.sh
```
