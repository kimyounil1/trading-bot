# TODO

## Definition of Done (완료 기준)

항목을 `[x]`로 두려면 다음을 **모두** 충족:

1. **코드** — 요구사항 반영, 프로젝트 스타일 준수
2. **테스트** — 관련 pytest 추가·통과
3. **운영** — 필요 시 백테스트/리포트·runbook 반영
4. **리뷰** — `RUN_ID=<phase> bash scripts/run_pass_complete.sh` ([`docs/codex_review_policy.md`](docs/codex_review_policy.md))

---

## Who owns what

| 문서 / 라벨 | 역할 |
|-------------|------|
| **`TODO.md`** | 활성 로드맵 (지금 할 일만) |
| **`docs/TODO_ARCHIVE.md`** | Phase 0–39 + 2026-06/07 리서치 패스 요약 |
| **`[Cursor]`** | `main.py`, 주문·리스크, 런타임 연결, config wiring |
| **`[Research]`** | 오프라인 실험·스윕·리포트 — **AGY 구현** (`train_ai_model`/`main.py` 주문 경로 미수정) |
| **`[AGY-test]`** | pytest·fixture·harness (구 `[AGY]`와 동일) |
| **`[AGY-risk]`** | 전략·승격·게이트 대형 diff — AGY **read-only** 설계/리스크 리뷰 |

상세: [`CURSOR.md`](CURSOR.md) Task Labels · [`AGY.md`](AGY.md) invocation modes

---

## Current Status (2026-07-07)

| 영역 | 상태 |
|------|------|
| **Paper P&L (Alpaca)** | all-time **+3.2%** ($103.2k) — **흑자 전환**. 6월 한 달 **+5.1%** vs SPY **−0.9%** vs 무제약 시뮬 복제 **+0.2%** (`logs/sim_paper_gap/`) |
| **Sleeves** | tournament **+$5.5k** (승률 100%, 6/9 가동) vs core **−$2.3k** (승률 49%) — 4주 표본, 배분 변경은 ~09월 판단 |
| **Market regime** | **BULL** (최근 60일 중 50일) · SPY 고점 −0.8% · 폭 건강(50MA 위 65%) · 데일리 스냅샷 + 전환 알림 가동 (`logs/market_regime/`) |
| **Research** | **리서치 카드 소진** — 유니버스 확대·gap_vol·실적 피처·VADER 뉴스·레짐 게이트 전부 게이트 기각 (2026-06/07). 마지막 카드 = LLM 소급 스코어링 (진행 중, 로컬 vLLM gemma4-26B) |
| **계측 (증거 루프)** | ① sleeve 성과 데일리(0-기록 버그 수리됨) ② 레짐 스냅샷 데일리 ③ 갭 어트리뷰션 주간(일 18:00 ET, 슬리브 예산 8주 규칙 사전 등록) |
| **버그 수리 (07-06/07)** | ATR <14봉 크래시 · sleeve 리포트 계좌 미조회 · 슬리브 트림 `limit_price` 누락 + `log_order` 시그니처 · 테스트→프로덕션 로그 오염 차단 · 전체 테스트 **503 green** |
| **Crowding A/B (06-16, 2→3)** | **3 유지** — 6월 차단 종목 사후수익 ~중립, 주간 어트리뷰션이 가드별 기회비용 계측을 대체 (별도 평가 종결) |
| **LLM (paper)** | blocking veto 유지 — 20d 기준 reject −4.1% vs accept +0.5% 실증. Gemini 무료티어 **일 20콜** 위에서 운영 중 (유료 전환 시 안정화) |
| **Live readiness** | 시간 조건 충족 + **paper 흑자 전환 달성** — 지속성 관측 후 operator sign-off 논의 가능 |

**현 국면:** "만들고 고치는" 단계 → **"운영하고 판단하는"** 단계. 새 리서치 없이 증거 루프가 9월 판단(슬리브 배분·예산 완화)의 데이터를 쌓는 중.

---

## Active — 지금 할 일

우선순위 순.

### 1. 이번 주 (2026-07-07~)

| # | 항목 | 상태 | 비고 |
|---|------|------|------|
| 1-A | **LLM 소급 스코어링 완주 + IC 최종 판정** | [x] **기각 (07-08)** | 9,866 ticker-days 완주 (vLLM gemma4-26B). `llm_outlook`만 유의(t=2.06)했으나 IC 0.027 < 기준 0.094×0.9 + 누출 편향 → 미채택. **리서치 카드 7연속 기각으로 리서치 트랙 종료.** 데이터셋은 재사용 가능 (`data/research/llm_retro_scores.jsonl`) |
| 1-B | **슬리브 트림 수정 검증** | [x] **종결 (07-08)** | 수정 후 2일간 SELL_ERROR 0 (이전엔 매 리밸런스마다 발생) · 07-08 10:30 REBALANCE_TRIM(OPEN) 정상 제출 · 회귀 테스트 2건이 경로 커버. 슬리브 오버웨이트 트림 자체는 드리프트 임계 미달로 미발동 — 다음 발동 시 정상 동작 예상 |
| 1-C | **stop5_trail10 트라이얼 종결 처리** | [ ] | `READY_TO_EVALUATE`(06-26)인데 06-24 exit 스윕 승격(**tr 0.15 / tp 0.08**)이 트라이얼 config(tr 0.10)를 덮어씀 — 평가 불능 상태. 트라이얼 공식 종료 + 리포트에 superseded 기록 |

### 2. 예정된 판단 (증거 축적 대기 — 손대지 말 것)

| 시점 | 판단 | 근거 데이터 |
|------|------|------------|
| **~2026-09 초** | 토너먼트 배분 30%→확대 여부 | `logs/sleeves/history.jsonl` 8주+ (07-06 이전 기록은 0-버그, `portfolio_value>0` 필터) |
| **~2026-09 초** | core 슬리브 예산 +15% A/B 착수 여부 | `logs/sim_paper_gap/trend_summary.json` — **사전 등록 규칙(8주 연속 플래그) 고정, 중간 수정 금지** |
| **레짐 전환 알림 시** | 노가드 토너먼트 재평가 | `logs/market_regime/` — BULL 이탈 시 텔레그램 알림 |
| **paper 흑자 지속 시** | Live 전환 논의 재개 (Toss 키 보유) | `logs/portfolio_pnl/` + `run_live_readiness.sh` |

### 3. Backlog (낮은 우선 · 선택)

| 항목 | 상태 | 비고 |
|------|------|------|
| **Gemini 유료 전환** | [ ] 선택 | 라이브 veto가 무료티어 **일 20콜** 위에서 아슬아슬 (캐시 미스 → degraded PASS). 유료 시 ~$1/월 수준으로 해소 |
| **테스트 커버리지 보강** | [ ] 선택 | 실행 경로 중 테스트 0인 곳에서 버그 2개씩 나온 전례 (슬리브 트림). 후보: partial_exit·dust_exit·cash_surplus_deploy 경로에 fake-broker 회귀 테스트 |
| **BRK-B→BRK.B 뉴스 매핑** | [ ] 선택 | Alpaca 뉴스 심볼 표기 차이 — 뉴스 리서치 재개 시에만 |
| **LLM×AI 불일치 시그널 연구** | [ ] 보류 | 1-A 결과 확인 후 판단 (같은 데이터 재사용 가능) |
| **Champion / rank live 승격** | [ ] blocked | AI authority gates — 변동 없음 |

---

## Quick commands

```bash
# 봇 / CMS
systemctl --user restart trading-bot trading-bot-cms
systemctl --user list-timers trading-bot.timer

# 일일 paper
bash scripts/run_daily_paper_ops.sh
bash scripts/check_paper_daily_timer.sh

# Rank / validation
bash scripts/run_paper_buy_validation.sh
bash scripts/run_paper_validation_trend.sh
bash scripts/run_rank_ai_gate_report.sh
bash scripts/run_rank_gate_forward_return.sh

# Sleeves / P&L
bash scripts/run_sleeve_rebalance_once.sh   # 즉시 allocation rebalance (retag + trim)
bash scripts/run_sleeve_performance_report.sh
bash scripts/run_tournament_score_report.sh
bash scripts/run_portfolio_pnl_report.sh    # paper P&L snapshot → logs/portfolio_pnl/

# Readiness / LLM precision
bash scripts/run_live_readiness.sh
bash scripts/run_data_health_check.sh
bash scripts/run_llm_block_precision.sh   # → logs/llm_advisory/precision.json

# 증거 루프 (2026-07 신규)
PYTHONPATH=. .venv/bin/python -m src.market_regime_snapshot          # 레짐 스냅샷 (데일리 자동)
bash scripts/run_weekly_gap_attribution.sh                           # 갭 어트리뷰션 (일 18:00 ET 타이머)
PYTHONPATH=. .venv/bin/python -m scripts.llm_retro_scoring --provider vllm --max-calls 10000  # 소급 스코어링 (resume)
PYTHONPATH=. .venv/bin/python -m scripts.llm_feature_research        # LLM 피처 IC 스크린

# Research gates
bash scripts/run_research_promotion_gates.sh
bash scripts/run_model_quality_report.sh   # calibration experiment + model_quality summary

# Phase pass (Codex)
RUN_ID=phase39_sleeve_alloc bash scripts/run_pass_complete.sh
SKIP_CODEX=1 RUN_ID=phase39_sleeve_alloc bash scripts/run_pass_light.sh

bash scripts/run_cms.sh
```

---

## Archive pointer

Phase 0–39 + 2026-06/07 리서치 패스 → [`docs/TODO_ARCHIVE.md`](docs/TODO_ARCHIVE.md)

상세 체크리스트(과거 DoD)는 git history `TODO.md` (Phase 36–38은 @ `944c4d4`, 2026-06/07 패스는 @ `02f7455`) 또는 `reports/agent_pipeline/` 참고.
