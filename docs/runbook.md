# 📘 Operational Runbook: AI Trading Bot

본 문서는 트레이딩 봇 운영 중 발생할 수 있는 주요 장애 시나리오와 대응 절차(SOP)를 정의합니다.

---

## ⚠️ 1. 긴급 중단 및 복구 (Kill Switch)

### 시나리오: 전체 포트폴리오 청산 및 중단
갑작스러운 시장 폭락이나 시스템 오작동 시 모든 포지션을 정리하고 봇을 중지해야 할 때:
1. **Systemd 타이머 비활성화**:
   ```bash
   systemctl --user stop trading-bot.timer
   systemctl --user disable trading-bot.timer
   ```
2. **수동 전량 청산**: Alpaca 대시보드에서 'Liquidate All' 버튼을 누르거나 아래 명령 실행:
   ```bash
   PYTHONPATH=. .venv/bin/python src/close_position.py ALL
   ```

---

## 🛠 2. 주요 장애 대응 절차

### 2.1 API 연결 및 타임아웃 오류
- **현상**: `ConnectionError`, `Alpaca Timeout`, `Gemini API quota exceeded` 알림 발생.
- **원인**: Alpaca 서버 점검, 로컬 네트워크 불안정, LLM API 사용량 초과.
- **대응**:
    1. 봇은 자동으로 실행을 중단(Fail-safe)하므로 중복 주문 걱정은 없음.
    2. 네트워크 상태 확인 후 수동으로 `src/main.py`를 실행하여 정상 동작 확인.
    3. LLM 할당량 초과 시 `config/strategy_config.json`에서 `llm_degraded_mode`를 `"PASS"`로 설정하여 정량 모델만으로 운용 가능.

### 2.2 Retrain 실패·부분 성공 (Stale Model)
- **현상**: 매일 아침 06:00 ET retrain 타이머 실패, 또는 학습은 됐으나 챔피언 유지.
- **Telegram 알림** (`src/train_ai_model.py`):
    - **실패**: `AI Retrain Failed` — `logs/retrain_history.csv`에 `status=failure` 기록.
    - **부분 성공**(학습·리포트 완료, 승격 없음): `Retrain finished; champion retained` — `logs/ml/model_promotion_report.json`의 `decision`이 `RETAIN_CHAMPION`.
    - **품질 경고**(학습 성공 중): feature drift, calibration(Brier), fold ROC 분산 — 각각 별도 `notify_info`.
    - **성능 저하**: 평균 ROC-AUC < 0.51이면 `AI Model Performance Degradation`.
- **대응**:
    1. `logs/retrain_runs/retrain_*.log` 및 `logs/retrain_history.csv` 확인.
    2. 데이터 소스(yfinance) 차단 여부 확인.
    3. `models/ai_score_model.joblib`은 **로컬 전용**(git 미추적). `model_promotion_report.json`에서 `decision=PROMOTE`일 때만 챔피언 파일을 교체하고, ROC-AUC < 0.51이면 커밋·배포하지 않음. 수동: `bash scripts/run_retrain.sh`.

### 2.3 Drawdown Circuit Breaker 발동
- **현상**: 포트폴리오 자산이 최고점 대비 15% 이상 하락하여 "New buys blocked" 알림 발생.
- **대응**:
    1. 현재 시장 레짐이 `BEAR`인지 확인.
    2. 포트폴리오 구성 종목의 개별 리스크(실적 악화 등) 재평가.
    3. 시장이 안정되었다고 판단되면 `config/strategy_config.json`의 `max_portfolio_drawdown_pct`를 일시적으로 상향 조정하여 가드 해제 가능.

### 2.3.1 LLM·뉴스 (AI + LLM 합의)

Paper/dry-run 기본: **`llm_advisory_only: false`** — AI 임계값 통과 **및** LLM APPROVE일 때만 매수 진행. dry-run도 캐시 미스 시 **live LLM** 호출(기본).

| `llm_advisory_only` | 동작 |
|---------------------|------|
| `false` (paper 기본) | LLM REJECT → `SKIP_BUY` (AI 통과해도 차단) |
| `true` | `LLM_ADVISORY` 로그만, 주문은 진행 (실험·비교용) |

| 환경 변수 | 동작 |
|-----------|------|
| (기본 dry-run) | cache miss → Gemini/vLLM 호출 |
| `LLM_CACHE_ONLY_DRY_RUN=1` | dry-run은 캐시만 (`llm_degraded_mode` 적용) |
| `TRADING_BOT_SKIP_LLM=1` | pytest/CI — LLM 가드 생략 |

pytest는 `tests/conftest.py`에서 `TRADING_BOT_SKIP_LLM=1` 자동 설정.

**나중에 수익 비교** (paper 누적 후):

```bash
bash scripts/run_bot_once.sh              # dry-run 또는 execute
bash scripts/run_llm_advisory_report.sh   # 따랐을 때 vs 무시한 매수 집계
```

산출물: `logs/llm_advisory/latest_summary.json`  
`buy_submitted_despite_llm_reject` = LLM은 거절했는데 실제로 산 건수. 체결 PnL까지 비교하려면 주문/체결 로그와 조인하는 후속 리포트가 필요.

백테스트 수익(+96% 등)은 **ML `ai_score`만** 반영. in-loop LLM 필터는 별도 실험용.

**운영에 가까운 in-loop 비교** (매수 직전 LLM+뉴스 필터, `portfolio_backtester`):

```bash
# 백테스트 진입일 기준 캐시 채우기 (중단 시 재실행 — 이미 있는 키는 스킵)
bash scripts/warm_llm_cache_from_backtest.sh

bash scripts/run_operational_alpha_validation.sh
LIVE_LLM=1 bash scripts/run_operational_alpha_validation.sh   # cache miss 시 Gemini 호출
```

산출물: `data/llm_cache.json`, `logs/llm_cache_warmup/latest_summary.json`, `logs/operational_alpha/latest_summary.json`  
워밍업은 진입일 키(`{티커}_{YYYY-MM-DD}`)로 저장. 당일 yfinance에 기사가 없으면 **현재 헤드라인 fallback**으로 Gemini 호출(완전한 과거 뉴스 아카이브는 아님). paper `main.py` 실행 시 같은 키로 캐시가 계속 쌓임.

**로컬 vLLM 서브모델 (Gemini quota/5xx 시)** — `src/llm_vllm.py` + `src/llm_analyst.py`:
- **기본 OFF** (`LLM_VLLM_ENABLED` 미설정 시 116/gemma4로 폴백하지 않음)
- 켜기: `.env`에 `LLM_VLLM_ENABLED=1`, `LLM_VLLM_BASE_URL=http://192.168.219.116:11434/v1`, `LLM_VLLM_MODEL=gemma4-26B`
- Gemini 429/500/quota 등 → (활성 시) 로컬 vLLM 호출; 캐시 `llm_provider: vllm`
- 점검: `PYTHONPATH=. .venv/bin/python -c "from src.llm_vllm import probe_vllm_models; print(probe_vllm_models())"`

⚠️ **Gemini 무료 티어 한도 (2026-07 실측):** 모델당 **일 20콜** (`gemini-2.5-flash`·`flash-lite` 각각 별도 쿼터). 라이브 veto가 이 한도 위에서 돌고 있어 캐시 미스가 몰리면 `llm_degraded_mode`(기본 PASS = 자동승인)로 넘어감 — veto 실효성이 필요하면 유료 전환(월 ~$1) 또는 vLLM 폴백 활성 권장. 대량 배치(소급 스코어링 등)는 반드시 vLLM으로: `scripts/llm_retro_scoring.py --provider vllm`.

```bash
bash scripts/run_paper_ops_bootstrap.sh   # dry-run + advisory + alpha + crowding gate (report only)
SKIP_ALPHA=1 bash scripts/run_paper_ops_bootstrap.sh   # model/alpha 없을 때 paper audit·crowding만
APPLY_CROWDING_CONFIG=1 bash scripts/run_paper_ops_bootstrap.sh   # GO일 때만 proposal merge
```

**일일 paper (rank/LLM 2주 검증 누적)** — 스케줄러 권장:

```bash
bash scripts/run_daily_paper_ops.sh   # dry-run + validation + rank gate + paper_ops (alpha/guard 생략)
bash scripts/install_paper_daily_timer.sh
systemctl --user enable --now trading-bot-daily-paper-ops.timer
# 기본: Mon..Fri 21:45 America/New_York (config/paper_daily_config.json)
# 로그: logs/paper_ops/daily_scheduler.log
```

### 2.3.2 Crowding guard (paper)

**현재 (2026-07-07):** `crowding_guard_enabled: true` · `crowding_max_positions` **2→3 적용 (06-16)** 후 유지.
6월 실측에서 크라우딩 차단 종목의 사후수익은 ~중립 — 가드별 기회비용은 **주간 갭 어트리뷰션**(§3)으로 상시 계측하므로 별도 A/B 평가는 종결.
재평가·롤백 시 guard impact 갱신 후 gate만 다시 실행; merge는 명시적일 때만. 롤백: `PYTHONPATH=. .venv/bin/python scripts/crowding_ab_gate.py --rollback`.

```bash
bash scripts/run_guard_impact_report.sh
bash scripts/run_crowding_paper_gate.sh   # logs/crowding_paper/go_no_go_checklist.json
bash scripts/run_crowding_paper_gate.sh --apply-config   # GO_PAPER일 때만 merge
# 또는 일괄:
APPLY_CROWDING_CONFIG=1 bash scripts/run_paper_ops_bootstrap.sh
```

| 지표 (백테스트 replay) | baseline | with crowding | delta |
|------------------------|----------|---------------|-------|
| Sharpe | 1.228 | 1.301 | +0.073 |
| Max DD % | -19.23 | -9.68 | +9.56pp |
| Return % | 55.49 | 50.38 | -5.11 |
| Blocked trades | — | 6 | — |

결정 기록: `logs/crowding_paper/decision_record.json`

**Live 모니터링** (dry-run/execute 후):

```bash
bash scripts/run_crowding_live_impact_report.sh --lookback-days 7
# → logs/crowding_live/latest_summary.json (by_kind, by_ticker, alignment vs backtest)
```

`paper_ops` 요약에 포함: `logs/paper_ops/latest_summary.json` → `crowding_live` 블록.

### 2.4 유니버스 프로필 (`UNIVERSE_PROFILE`)

| 프로필 | 스캔 풀 | 용도 |
|--------|---------|------|
| `paper` (기본) | `config/strategy_config.json` tickers | 운영·기본 백테스트 |
| `smoke` | `config/universe_smoke.json` (~11종) | pytest·빠른 로컬 검증 |
| `research` | `config/universe_master.csv` (255종 — 2026-07-06 죽은 티커 정리: SQ→XYZ, WRK→SW, ANTM·MMC·CKNG·SEE 제거) | 넓은 스캔·retrain 데이터 풀 |

```bash
# master CSV 일괄 캐시 (로컬, 시간 소요)
UNIVERSE_PROFILE=research PYTHONPATH=. .venv/bin/python -c "
from src.settings import load_settings
from src.data_loader import load_price_data_batch
s = load_settings()
load_price_data_batch(s.tickers, period='2y')
print(len(s.tickers), 'tickers cached')
"
```

**레버리지 ETF vs 마진 레버리지**
- **레버리지 ETF** (`TQQQ`, `SOXL` 등): `config/instrument_registry.json` + `allow_leveraged_etfs` (기본 `false`). 유효 노출 = `Σ(market_value × |multiple|)` ≤ `max_effective_leverage_exposure_pct × portfolio`. 고 VIX 시 차단: `block_leveraged_etfs_vix_above` (기본 28).
- **마진 `leverage_factor`**: 계좌 배수 — ETF 메타와 별도.
  ```bash
  bash scripts/run_leverage_stress_report.sh --leverage 2.0
  bash scripts/run_margin_leverage_paper_gate.sh --leverage-factor 1.25 --refresh-stress
  # GO → config/margin_leverage_paper_proposal.json 값으로 paper 소액 실험
  # strategy_config: margin_leverage_paper_enabled=true (기본 stress gate 필수)
  ```
  산출물: `logs/margin_leverage_paper/go_no_go_checklist.json`

### 2.5 데이터 최신성(Stale Data) 오류
- **현상**: `SKIP_BUY - stale price data` 로그 발생.
- **대응**:
    1. 특정 종목의 거래 정지 여부 확인.
    2. 전체 종목이 스킵된다면 yfinance API 지연 문제임. 30분~1시간 후 재실행.

---

## 📈 3. 주기적 점검 사항 (Maintenance)

- **증거 루프 (2026-07 신설)** — 9월 판단(슬리브 배분·예산 완화)과 라이브 전환의 근거 데이터:
  ```bash
  # ① 슬리브 성과 (데일리 — bootstrap 8c 단계 자동, 수동은 아래)
  bash scripts/run_sleeve_performance_report.sh      # → logs/sleeves/ (07-06 이전 기록은 0-버그, portfolio_value>0 필터)
  # ② 마켓 레짐 스냅샷 (데일리 — bootstrap 8c2 단계 자동, 레짐 전환 시 Telegram 알림)
  PYTHONPATH=. .venv/bin/python -m src.market_regime_snapshot   # → logs/market_regime/
  # ③ 시뮬-페이퍼 갭 어트리뷰션 (주간 — 일 18:00 ET 타이머)
  bash scripts/install_gap_attribution_timer.sh && systemctl --user enable --now trading-bot-gap-attribution.timer
  bash scripts/run_weekly_gap_attribution.sh         # → logs/sim_paper_gap/ (trend_summary.json에 8주 판정 규칙)
  ```
  ⚠️ 갭 어트리뷰션의 슬리브 예산 판정 규칙은 **사전 등록(2026-07-06 고정)** — 중간에 규칙을 수정하지 말 것. BULL 이탈 알림 = 노가드 tournament 슬리브 재평가 트리거.
- **슬리브 리밸런스 (수동 트리거)**:
  ```bash
  bash scripts/run_sleeve_rebalance_once.sh    # retag + drift trim 즉시 실행
  bash scripts/run_portfolio_pnl_report.sh     # paper P&L 스냅샷 → logs/portfolio_pnl/
  ```
- **일간·주간 ops 배치** (권장):
  ```bash
  bash scripts/run_ops_reports.sh              # audit + LLM cache
  bash scripts/run_ops_reports.sh --weekly     # + slippage
  bash scripts/run_ops_reports.sh --heavy      # + guard impact + leverage stress
  ```
  타이머 일괄 설치: `bash scripts/install_ops_report_timers.sh`  
  일일 paper (rank tracker): `bash scripts/install_paper_daily_timer.sh`  
  paper/backtest 진입 동등성: `bash scripts/install_daily_paper_backtest_parity_timer.sh`
  (슬리피지 주간 타이머는 별도: `bash scripts/install_slippage_report_timer.sh`)
- **일일 paper/backtest 동등성** (평일 23:30 ET, paper ops 완료 후):
  ```bash
  bash scripts/run_daily_paper_backtest_parity.sh
  bash scripts/install_daily_paper_backtest_parity_timer.sh
  systemctl --user enable --now trading-bot-paper-backtest-parity.timer
  ```
  `BUY_PLAN`의 Rank 점수·원종목/주문종목·품질 배율·레버리지 허용·주문 비중을 `portfolio_entries.csv`와 비교한다. 체결률과 기준가 대비 매수 슬리피지, 최근 주문 오류도 함께 집계하며 이상이 있을 때만 Telegram 오류 알림을 보낸다. 최신 캐시가 부분 갱신 중이면 기본 유니버스 80% 이상이 완성된 마지막 시장일까지 자동으로 잘라 비교한다. 산출물: `logs/paper_backtest_parity/latest_summary.json`, `latest_comparison.csv`.
- **일간**: Telegram 요약 + audit JSON
  ```bash
  bash scripts/run_daily_audit_summary.sh
  ```
  산출물: `logs/audit_daily/latest_summary.json` (`logs/execution_audit.csv` 기준)  
  CI smoke: `PYTHONPATH=. .venv/bin/python scripts/check_audit_daily_summary.py`  
  GitHub Actions: push/PR to `main` → `.github/workflows/ci.yml` (pytest 248+, cms-import, deploy-gate).
- **Extended-hours limit 체결률** (paper):
  ```bash
  PYTHONPATH=. .venv/bin/python -m src.extended_hours_fill_report
  ```
  산출물: `logs/paper_ops/extended_hours_fill_report.json` (bootstrap 6/7단계에 포함).
- **Run frequency 비교** (캐시 주기 what-if):
  ```bash
  bash scripts/compare_run_frequency.sh
  ```
  산출물: `logs/run_frequency/run_frequency_comparison.json` — 일 1회 vs 10분 캐시 시뮬레이션 요약.
- **주간**: paper 체결 vs 시그널 슬리피지 자동 리포트
  ```bash
  bash scripts/run_weekly_slippage_report.sh
  # 또는: PYTHONPATH=. .venv/bin/python -m src.report_performance --weekly
  ```
  산출물: `logs/slippage_reports/latest_summary.json` (타이머 설치: `bash scripts/install_slippage_report_timer.sh`)
- **월간**: `data/llm_cache.json` 및 오래된 로그 파일 정리 (용량 관리).
- **모델·알파 품질 (수동)**:
  ```bash
  bash scripts/run_fold_variance_report.sh    # logs/ml/fold_variance_report.json
  bash scripts/run_promotion_summary.sh       # logs/ml/model_promotion_report.json
  bash scripts/run_benchmark_gap_report.sh    # logs/benchmark_gap/latest_summary.json
  ```
  승격 게이트 문서: [`docs/promotion_gates.md`](promotion_gates.md)
- **Paper crowding guard (수동)**:
  ```bash
  bash scripts/run_guard_impact_report.sh
  bash scripts/run_crowding_live_impact_report.sh   # logs/crowding_live/latest_summary.json
  bash scripts/run_crowding_paper_gate.sh   # logs/crowding_paper/go_no_go_checklist.json
  ```
  GO 시 설정안: `config/crowding_paper_proposal.json` (paper only)
- **실행 정합 (주간)**:
  ```bash
  bash scripts/run_execution_alignment_report.sh   # audit vs slippage diff
  ```
- **레버리지 stress 알림**: `config/leverage_stress_config.json` — `run_leverage_stress_report.sh --leverage 2.0`
- **LLM cache 알림**: `config/llm_monitoring_config.json` — `run_llm_cache_report.sh`
- **리스크 리포트 (수동/주간)**:
  ```bash
  bash scripts/run_guard_impact_report.sh      # logs/guard_impact/latest_summary.json
  bash scripts/run_leverage_stress_report.sh   # logs/leverage_stress/latest_summary.json
  bash scripts/run_llm_cache_report.sh         # logs/llm_monitoring/latest_summary.json
  ```

---

## 📞 4. 연락처 및 알림 설정
- 모든 치명적 에러는 **Telegram**으로 즉시 전송됩니다.
- 알림 설정 변경: `config/notification_config.json` 수정 후 봇 재실행.
