# Codex review policy (token budget)

목표: Codex **~15–20%** of agent turns (리뷰 호출 기준), Cursor 구현 + AGY 테스트가 대부분.

## 왜 사용량이 커졌는지 (2026-05 Phase 20–25)

- Phase 20만 **10회+** 별도 `RUN_ID` (promotion v2–v4, slippage v2, gate v2 등) → **픽스마다 Codex 재실행**
- `run_pass_complete.sh`는 기본적으로 **매번** `--run-codex-review` 호출
- 커밋 태그 `[codex]`는 없지만 `reports/agent_pipeline/*/NEXT_TODO.codex.md` **1개 = Codex 1회**

**권장:** Phase당 **Codex 1~2회** (초기 리뷰 + 최종 마감). 중간 수정은 Codex 없이 pytest만.

## 언제 Codex **필수**

- `src/main.py`, 주문·체결, `risk_manager`, 승격/롤백 (`train_ai_model`, `ml_model`)
- 데이터 스키마·감사 로그·설정 검증 경로 변경
- Phase **마감** 전 최종 1회 (high-risk diff)

## 언제 Codex **생략 가능** (`SKIP_CODEX=1`)

- `docs/`, `scripts/run_*_report.sh`, 리포트 전용 `src/*_report.py`
- pytest/fixture만 (`tests/`, `[agy]` 전용)
- Codex P2/P3 반영용 **소규모 follow-up** (이미 같은 Phase에서 리뷰 완료)
- 타이머·runbook·TODO 정리

## 명령

```bash
# 가벼운 패스 (pytest + review_packet, Codex 없음)
RUN_ID=phase26_a SKIP_CODEX=1 bash scripts/run_pass_complete.sh

# 또는
RUN_ID=phase26_a bash scripts/run_pass_light.sh

# Phase 마감 / 고위험 변경 시에만 전체
RUN_ID=phase26_final bash scripts/run_pass_complete.sh "phase 26 complete"
```

## 재리뷰 금지 패턴

| 하지 말 것 | 대신 |
|-----------|------|
| P2 수정마다 `phase20_promotion_v3` 새 RUN_ID | 같은 Phase는 `SKIP_CODEX=1`로 pytest만 |
| 문서-only 커밋에 full pass | `run_pass_light.sh` |
| `--max-changed-files` 초과 시 매번 전체 리뷰 | diff 줄이기 또는 Phase 단위 1회 리뷰 |

## Definition of Done (완화)

| 변경 유형 | pytest | Codex |
|-----------|--------|-------|
| 고위험 (`main`, orders, promotion) | 필수 | 필수 (Phase당 ≤2회) |
| 리포트/문서/테스트 only | 필수 | **선택** |
| TODO `[x]` (Phase 완료) | 필수 | 해당 Phase **마지막** 슬라이스 1회 |
