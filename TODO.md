# TODO

## Definition of Done (완료 기준)
항목을 `[x]`로 두려면 다음을 **모두** 충족:
1. **코드** — 요구사항 반영, 프로젝트 스타일 준수
2. **테스트** — 관련 pytest 추가·통과 (기본: `run_pass_complete.sh` subset 또는 명시한 경로)
3. **운영** — 필요 시 백테스트/리포트·runbook 반영
4. **리뷰** — pytest 필수; **Codex는 고위험·Phase 마감 시만** ([`docs/codex_review_policy.md`](docs/codex_review_policy.md)):

```bash
RUN_ID=<pass_id> SKIP_CODEX=1 bash scripts/run_pass_complete.sh
RUN_ID=phase29_final bash scripts/run_pass_complete.sh "Phase 29 alpha"
```

---

## Who owns what

| 문서 | 역할 |
|------|------|
| **`TODO.md`** | 활성 로드맵 |
| **`docs/TODO_ARCHIVE.md`** | Phase 0–28 + 백로그 요약 |

**루프:** Cursor 구현 → `[AGY]` 테스트 → `SKIP_CODEX=1` pytest → Codex (마감) → 반영.

---

## Current Status (2026-05-31)

| 영역 | 상태 |
|------|------|
| **알파 목표** | 승격 시 **벤치마크 이상** 필수 (`promotion_portfolio_thresholds`, excess ≥ 0 pp) |
| **랭킹** | `rank_ai_weight=1.0`, `rank_trend_weight=0.5`, RS 필터 ON |
| **포트폴리오 백테스트** | **+96.8%** vs equal-weight B&H **+65.0%** (gap **+31.8pp**), MDD **-7.3%**, Sharpe **3.15** |
| **챔피언** | LGBM+XGB; retrain은 PROMOTE 게이트 통과 시만 교체 |

**완료:** Phase 0–28, 백로그 → [`docs/TODO_ARCHIVE.md`](docs/TODO_ARCHIVE.md)

---

## Phase 29 — Beat benchmark (알파) ← **진행 중**

- [x] `[Cursor]` 승격 OOS: `min_return_vs_benchmark=0`, `min_sharpe=1.0` (`src/promotion_thresholds.py`)
- [x] `[Cursor]` `config/strategy_config.json` — AI 랭킹·RS 필터로 후보 품질 상향
- [x] `[Cursor]` `benchmark_gap` 리포트 — `beats_benchmark`, `recommendations`
- [x] `[AGY]` `tests/test_promotion_beat_benchmark.py`
- [x] `[Cursor]` equal-weight 벤치마크 NaN 버그 수정 (`_build_equal_weight_benchmark_values`)
- [x] `[Cursor]` `run_portfolio_backtest` ↔ config 정합 (`portfolio_backtest_settings.py`, 손절/익절 전달)
- [x] `[Cursor]` `volume_filter_enabled=false`, `max_position_pct=0.11`, AI·RS 랭킹 유지
- [x] `[AGY]` `bash scripts/run_alpha_pipeline.sh` — **+96.8% vs bench +65.0%** (`beats_benchmark=true`, gap +31.8pp)
- [x] `[AGY]` LLM/뉴스 필터 impact — `python -m src.llm_backtest_impact_report` (`run_alpha_pipeline` 포함)
- [x] `[Cursor]` in-loop 운영 검증 — `bash scripts/run_operational_alpha_validation.sh` (baseline vs LLM+news)
- [x] `[Cursor]` 백테스트 진입 141키 `data/llm_cache.json` 워밍업 (`scripts/warm_llm_cache_from_backtest.sh`)
- [ ] `[Cursor]` paper `main.py`로 캐시·`execution_audit.csv` 운영 중 갱신
- [ ] `[Cursor]` 벤치 초과 유지 시 paper `crowding_guard_enabled` 점진 활성화 검토

---

## Quick commands

```bash
bash scripts/run_alpha_pipeline.sh
bash scripts/run_ops_reports.sh --weekly
RUN_ID=phase29 SKIP_CODEX=1 bash scripts/run_pass_complete.sh
```
