# AI-Driven Quant Trading Bot (2026 Edition)

[![CI](https://github.com/kimyounil1/trading-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/kimyounil1/trading-bot/actions/workflows/ci.yml)

본 프로젝트는 AI(LightGBM + XGBoost 앙상블)와 정성적 분석(LLM Consensus)을 결합한 지능형 Alpaca Paper Trading 봇입니다. 시장 레짐(BULL/BEAR/NEUTRAL)을 자동으로 감지하고, 이에 최적화된 동적 전략 프로필을 적용하여 안정적인 수익을 추구합니다.

## 🚀 주요 혁신 기능

### 1. 하이브리드 의사결정 엔진
- **정량 모델 (Ensemble AI)**: LightGBM과 XGBoost를 결합한 앙상블 모델이 24개 이상의 피처(기술적 지표, 옵션 시장 tail risk, 매크로 지표)를 기반으로 매수 확률 점수를 산출합니다.
- **정성 모델 (LLM Consensus)**: Google **Gen AI SDK** (`google-genai`) + Gemini API로 최신 뉴스를 분석합니다. `GEMINI_API_KEY` 또는 `GOOGLE_API_KEY` 필요. 소송, 부정회계, 가이던스 하향 등 정량 모델이 놓치기 쉬운 펀더멘털 리스크를 감지하여 최종 승인을 결정합니다. (결과는 비용 절감을 위해 로컬 캐싱되며, Gemini 429/quota 시 로컬 vLLM 폴백을 지원합니다 — `LLM_VLLM_*` env, [`docs/runbook.md`](docs/runbook.md) §2.3.1.)

### 2. 시장 레짐 인지형 전략 (Regime-Aware)
- VIX 지수와 지수 추세를 조합하여 시장 상태를 **BULL / BEAR / NEUTRAL**로 분류합니다.
- 레짐별 독립 모델 가동 및 **Dynamic Profile**(예: BULL 시 공격적 집중 투자, BEAR 시 보수적 비중 축소)을 자동으로 전환합니다.

### 3. 고도화된 리스크 관리 (The Risk Engine)
- **ATR 기반 Adaptive Trailing Stop**: 종목별 변동성(ATR)에 맞춰 익절 라인을 유동적으로 조절하여 노이즈를 피하고 수익을 보존합니다.
- **Economic Event Guard**: FOMC, CPI, NFP 등 주요 경제 지표 발표 전후 윈도우에서 신규 진입을 제한하여 매크로 변동성 리스크를 회피합니다.
- **Concentration Guard**: 단순 Pairwise 상관관계를 넘어 포트폴리오 전체의 평균 상관도 및 클러스터링을 체크하여 특정 테마 쏠림을 차단합니다.
- **Time-based Exit**: 효율적인 자본 순환을 위해 일정 기간(기본 30일) 이상 횡보하거나 신호가 약화된 포지션을 강제 청산합니다.

### 4. 운영 안정성 (Execution Resilience)
- **Idempotency**: 모든 주문에 고유 `client_order_id`를 부여하여 중복 체결을 방지합니다.
- **Fail-Safe**: 네트워크 오류 발생 시 무리한 재시도 대신 안전하게 실행을 중단하고 알림을 발송합니다.
- **Comprehensive Audit**: 모든 주문 사유, 적용 프로필, AI 점수, LLM 판정 결과를 통합 로그로 기록하여 완벽한 사후 추적성을 보장합니다.

### 5. Paper 검증 & Rank AI gate (Phase 32–33)
- **Rank AI buy/add gate (paper)**: cross-sectional rank 모델로 신규 매수·추가매수만 필터 (`rank_ai_buy_gate_enabled`). 매도 로직은 변경 없음. Tier 규칙: [`docs/ai_authority_gates.md`](docs/ai_authority_gates.md)
- **Paper validation**: AI vs LLM agreement, SKIP 레이어(AI/LLM/rank), 2주 rank gate 누적 → `logs/paper_validation/`
- **신호 검증 리포트**: rank forward-return, LLM block precision, paper validation trend (Phase 33)
- **일일 paper ops**: 평일 21:45 ET systemd timer → dry-run + bootstrap + 리포트 갱신

### 6. 포트폴리오 슬리브 & 증거 루프 (Phase 36–39 + 2026-07)
- **슬리브 분할**: core 50% (rank gate 전략) / **tournament 30%** (알파 모델 집중 베팅, 최대 35% 포지션·14일 보유·노가드) / cash 20% — 레지스트리·드리프트 트림·할당 리밸런스 포함
- **증거 루프 3종** (판단은 감이 아니라 데이터로):
  - 슬리브 성과 데일리 (`logs/sleeves/`) — 실현/미실현 P&L·승률, 배분 조정 근거
  - 마켓 레짐 스냅샷 데일리 (`logs/market_regime/`) — BULL/BEAR 판정 + **전환 시 Telegram 알림**
  - 시뮬-페이퍼 갭 어트리뷰션 주간 (`logs/sim_paper_gap/`) — 가드별 기회비용, 슬리브 예산 완화 판정 규칙(8주 연속) 사전 등록
- **리서치 결론 (2026-06/07)**: 유니버스 확대·피처 추가(실적/뉴스/gap_vol)·레짐 게이트 전부 게이트 기각 — 남은 수익 레버는 자본 배치 판단(~09월). 상세: [`docs/TODO_ARCHIVE.md`](docs/TODO_ARCHIVE.md)

## 📂 프로젝트 구조

```text
trading-bot/
├── app/                # Streamlit CMS 대시보드
├── config/             # 전략 프로필 및 시스템 설정 (JSON)
├── data/               # 피크 정보, LLM 캐시, 트레일링 스탑 데이터
├── logs/               # 실행 감사(Audit), 주문, 신호 로그 (대부분 gitignore; 일부 summary만 추적)
├── models/             # 챔피언 모델 (로컬, git 미추적 — retrain·승격 후 생성)
├── scripts/            # 실행, 서비스 등록 및 에이전트 오케스트레이터
│   ├── run_daily_paper_ops.sh      # 일일 paper bootstrap (timer entrypoint)
│   ├── run_paper_ops_bootstrap.sh  # dry-run + LLM/rank/validation 리포트
│   ├── run_pass_complete.sh        # pytest + Codex scoped review
│   └── run_bot_once.sh               # 봇 단발성 실행
├── src/                # 핵심 로직 (Python 3.11+)
│   ├── main.py         # 메인 트레이딩 루프
│   ├── rank_ai_gate.py # Rank AI paper buy/add gate
│   ├── paper_buy_validation_report.py
│   └── llm_analyst.py  # Gemini LLM 분석 및 캐싱
└── tests/              # 유닛 및 E2E 테스트 스위트
```

### Git에 없는 것 (clone 후 로컬 생성)
| 경로 | 생성 방법 |
|------|-----------|
| `models/ai_score_model.joblib` | `bash scripts/run_retrain.sh` 또는 `PYTHONPATH=. .venv/bin/python -m src.train_ai_model` |
| `logs/ml/.../rank_models.joblib` | `PYTHONPATH=. .venv/bin/python -m src.rank_label_experiment --output-dir logs/ml/rank_label_experiment_h20_top15_q85` |
| `data/raw/{ticker}/*.csv` | yfinance 자동 캐시 (`src/data_loader.py`) |
| `logs/paper_ops/`, 대부분 `logs/*` | `bash scripts/run_daily_paper_ops.sh` |

Champion·rank 모델은 **코드로 재생성** 가능. 바이트 단위 복제가 필요하면 `models/`·실험 폴더를 rsync/scp.

## 🤖 AI Agent Harness (Cursor-First)

코드 구현·리뷰는 **Cursor-first** 워크플로를 사용합니다.

| 역할 | 담당 | 규칙 문서 |
|------|------|-----------|
| **Cursor** | 메인 구현 (~60–70%) | [`CURSOR.md`](CURSOR.md) |
| **Codex** | read-only 리뷰, `NEXT_TODO` (~15–20%) | [`AGENTS.md`](AGENTS.md) |
| **AGY** | **`[Research]`** 오프라인 실험 · **`[AGY-test]`** pytest · **`[AGY-risk]`** 전략 리뷰 (~15–25%) | [`AGY.md`](AGY.md) |
| **Gemini CLI** | 레거시·문서만 (~0–5%, 테스트 금지) | [`GEMINI.md`](GEMINI.md) |

**평소 흐름**

1. **런타임:** Cursor `[Cursor]` 구현. **리서치(§4–§5):** AGY `[Research]` → Cursor 런타임 연결/채택
2. 넓은 조사는 Cursor **서브 에이전트**(`explore` 등, read-only) 병렬 탐색 — [`CURSOR.md` §7](CURSOR.md#7-cursor-sub-agents-in-session)
3. **AGY** `[AGY-test]` pytest 슬라이스 → `pytest` green
4. **패스 마감 (필수):** `RUN_ID=my_feature bash scripts/run_pass_complete.sh`
5. `reports/agent_pipeline/<run_id>/NEXT_TODO.codex.md` 확인 후 Cursor follow-up
6. 전략/리스크 대형 diff → AGY `[AGY-risk]` 리뷰 (Codex 대체 아님)

작업량 비율: `PYTHONPATH=. .venv/bin/python scripts/agent_workload_report.py --record` (커밋 메시지 `[cursor]` / `[agy]` 태그)

상세: [docs/agent_review_harness.md](docs/agent_review_harness.md) (구 [gemini_codex_harness.md](docs/gemini_codex_harness.md))

## 🛠 시작하기

### 환경 설정
- **Python 3.11+** (로컬 `.venv`는 3.12 권장)
- `.env.example`을 복사해 `.env` 생성 — Alpaca API Key, `GEMINI_API_KEY` 또는 `GOOGLE_API_KEY`
- clone 직후 champion 모델 없음 → 아래 **Git에 없는 것** 표 참고

### 가상환경 구축 및 실행
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 드라이런 (주문 미제출)
PYTHONPATH=. .venv/bin/python src/main.py

# Paper Trading 실행
PYTHONPATH=. .venv/bin/python src/main.py --execute
```

### 일일 paper ops (Rank/LLM 검증 누적)
```bash
# 수동 1회
bash scripts/run_daily_paper_ops.sh

# systemd timer (평일 21:45 America/New_York)
bash scripts/install_paper_daily_timer.sh
systemctl --user enable --now trading-bot-daily-paper-ops.timer
systemctl --user list-timers trading-bot-daily-paper-ops.timer

# 로그아웃 후에도 timer 유지 (WSL/서버)
loginctl enable-linger $USER

# timer/linger 상태 점검
bash scripts/check_paper_daily_timer.sh
```

### 검증·리포트 (Phase 33)
```bash
bash scripts/run_paper_buy_validation.sh      # → logs/paper_validation/latest_summary.json
bash scripts/run_paper_validation_trend.sh  # → logs/paper_validation/trend_summary.json
bash scripts/run_rank_gate_forward_return.sh
bash scripts/run_llm_block_precision.sh
bash scripts/run_rank_ai_gate_report.sh
bash scripts/run_crowding_gate_reassessment.sh
bash scripts/run_regime_weakness_report.sh
bash scripts/run_model_quality_report.sh
bash scripts/run_live_readiness.sh   # live GO/NO_GO (Phase 34)

# 슬리브 · 증거 루프 (2026-07)
bash scripts/run_sleeve_performance_report.sh                       # 슬리브별 P&L/승률
bash scripts/run_portfolio_pnl_report.sh                            # paper P&L (FIFO realized)
PYTHONPATH=. .venv/bin/python -m src.market_regime_snapshot         # 레짐 스냅샷 (데일리 자동)
bash scripts/run_weekly_gap_attribution.sh                          # 갭 어트리뷰션 (일 18:00 ET 타이머)
```

Live execute (double confirm): `TRADING_ENV=live CONFIRM_LIVE_TRADING=YES_I_UNDERSTAND PYTHONPATH=. .venv/bin/python src/main.py --execute`

요약 대시보드: `bash scripts/run_cms.sh` · paper ops: `logs/paper_ops/latest_summary.json` · live readiness: `logs/live_readiness/latest_summary.json`

### 테스트 · CI
```bash
# 전체 테스트 (로컬 = CI와 동일)
.venv/bin/python -m pytest tests/ -q
```
PR/push 시 GitHub Actions가 `requirements.txt` 설치 후 pytest·CMS import·deploy-gate를 실행합니다.

**Run frequency**: `bash scripts/compare_run_frequency.sh` → `logs/run_frequency/run_frequency_comparison.json`

로드맵·활성 TODO: [`TODO.md`](TODO.md) · AI 권한 Tier: [`docs/ai_authority_gates.md`](docs/ai_authority_gates.md)

## 📊 현재 성과·상태 (2026-07-07)
| 영역 | 요약 |
|------|------|
| **Paper P&L (Alpaca)** | all-time **+3.2%** ($103.2k) — 흑자 전환. 6월 한 달 **+5.1%** vs SPY **−0.9%** — `logs/portfolio_pnl/` |
| **Sleeves** | tournament **+$5.5k** (승률 100%, 6/9 가동) vs core **−$2.3k** — 4주 표본, 배분 판단 ~09월 |
| **Market regime** | **BULL** (최근 60일 중 50일) · 데일리 스냅샷 + 전환 알림 — `logs/market_regime/` |
| **Rank AI (paper)** | buy/add gate ON · `rank_gate_ready` **true** (14/14, 2026-06-16) |
| **LLM (paper)** | blocking mode · 20d 기준 reject −4.1% vs accept +0.5% 실증 — `logs/llm_advisory/precision.json` |
| **Crowding** | `crowding_max_positions` **3** (06-16 적용, 유지) — 가드 기회비용은 주간 갭 어트리뷰션으로 계측 |
| **Research** | 레버 전수 검증·기각 (2026-06/07) — 상세 [`docs/TODO_ARCHIVE.md`](docs/TODO_ARCHIVE.md) |

⚠️ 백테스트 시뮬의 "+30%p gap"은 라이브 기대치가 아님 — 동일 윈도우 비교에서 실제 paper가 무제약 시뮬을 상회 (`logs/sim_paper_gap/`).
