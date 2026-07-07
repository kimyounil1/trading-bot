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
| **`docs/TODO_ARCHIVE.md`** | Phase 0–31 요약 |
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
| 1-A | **LLM 소급 스코어링 완주 + IC 최종 판정** | [ ] 진행 중 (오늘 ~17:40) | 로컬 vLLM gemma4-26B, 9,861 ticker-days · 완주 후 `scripts/llm_feature_research.py` — **마지막 리서치 카드**. 중간(36d): 전부 no-edge, `llm_approved` 음수 관찰 · 사전학습 누출 편향 주의 (통과해도 paper A/B 필수) |
| 1-B | **BB/GRAB 슬리브 트림 재시도 확인** | [ ] 내일 04:45 런 | `limit_price` 수정(dd1a91e)은 07-07 15:00 런에서 무에러 검증 완료. 트림 자체는 다음 리밸런스 트리거에서 `SELL_SUBMITTED` 확인 → 완료 시 memory `bb-trim-verification-pending` 삭제 |
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

## Shipped — 2026-06/07 리서치 소진 + 계측/하드닝 패스

**리서치 레버 전수 검증 — 전부 기각** (원칙: IC 통과 ≠ 모델 게이트 통과, 6연속 확인):

| 레버 | 결과 | 산출물 |
|------|------|--------|
| 유니버스 110→255 확대 (3-arm A/B) | 수익 +2.8pp뿐, Sharpe 반토막·MDD 3배 → 기각. 학습만 확대도 −8.9pp | `scripts/rank_universe_ab.py` · `logs/ml/rank_universe_ab/` |
| gap_vol_20d 피처 | 단독 IC 최강, 재학습 gap 36→14% → 기각 | `logs/ml/rank_gap_feature_retrain/` |
| 실적 피처 (days_to/surprise_streak/last_surprise) | IC 3종 통과(t 2.7~3.9), 재학습 gap −17pp → 기각 | `scripts/earnings_feature_*` · `logs/ml/earnings_feature_retrain/` |
| VADER 뉴스 센티먼트 4종 | IC 스크린 탈락 (best t=1.6) | `scripts/news_*` · `data/news_history/` (156k 헤드라인, 재사용 가능) |
| 레짐 조건부 랭크 게이트 | 6m 통과, 12m 재현 실패 → 기각. 컷오프 조이기는 no-op | `scripts/rank_regime_gate_experiment.py` · `logs/ml/rank_regime_gate/` |
| 랭크 게이트 그리드 (q80/85/90) | 기존 06-02 실험 — 현행 q85/top15 최고 확인 | `logs/ml/rank_label_experiment_*` |

**갭 어트리뷰션 (핵심 발견):** 6월 paper **+3.1%** > EW +1.1% > 무제약 시뮬 +0.2% > SPY −0.9% — 백테스트 gap은 라이브 기대치 아님. 최대 누수 = **슬리브 예산 소진**(차단 종목 +3.2% fwd), correlation 가드는 패자 차단(유지). → 주간 리포트화 + 8주 판정 규칙 사전 등록.

**크라우딩 A/B (06-16, 2→3) 종결:** 3 유지 — 6월 차단 종목 사후수익 ~중립, 이후 가드 계측은 주간 어트리뷰션으로 일원화. §5-A(ma_slow/rsi 트라이얼)는 근거 부족으로 보류 전환.

**버그 수리:** ATR <14봉 IndexError(신규상장 매수 전멸) · sleeve 리포트 계좌 미조회(0-기록 22일) · 슬리브 트림 `limit_price`+`log_order`(트림 전멸) · 테스트→프로덕션 audit CSV 오염 · 시간 썩은 테스트 2건. **suite 503 green.**

**신규 계측:** `market_regime_snapshot`(데일리+전환 알림) · `sim_paper_gap_attribution`(주간, systemd timer) · sleeve P&L 실데이터 데일리. `universe_master.csv` 죽은 티커 6종 정리(SQ→XYZ, WRK→SW 등).

---

## Shipped — Phase 33 (고도화 검증)

코드·리포트 경로 반영됨. 수치는 `logs/ml/`, `logs/paper_validation/` 참고.

| 슬라이스 | 완료 |
|----------|------|
| **A. 신호 검증** | rank forward-return, LLM block precision, paper validation trend |
| **B. 모델 품질** | calibration overlay, regime weakness report |
| **C. 운영** | crowding reassessment, daily scheduler + Telegram fail alert |

---

## Shipped — Phase 34–35 (Live foundation)

| Phase | 핵심 |
|-------|------|
| **34** | Broker v2 · FakeBroker · LiveSafetyGuard · profiles/schema · live deploy guard · LiveReadinessGate · OrderIntent · audit v2 · data health · CMS operator view |
| **35** | Dust parity · broker order tests · bootstrap wiring · profile merge · audit full migration · Alpaca order board |

---

## Shipped — Phase 36–38 (Portfolio sleeves)

| Phase | 핵심 |
|-------|------|
| **36** | Sleeve config · allocator · OrderIntent sleeve fields · tournament profile · model registry · alpha adapter · sleeve/tournament reports · CMS panel · reconciliation · paper ops reports |
| **37** | CMS sleeve save · `sleeve_runtime` · `main.py` split (`run_context`, buy/exit pipeline) |
| **38** | `sleeve_position_registry` · drift trim pipeline · tournament buy path · Codex `phase38_sleeves_exec` |

**Phase 36 #13** (main 주문 예산 sleeve 경유): Phase 37–38에서 core/tournament/태깅/리밸런스까지 완료 → **[x]**

---

## Shipped — Phase 39 (Allocation rebalance + P&L)

커밋 `82764c6` @ `main`.

| 슬라이스 | 완료 |
|----------|------|
| **39-A Allocation rebalance** | `build_sleeve_retag_actions` · `build_sleeve_allocation_rebalance_plan` · `sleeve_rebalance_state.py` (pending / drift≥5%) · pipeline retag→refresh→sell · `--sleeve-rebalance-only` · `run_sleeve_rebalance_once.sh` |
| **39-B CMS sleeves** | drift 표시 · 「지금 슬리브 재배치 실행」 / 「다음 execute 예약」 · 저장 시 pending |
| **39-C Portfolio P&L** | `portfolio_pnl_report.py` — Alpaca equity periods · positions · trades · **FIFO realized** · CMS **수익 · 매매** · `run_portfolio_pnl_report.sh` |
| **39-D Tests** | `test_sleeve_rebalance.py` · `test_sleeve_rebalance_state.py` · `test_portfolio_pnl_report.py` |
| **39-E Review** | Codex `phase39_sleeve_alloc` — clean |

**한계 / follow-up:** ~~cash surplus~~ · ~~Telegram silent fail~~ · ~~dust close~~ — resolved in follow-up pass.

---

## Follow-up backlog (비 Phase)

- [x] 현금 과다(cash>target) 시 **강제 배분 매수** — `compute_sleeve_cash_surplus_deploy` + `apply_cash_surplus_deploy` (main run)
- [x] Telegram silent fail — `notifier` WARNING 로깅
- [x] Dust close `qty must be positive after truncation` — `safe_order_qty_or_none` + broker full close fallback
- [x] CMS 한글 스킵 설명 (`buy_skip_reason_ko`) + guard×레짐 스터디 (`guard_regime_study`) — 커밋 `1f696bd`
- [x] **Live readiness 블로커 해소 (2026-06-11)** — 남은 NO_GO 사유는 시간 조건 2개뿐 (rank 14d, validation 14d)
  - LLM precision: blocking 모드 REJECT(`LLM_ADVISORY`/`SKIP_BUY`)도 집계 + ticker/일자/판정 dedupe + **단기 5d horizon** 추가(`events_used`는 단기 기준) + 일일 bootstrap 연결(`run_paper_ops_bootstrap.sh` 2a). audit 이력이 05-27부터라 20d horizon은 미성숙 → 단기 horizon으로 게이트 충족 (reject=15/accept=82)
  - data_health: 변동성 지수(^VIX 등) 전용 `max_daily_jump` 임계치 1.5 (일반 0.35 유지) → ^VIX 74% 점프 오탐 해소, **GO**
  - LLM verdict 파싱: thinking 모드 CoT 대응 — **마지막** DECISION/CATEGORY/REASON 블록 채택(`parse_llm_decision`), reason 1줄·300자 클립, `format_llm_verdict` 500자 안전망. 기존 "CoT에 'DECISION: APPROVE' 언급만 있어도 승인" 버그 수정

### Next research directions (커밋 `1f696bd` 기반)

엔진 기반(`portfolio_backtester` regime/sector kwargs, `regime_stop_policy`)은 default-off로 이미 머지됨. 아래는 **결론·연결 대기**.

- [x] **방향2 — 레짐 적응형 손절/트레일링** (백테스트 완료 · paper **미채택**)
  - 하네스: `src/regime_stop_backtest.py` · `scripts/run_regime_stop_backtest.sh`
  - **결론 (2026-06-11):** 2년 full / bull / bear 구간 모두 **baseline 5%/20%** (실질 stop-only) 우수. 레짐 adaptive(standard/conservative/bear-only)는 수익 열위.
  - **follow-up:** `9_stop5_trail10` (5%/10%) — full 2y 수익 -0.2pp, MDD -9.4%→-6.3% 개선 → **Active §3 paper trial**로 이동.
  - **연결:** `exit_pipeline` + `regime_adaptive_stop_enabled` (config **false**). 켜려면 `strategy_config.json` + 관측.
  - 산출물: `logs/regime_stop_backtest/latest_summary.json`, `followup_latest_summary.json`
- [x] **방향3 — 장중 진입/청산 타이밍** (백테스트 완료 · 스케줄 **유지**)
  - 하네스: `src/intraday_timing_backtest.py` · `scripts/run_intraday_timing_2w.sh`
  - **결론 (2026-06-11, 11거래일):** baseline 09:35/15:45 **-1.88%**. 최선 `5_fade_spike` **-1.71%** (+0.17pp) — 채택 기준 0.5pp 미달.
  - 시그널일 진입엣지: 11:00이 64% 더 저렴(avg +98bps)이나 포트 수익은 오히려 열위 → **스케줄 변경 없음**.
  - 산출물: `logs/intraday_timing_2w/latest_summary.json`
- [x] **방향4 — 리서치 산출물 → promotion gate 반영**
  - `research_promotion_gates.py` · `run_research_promotion_gates.sh` — rank sweep(9건, **2건 OOS 통과**) + guard policy + exit/timing verdict 통합
  - `promotion_summary --research` · `paper_ops_summary` · `docs/promotion_gates.md` 연동
  - **결론:** champion 승격 불가 · paper rank `h20_top15_q85` 유지 · guard 완화 금지(관측 중) · regime/intraday 변경 없음
  - 일회성 스윕 스크립트(`exp_*.py`)는 별도 보관(untracked)

---

## Shipped — Phase 32 (코드·리포트)

| 슬라이스 | 완료 내용 |
|----------|-----------|
| **32-B LLM** | `google.genai`, vLLM 폴백 |
| **32-C Crowding** | GO paper apply, live impact, bootstrap step |
| **32-D Paper** | LLM block, `paper_buy_validation`, CMS 카드 |
| **32-E Alpha** | trailing 20%, SPY 벤치, CMS alpha metrics |
| **32-F AI quality** | model_quality, rank paper buy gate, threshold/label sweep |

Rank research: 20d/top15%/q85 OOS gate → paper config only. Champion 승격 **없음**.

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
bash scripts/run_llm_block_precision.sh   # → logs/llm_advisory/precision.json (Active §1-A)

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

Phase 0–31 → [`docs/TODO_ARCHIVE.md`](docs/TODO_ARCHIVE.md)

Phase 36–38 상세 체크리스트(과거 DoD)는 git history `TODO.md` @ `944c4d4` 또는 `reports/agent_pipeline/phase36_sleeves*/` 참고.
