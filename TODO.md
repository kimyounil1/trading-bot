# TODO

## Definition of Done (완료 기준)
항목을 `[x]`로 두려면 다음을 **모두** 충족:
1. **코드** — 요구사항 반영, 프로젝트 스타일 준수
2. **테스트** — 관련 pytest 추가·통과 (기본: `run_pass_complete.sh` subset 또는 명시한 경로)
3. **운영** — 필요 시 백테스트/리포트·runbook 반영
4. **리뷰** — pytest 필수; **Codex는 고위험·Phase 마감 시만** ([`docs/codex_review_policy.md`](docs/codex_review_policy.md)):

```bash
# 일반 follow-up / docs / 리포트 스크립트
RUN_ID=<pass_id> SKIP_CODEX=1 bash scripts/run_pass_complete.sh

# Phase 마감 또는 main/orders/promotion 변경
RUN_ID=<phase>_final bash scripts/run_pass_complete.sh "Phase N complete"
```

---

## Who owns what

| 문서 | 역할 |
|------|------|
| **`TODO.md`** | 활성 로드맵 (Phase 24+) — 사용자·Cursor가 우선순위 갱신 |
| **`docs/TODO_ARCHIVE.md`** | 완료 Phase 0–23 요약 |
| **`reports/.../NEXT_TODO.codex.md`** | 패스 직후 Codex 구현 큐 |

**루프:** Cursor 구현 → `[AGY]` 테스트 → `SKIP_CODEX=1` pytest (중간) → Codex **1회** (마감) → 반영.

| 역할 | 담당 |
|------|------|
| **Cursor** | `src/` 구현·설정·runbook |
| **AGY** | `[AGY]` pytest·fixture·harness |
| **Codex** | scoped 리뷰 **Phase당 1~2회** (~15–20% 호출 목표; 중간 수정은 `SKIP_CODEX=1`) |
| **Gemini CLI** | 문서만 (테스트·트레이딩 경로 금지) |

커밋 태그: `[cursor]` / `[agy]` — `scripts/agent_workload_report.py --record`

---

## Current Status (2026-05-30)

| 영역 | 상태 |
|------|------|
| **유니버스** | `UNIVERSE_PROFILE` paper/smoke/research; master **259** (`config/universe_master.csv`) |
| **종목 메타** | `instrument_registry.json` — 레버리지 ETF 기본 매수 차단 (`allow_leveraged_etfs: false`) |
| **마진 레버리지 paper** | stress gate + `margin_leverage_paper_proposal.json` (기본 비활성) |
| **챔피언 모델** | LGBM+XGB, 로컬 `models/ai_score_model.joblib` (git 미추적) |
| **최근 retrain** | `logs/retrain_history.csv` — fold ROC-AUC ~0.45–0.55, 평균 ~0.51 근처 |
| **포트폴리오 백테스트** | return **+50.7%** vs bench **+58.2%**, max DD **-10.2%**, 42 trades (`logs/portfolio_backtest/`) |
| **거버넌스** | 승격 = ML 품질 + 포트폴리오 OOS 게이트; retrain 실패/챔피언 유지 Telegram |
| **관측** | 일별 audit, 주간 slippage, guard/leverage/LLM cache 리포트 스크립트 (`docs/runbook.md`) |
| **비활성** | `deep_model.py`, `rl_portfolio.py` — `docs/RESEARCH_MODELS.md` |

**완료 로드맵:** Phase 0–28 → [`docs/TODO_ARCHIVE.md`](docs/TODO_ARCHIVE.md)

**우선순위 가이드 (2026 Q2)**
1. **백로그** — 마진 레버리지 paper, crowding 라이브, DL/RL
2. **알파·승격 품질** — 벤치마크 underperform, fold 편차 완화
3. **라이브 정합** — paper vs 백테스트·슬리피지 드리프트
4. **백로그** — 마진 레버리지 paper, DL/RL 연구

---

## Backlog

- [x] `[AGY]` Factor/crowding guard **라이브** 영향도 — `src/crowding_live_impact_report.py`, `bash scripts/run_crowding_live_impact_report.sh`
- [x] `[Cursor]` Transformer / RL — `experiments/README.md`, `bash scripts/run_research_smoke.sh`
- [x] `[Cursor]` Streamlit CMS ops `latest_summary` 뷰어 확장 (`app/streamlit_app.py` Ops / 게이트)

---

## Quick commands

```bash
# 패스 마감
RUN_ID=phase24_ops bash scripts/run_pass_complete.sh "작업 요약"

# 유니버스 프로필 (기본 paper = strategy_config tickers)
UNIVERSE_PROFILE=smoke .venv/bin/python -m src.run_portfolio_backtest   # 빠른 스모크
UNIVERSE_PROFILE=research .venv/bin/python -m src.main --dry-run      # master 259종 스캔

# 운영 리포트 (수동)
bash scripts/run_ops_reports.sh
bash scripts/run_ops_reports.sh --weekly
bash scripts/run_fold_variance_report.sh
bash scripts/run_promotion_summary.sh
bash scripts/run_benchmark_gap_report.sh
bash scripts/run_guard_impact_report.sh    # 무거움 — 주간 권장
bash scripts/run_crowding_live_impact_report.sh
bash scripts/run_research_smoke.sh         # research-only, non-production
bash scripts/run_leverage_stress_report.sh --leverage 2.0
bash scripts/run_margin_leverage_paper_gate.sh --leverage-factor 1.25

# retrain (로컬 챔피언만 갱신, PROMOTE 시에만 교체)
bash scripts/run_retrain.sh
```
