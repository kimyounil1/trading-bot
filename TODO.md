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

## Current Status (2026-07-15)

### AI/백테스트 정렬 작업 (07-14)

| # | 항목 | 상태 | 비고 |
|---|------|------|------|
| AI-BT-1 | **운영 AI 점수와 백테스터를 당일 인과적 피처·당일 레짐으로 단일화** | [x] 완료 (07-14) | 기존 운영의 label horizon 20거래일 지연과 기존 BT의 마지막 레짐 과거 전체 적용 제거. 단일 inference 경로·point-in-time 레짐 및 전체 회귀 테스트 통과 |
| AI-BT-2 | **운영형 백테스트 parity** | [x] 완료 (07-14) | 직접 2배 상품→본주 fallback, VIX/노출 제한, 상관·crowding·sector guard의 as-of 데이터, 부분익절, 현금 하한, non-fractionable, 동적 유니버스/Rank 횡단면, core/tournament/cash 예산 분리 반영 |
| AI-BT-3 | **월별 성과 원인 분석 자동화** | [x] 완료 (07-14) | 매 BT 저장 시 `monthly_attribution.csv` + `monthly_review_queue.md` 생성. 손실/벤치마크 미달 월은 최악 종목·슬리브·청산 사유·2배/본주 실현손익을 기록 |
| AI-BT-4 | **Rank-primary 운용 조합 승격** | [x] paper 채택 (07-14) | Rank 모델을 MA·기존 AI 뒤의 보조 게이트가 아닌 상위 15% 주 선택기로 사용. Rank-only 토너먼트 정렬, 손절 10%·익절 20%·트레일링 40%·최대 30일·부분익절 OFF. 실주문/서비스 재시작은 별도 승인 |

#### 07-14 Rank-primary 채택 검증

- 원인: Rank 모델 자체 OOS AUC는 **0.611**이었지만, 기존 MA·방향성 AI·동적 청산을 앞에 겹쳐 2026 전체 수익이 **-3.31%**까지 낮아졌다. Rank 원형 운용은 같은 모델로 +41.76%여서 모델 교체보다 통합 조건 불일치가 핵심이었다.
- 선별(2025-12-01~2026-05-01): **+28.52%**, B&H **+9.73%**, MDD **-12.79%**, Sharpe **1.74**.
- 미사용 forward(2026-05-04~07-13): **+13.66%**, B&H **+8.47%**, MDD **-12.84%**, Sharpe **1.96**.
- 전체(2026-01-01~07-13): **+53.26%**, B&H **+15.72%**, MDD **-16.48%**, Sharpe **2.08**, 최종 **$15,325.80**(초기 $10,000).
- 월별 후속: 3월 **-2.21%**, 5월 전략 +6.31%이나 B&H 미달, 6월 **-0.33%**. `logs/portfolio_backtest_rank_primary_final_2026/monthly_review_queue.md`에서 손절·ANET·CONL 및 슬리브 기여를 paper 체결과 대조한다.
- 제한: 과거 LLM/뉴스 판정, cross-sleeve 동일 종목/주문 경합, 장중·확장시간 체결 및 브로커 거절은 완전 재현하지 않는다. 따라서 paper 설정만 채택하고 live 승격은 계속 차단한다.

#### 07-14 Rank 개선 재검증

- 최신 캐시에 빈 장중 OHLCV placeholder가 있으면 추론이 20거래일 지연되던 문제를 수정했다. 공용 inference 경로가 완성된 마지막 봉까지만 사용하며 회귀 테스트를 추가했다.
- 사전 선별 구간까지만 학습한 후보를 현재 슬리브·직접 2배 상품·청산 설정으로 재생했다. 최신 기본 재학습은 선별 **-7.22%** / forward **+16.09%** / 2026 전체 **+4.98%**, LambdaMART Ranker는 **+14.40% / +5.21% / +11.17%**, 재학습·Ranker 혼합은 **-7.45% / +19.15% / +19.89%**로 현재 모델의 **+28.52% / +13.66% / +53.26%**를 일관되게 넘지 못했다.
- 절대수익·하방위험 보조 게이트는 단순 OOS 포트폴리오를 악화시켜 탈락했다. 현재 모델 원점수 하한 0.40/0.42는 실제 진입을 바꾸지 못했고, 0.44는 전체 수익을 **+52.35%**로 낮춰 기각했다.
- 결론: 운영 Rank 모델·상위 15% 설정은 유지한다. 후보 모델은 연구 산출물로만 보존하며 승격하지 않는다. 상세 결과는 `logs/ml/rank_ai_v2_experiment_20260714/`과 `logs/ml/rank_quality_guard_validation_20260714_cleaned/`에 있다.

#### 07-15 Rank 품질별 위험 배율 검증

- Rank 순서와 모델은 유지하고 진입 위험만 조정하는 공통 운영·백테스트 오버레이를 추가했다. 고점 대비 25% 이상 하락과 `SMA20 < SMA200` 중 한 조건 불량은 진입금액 50%, 두 조건 불량은 25%로 줄이며, 두 조건 모두 불량하면 직접 2배 상품 대신 본주로 진입한다.
- 기존 31개 직접 2배 라우팅을 고정한 OOS 비교에서 기준선 대비 선별 **+28.52% → +31.66%**, forward **+13.66% → +17.07%**, 2026 전체 **+53.26% → +59.86%**로 개선됐다. 전체 MDD는 **-16.48% → -13.55%**, Sharpe는 **2.08 → 2.50**으로 개선됐다.
- 오늘 발견된 35개 라우팅에서도 선별 **+14.68% → +31.76%**, forward **+16.50% → +17.28%**, 전체 **+60.79% → +60.01%**로 수익을 거의 유지하면서 MDD **-18.04% → -13.62%**, Sharpe **2.15 → 2.51**을 기록했다.
- paper 적용 설정만으로 2026-01-02~07-13을 다시 실행해 **+60.01%**, MDD **-13.62%**, Sharpe **2.506**, 최종 **$16,001.32**, 569건을 동일하게 재현했다. 결과는 `logs/ml/rank_quality_risk_overlay_20260715/applied_config_validation/`에 보존한다.
- 제한: 전체 거래 수가 31개 라우팅 기준 **369 → 569**로 증가했고 1~3월 월별 성과는 소폭 악화됐다. 주문 경합·최소 주문금액·추가매수 배율과 실시간 2배 라우팅 동등성을 공통 정책으로 구현해 paper 설정에 적용했다. 상세 결과는 `logs/ml/rank_quality_risk_overlay_20260715/`에 있다.

#### 07-15 이후 순수 forward paper 검증

- `BUY_PLAN`과 동일 설정 백테스트의 `portfolio_entries.csv`를 시장일·슬리브·원종목 기준으로 매일 비교한다. 라우팅, 100%/50%/25% 배율, 레버리지 허용, 주문 비중, 체결률·슬리피지·운영 오류를 `logs/paper_backtest_parity/`에 누적한다.
- 최소 **20거래일**과 실제 매수 계획 **30건**이 쌓이기 전에는 Rank 모델·컷·품질 배율을 다시 조정하지 않는다.
- 1차 통과 기준: 정책 동등성 95% 이상, 치명적 주문 오류 0건, 불리한 매수 슬리피지 60bps 이하. 후보 일치율은 실계좌와 시뮬레이션 보유상태 차이를 함께 기록해 해석한다.
- 월말에는 손실 종목, 미체결/거절, 백테스트 전용 후보와 paper 전용 후보를 원인별로 분류한 뒤 미사용 구간 검증을 통과한 변경만 채택한다.

#### 07-15 가드 캡 스윕 — 섹터 캡 2→4 채택

- 라이브 반사실(`logs/guard_gates/`)과 paper 정합 sleeved 백테스트 스윕(`scripts/exp_guard_cap_sweep.py`, `logs/guard_cap_sweep/`)이 같은 방향을 가리켰다: 섹터 캡이 상승 종목을 막는다. 스윕(2026-01-02~07-14, 기준선 +60.01% 재현): 캡3 **+66.02%**/MDD -11.51%, 캡4 **+69.46%**/MDD **-10.94%**, 해제 +58.53%(선별 구간 악화로 기각). forward(05-04~) 구간도 17.7→18.1%로 개선. **07-15 max_sector_positions 2→4 적용.**
- 크라우딩 가드는 **유지**: 라이브 반사실은 유효(차단 종목 h10 SPY -2.8%p), 백테스트는 해제 시 +71.9%로 충돌. 개별 종목 수익과 포트폴리오 효과가 다른 것을 측정하므로 증거 불일치로 기록하고 미조정.
- 랭크 컷오프(top 10/15/20/30%)는 **전 시나리오 결과 동일 = non-binding 판정**: 후보가 percentile 내림차순 정렬 후 슬롯 수만큼만 선택되므로 컷이 아니라 슬롯/예산이 병목. 라이브 percentile 비단조성 발견의 실질 영향 낮음. 컷 조정 카드 종결.
- LLM 게이트는 백테스트 재현 불가(누출 없는 과거 판정 부재) — 라이브 반사실 축적으로만 판정(~08월).

### 월별 손익 리뷰 — 반복 TODO

월별 리뷰는 결과를 보고 즉시 설정을 바꾸는 절차가 아니다. 원인 확인 → 수정안 백테스트 → 미사용 기간/forward 검증 → 채택 또는 기각 기록 순서를 지킨다.

| 주기 | TODO | 완료 조건 |
|------|------|----------|
| 매월 첫 거래일 | 전월 수익률·Buy & Hold 대비·MDD·슬리브별 손익 확인 | `monthly_attribution.csv`와 실제 paper P&L 대조 |
| 손실 월 발생 시 | 시장 하락 동반 여부, 손절 연속 구간, 최악 종목/섹터, AI·Rank 점수 구간, 2배 상품과 본주 차이 분석 | `monthly_review_queue.md`의 원인 확인 체크 |
| 수정안 생성 시 | 진입 cutoff, 레짐 필터, 손절/익절, 보유기간, leverage fallback 중 원인과 직접 관련된 변경만 후보화 | 변경 이유·예상 부작용·비교 기준 기록 |
| 수정안 검증 시 | 같은 기간 재최적화에 그치지 않고 OOS 또는 다음 forward 기간 검증 | 수익·MDD·Sharpe·회전율·Buy & Hold gap 동시 비교 |
| 판단 완료 시 | 채택/기각과 근거를 월별 queue 및 archive에 기록 | 단일 손실 월만으로 자동 채택 금지 |

남은 fidelity 점검: 과거 LLM/뉴스 판단 데이터의 완전성, cross-sleeve 동일 종목/주문 경합, 장중·확장시간 체결, 실제 브로커 주문 거절·미체결을 별도 execution replay에서 검증한다.

| 영역 | 상태 |
|------|------|
| **Paper P&L (Alpaca)** | all-time **+3.2%** ($103.2k) — **흑자 전환**. 6월 한 달 **+5.1%** vs SPY **−0.9%** vs 무제약 시뮬 복제 **+0.2%** (`logs/sim_paper_gap/`) |
| **Sleeves** | tournament **+$5.5k** (승률 100%, 6/9 가동) vs core **−$2.3k** (승률 49%) — 4주 표본, 배분 변경은 ~09월 판단 |
| **Market regime** | **BULL** (최근 60일 중 50일) · SPY 고점 −0.8% · 폭 건강(50MA 위 65%) · 데일리 스냅샷 + 전환 알림 가동 (`logs/market_regime/`) |
| **Research** | **리서치 카드 소진** — 유니버스 확대·gap_vol·실적 피처·VADER 뉴스·레짐 게이트·LLM 소급 스코어링 모두 게이트 기각. Rank 재학습/Ranker/보조 게이트도 현 모델을 넘지 못해 미승격 |
| **계측 (증거 루프)** | ① sleeve 성과 데일리 ② 레짐 스냅샷 데일리 ③ 갭 어트리뷰션 주간 ④ paper↔동일 설정 BT 진입 동등성 데일리(평일 23:30 ET) |
| **버그 수리/검증** | ATR 단기 히스토리 · sleeve 리포트/트림 · 주문 수량/중복 ID · AAPL 피처 키 · 최신 미완성 봉 · Rank/BT 동등성 경로 보강 · 전체 테스트 **595 green** |
| **Crowding A/B (06-16, 2→3)** | **3 유지** — 6월 차단 종목 사후수익 ~중립, 주간 어트리뷰션이 가드별 기회비용 계측을 대체 (별도 평가 종결) |
| **LLM (paper)** | blocking veto 유지 — 20d 기준 reject −4.1% vs accept +0.5% 실증. Gemini 무료티어 **일 20콜** 위에서 운영 중 (유료 전환 시 안정화) |
| **Live readiness** | 시간 조건 충족 + **paper 흑자 전환 달성** — 지속성 관측 후 operator sign-off 논의 가능 |

**현 국면:** "만들고 고치는" 단계 → **"운영하고 판단하는"** 단계. 새 리서치 없이 증거 루프가 9월 판단(슬리브 배분·예산 완화)의 데이터를 쌓는 중.

---

## Active — 지금 할 일

우선순위 순.

### 1. 진행 중 (2026-07-15~)

| # | 항목 | 상태 | 비고 |
|---|------|------|------|
| 1-A | **Rank 품질 오버레이 순수 forward 검증** | [ ] 수집 중 | 20거래일·실제 `BUY_PLAN` 30건 전까지 재튜닝 금지. `paper_backtest_parity`의 정책 동등성 ≥95%, 치명적 주문 오류 0, 불리한 매수 슬리피지 ≤60bps 확인 |
| 1-B | **paper↔백테스트 불일치 원인 분류** | [ ] 데일리 자동 | 후보 누락, 라우팅, 100/50/25% 배율, 2배 허용, 주문 비중, 미체결/거절을 시장일·슬리브·원종목 기준으로 기록 |
| 1-C | **월별 손익 리뷰** | [ ] 월별 반복 | 손실/B&H 미달 월만 원인 확인 후 별도 OOS/forward 검증. 단일 손실 월을 근거로 설정 자동 변경 금지 |

### 2. 예정된 판단 (증거 축적 대기 — 손대지 말 것)

| 시점 | 판단 | 근거 데이터 |
|------|------|------------|
| **~2026-09 초** | 토너먼트 배분 30%→확대 여부 | `logs/sleeves/history.jsonl` 8주+ (07-06 이전 기록은 0-버그, `portfolio_value>0` 필터) |
| **~2026-09 초** | core 슬리브 예산 +15% A/B 착수 여부 | `logs/sim_paper_gap/trend_summary.json` — **사전 등록 규칙(8주 연속 플래그) 고정, 중간 수정 금지** |
| **~2026-09 초** | **cash 목표 20% 축소 검토** (예산 A/B와 패키지) | 오프라인 스윕 완료 (07-08, `logs/cash_floor_sweep/`): **20%가 0%/10%를 Sharpe·MDD에서 압도, 12m에선 수익도 +2.2pp 우위 · 30%는 12m 붕괴(비단조)** → 사전 기대는 "20% 유지". 9월에 어트리뷰션 실측과 합산 최종 판단 |
| **레짐 전환 알림 시** | 노가드 토너먼트 재평가 | `logs/market_regime/` — BULL 이탈 시 텔레그램 알림 |
| **20거래일·30 BUY_PLAN 충족 시** | Rank 품질 오버레이 유지/수정 판단 | `logs/paper_backtest_parity/` — 정책 동등성·주문 오류·슬리피지·후보 불일치 원인 |
| **paper 흑자 지속 시** | Live 전환 논의 재개 (Toss 키 보유) | `logs/portfolio_pnl/` + `run_live_readiness.sh` |

### 3. Backlog (낮은 우선 · 선택)

| 항목 | 상태 | 비고 |
|------|------|------|
| **Gemini 유료 전환** | [ ] 선택 | 라이브 veto가 무료티어 **일 20콜** 위에서 아슬아슬 (캐시 미스 → degraded PASS). 유료 시 ~$1/월 수준으로 해소 |
| **테스트 커버리지 보강** | [ ] 선택 | 실행 경로 중 테스트 0인 곳에서 버그 2개씩 나온 전례 (슬리브 트림). 후보: partial_exit·dust_exit·cash_surplus_deploy 경로에 fake-broker 회귀 테스트 |
| **BRK-B→BRK.B 뉴스 매핑** | [ ] 선택 | Alpaca 뉴스 심볼 표기 차이 — 뉴스 리서치 재개 시에만 |
| **LLM×AI 불일치 시그널 연구** | [x] 종료 | LLM 소급 스코어링 게이트 기각으로 추가 리서치 중단. 데이터셋만 재사용 가능 |
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
bash scripts/run_daily_paper_backtest_parity.sh --no-notify
systemctl --user status trading-bot-paper-backtest-parity.timer

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
