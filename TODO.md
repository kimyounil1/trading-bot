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

## Current Status (2026-06-12)

| 영역 | 상태 |
|------|------|
| **Alpha** | trailing 20% · 전략 **+76.1%** vs EW **+67.1%** (gap **+9.0pp**) · SPY **+28.9pp** (`logs/benchmark_gap/latest_summary.json`) |
| **Crowding** | config **ON** · reassessment `DISABLE_OR_KEEP_OFF` (blocked_trades=0) |
| **Paper ops** | daily timer active · `logs/paper_ops/latest_summary.json` |
| **LLM (paper)** | blocking mode · Gemini 429 간헐 · **precision 리포트 stale** (`precision.json` 6/2 이후 미갱신, `llm_reject n=0` 오탐) |
| **Rank AI (paper)** | buy/add gate ON · `rank_gate_ready` false — **~10/14일 · ~4일 남음** |
| **Live readiness** | **블로커 3건** — LLM precision · data_health ^VIX 오탐 · (연쇄) LLM verdict 파싱 |
| **Champion AI** | **유지** — promotion gate 미통과. **모델 품질:** Brier **0.323** (CV rebuild) · isotonic OOF **0.244** (`calibration_experiment` ok) · fold std 0.0695 · champion 승격은 여전히 블로커 |
| **Portfolio sleeves** | ON (core 50 / tournament 30 / cash 20) · registry + drift trim + allocation rebalance |
| **Research (shipped)** | regime/intraday/guard/rank gates 결론 반영 (`b9f4f6c`) · stop5_trail10 paper trial **대기** · **전략 레이어 연구 소진 → 다음 헤드룸은 모델 품질 (Active §4)** |

**마일스톤:** Rank 2주 관측 종료(~4일 후) 시점에 live readiness가 **시간 조건만** 남도록 **1→2→3** 선행. 모델 품질 트랙(§4)은 오프라인 리서치라 paper config 불변 — Rank 관측·stop trail 트라이얼과 **병행 가능**.

---

## Active — 지금 할 일

우선순위 순.

### 1. Live readiness 블로커 (완료 — 2026-06-11)

`run_live_readiness.sh` NO_GO 사유는 이제 **시간 조건 2개만** (rank 14d · validation 14d). 상세는 Follow-up backlog 참조.

| # | 항목 | 상태 | 비고 |
|---|------|------|------|
| **1-A** | **LLM precision 리포트 수리** | [x] | blocking 모드 REJECT 집계 + dedupe + 단기 5d horizon + bootstrap 연결 → reject=15/accept=82 |
| **1-B** | **data_health ^VIX 오탐** | [x] | 변동성 지수 전용 `max_daily_jump` 1.5 → **GO** |
| **1-C** | **LLM verdict 파싱 정리** | [x] | `parse_llm_decision` — 마지막 DECISION 블록 채택 + reason 클립. CoT 'APPROVE' 언급 오승인 버그 수정 |

---

### 2. Phase 32 — Rank AI paper 관측 (시간 대기)

**Toss(32-A)는 API 키 전까지 보류.**

| # | 항목 | 상태 |
|---|------|------|
| 1 | **Rank AI paper 2주** — 매일 bootstrap → `logs/paper_validation` · `rank_gate_ready=true` | [ ] 진행 중 (~10/14 calendar days, **~4일 남음**) |
| 2 | **Paper validation 추세** — rolling agreement · SKIP 레이어 관찰 · rank/LLM spike alerts | [x] |
| 3 | Codex scoped review `phase32_retry` | [x] |

**하지 말 것** ([`docs/ai_authority_gates.md`](docs/ai_authority_gates.md))

- `models/ai_score_model.joblib` champion 교체
- Rank gate **live** 기본 ON (Tier-1 paper 2주 전)

---

### 3. Research — stop5_trail10 paper trial

백테스트 follow-up (`regime_stop_backtest --followup`): 수익 **-0.2pp**, MDD **-9.4%→-6.3%**. 레짐 adaptive와 무관.

| # | 항목 | 상태 |
|---|------|------|
| 1 | `trailing_stop_pct` 0.20→**0.10** paper config trial | [x] **2026-06-12 시작** — `strategy_config.json` 반영 · `src/stop_trail_trial_report.py` + `run_stop_trail_trial_report.sh` (`--start` 완료) · bootstrap 8d 연결 |
| 2 | 2주 paper 관측 — return vs MDD vs baseline (`logs/stop_trail_trial/latest_summary.json` · `READY_TO_EVALUATE` ~06-26) | [ ] 진행 중 |
| 3 | 평가 후 결정: 유지(MDD 개선·수익 drag ≤ -0.2pp) 또는 **0.20 롤백** | [ ] blocked until 2 |

---

### 4. Research — 모델 품질 트랙 (성능 개선 1순위)

**배경 (2026-06-12 탐색):** 전략 레이어(레짐 스탑·장중 타이밍·할당 방식 MVO/BL·rank label 스윕)는 결론 완료 — 대부분 채택 기준 미달. 남은 헤드룸은 **모델 품질**. 챔피언 ROC-AUC 0.5075(동전 수준)이며, Brier·fold std·약세 레짐 3개 블로커가 champion 승격과 authority 확장을 막고 있음. 오프라인 리서치이므로 paper config 불변 — §2·§3 관측과 병행 가능.

| # | Owner | 항목 | 상태 | 작업 내용 |
|---|-------|------|------|----------|
| **4-A-R** | `[Research]` | **캘리브레이션 실험·리포트** | [x] | `ml_quality_report --rebuild-calibration-rows` → `model_calibration_rows.csv` (70k rows) · `calibration_experiment` **ok** — isotonic OOF Brier **0.244** (base 0.321) · `run_model_quality_report.sh` auto-rebuild if rows missing |
| **4-A-C** | `[Cursor]` | **캘리브레이션 런타임 연결** | [x] | `predict_ai_score_from_bundle` + `ai_score_calibration_enabled` (**default-off**) · bins `logs/ml/model_calibration_bins.csv` |
| **4-B** | `[Research]` | **약세 레짐 피처 실험** | [x] | `regime_feature_experiment.py` · `run_regime_feature_experiment.sh` — **BULL** weak only · best baseline AUC **0.495** · **게이트 미통과** (≥0.52) · report-only 유지 |
| **4-C** | `[Research]` | **Fold 안정성 (variance 축소)** | [x] | `fold_stability_experiment.py` · `run_fold_stability_experiment.sh` — BULL `xgb_reg_0.5` std **0.005** (gate pass) · BEAR/NEUTRAL 여전히 >0.05 · label challenger 검토만 |

**순서:** 4-A-R → 4-A-C → `[AGY-test]` (스키마·연결 회귀) → Codex. 각 항목 DoD: pytest + 리포트 산출물 + scoped review.

---

### 5. Research — 미스윕 파라미터 (2순위)

한 번도 스윕된 적 없는 하드코딩 파라미터. 기존 `portfolio_backtester` 재사용.

| # | Owner | 항목 | 상태 | 작업 내용 |
|---|-------|------|------|----------|
| **5-A** | `[Research]` | **진입 시그널 스윕** | [ ] | `ma_fast`(5–30) × `ma_slow`(30–100) × `rsi_buy_limit`(40–75) 그리드 — `research_promotion_gates.py` OOS 기준(gap≥0pp·Sharpe≥1.0) + 채택 임계 **+0.5pp**. train/OOS 분리 필수 |
| **5-B** | `[Research]` | **사이징·익절 스윕** | [ ] | `conviction_position_mult_max`(1.0–1.5) · `take_profit_partial_pct`(0.10–0.25) · `partial_exit_ratio` · `max_holding_days`(20–60) — 동일 백테스터·동일 채택 기준 |
| **5-adopt** | `[Cursor]` | **채택 시 config 반영** | [ ] | 스윕 pass 시에만 — `run_research_promotion_gates.sh` 경로로 paper config 반영 (자동 반영 금지) |

**주의:** 5-A/5-B는 AGY `[Research]` 세션. 채택은 5-adopt `[Cursor]`만.

---

### 6. Backlog (차단·대기·낮은 우선)

| 항목 | 상태 | 비고 |
|------|------|------|
| **Toss Open API** (Phase 33) | [ ] blocked | API 키·스펙 대기 |
| **Live 전환** (Phase 34 foundation 완료) | [ ] blocked | §1 블로커 해소 + Rank 2주 + operator sign-off |
| **Champion / rank live 승격** | [ ] blocked | AI authority gates |
| **Gemini 429 quota 대응** | [ ] | 간헐 발생 · retry/backoff/degraded mode 강화 |
| **Tournament sleeve 성과 리포트 자동 판정** | [ ] | `run_tournament_score_report.sh` → pass/fail 요약 |
| **Untracked logs 정리** | [ ] | `logs/ml/rank_label_experiment_*` 등 `.gitignore` 정리 |
| **LLM×AI 불일치 시그널 연구** | [ ] | score↔llm r=0.031 직교 (`logs/llm_ai_comparison`) — 불일치(AI pass + LLM fail) 시 포지션 축소 연구. 낮은 우선 |

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

# Research gates
bash scripts/run_research_promotion_gates.sh
bash scripts/run_regime_stop_backtest.sh --followup
PYTHONPATH=. .venv/bin/python -m src.ml_quality_report --rebuild-calibration-rows  # §4-A rows
bash scripts/run_model_quality_report.sh   # calibration experiment + model_quality summary
bash scripts/run_regime_feature_experiment.sh   # §4-B
bash scripts/run_fold_stability_experiment.sh   # §4-C

# Phase pass (Codex)
RUN_ID=phase39_sleeve_alloc bash scripts/run_pass_complete.sh
SKIP_CODEX=1 RUN_ID=phase39_sleeve_alloc bash scripts/run_pass_light.sh

bash scripts/run_cms.sh
```

---

## Archive pointer

Phase 0–31 → [`docs/TODO_ARCHIVE.md`](docs/TODO_ARCHIVE.md)

Phase 36–38 상세 체크리스트(과거 DoD)는 git history `TODO.md` @ `944c4d4` 또는 `reports/agent_pipeline/phase36_sleeves*/` 참고.
