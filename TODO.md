# TODO

## Current Status (2026-05-26)

### Active Config
- Tickers: 110개 (`config/strategy_config.json`)
- AI model: LightGBM, 21 features, **prediction_horizon=20일**
- AI buy threshold: **0.50** (20일 모델 기준 최적)
- AI exit: **MA primary / VIX>30 공황 시에만 AI score<0.45 청산**
  - `ai_exit_dynamic_enabled=true`, `ai_exit_vix_high=30.0`, `ai_exit_threshold_bear=0.45`
- Entry-ranking: trend=1.0, ai=0.0, momentum=0.5, volatility=1.0
- Volume filter: lookback=20, min_ratio=1.0
- MA: fast=10, slow=50 / RSI buy limit=65 / max_position_pct=0.10 / max_total_positions=8
- Daily retraining: 매 평일 06:00 ET (systemd timer)
- News sentiment filter: enabled (compound < -0.30 → 매수 차단)

### OOS Validated Performance (test: 2024-05-26 ~ 2026-05-26)
- MA only:       return=83.96%, MDD=-25.28%, Sharpe=1.474
- **Current AI**: return=71.56%, MDD=-8.85%,  Sharpe=1.978
- AI 우위: Sharpe +0.5, MDD 3분의 1 / Raw return은 bull market에서 MA보다 낮음

### Disabled (실험 후 비채택)
- SPY 50/200 market regime filtering (수익 감소)
- Relative strength filtering (baseline 미달)
- Stop-loss / take-profit / trailing-stop (baseline 미달)
- Volatility filter (baseline 미달)
- VIX-dynamic exit (고정 0.25 대비 5일 모델에서 열위, 20일 모델에서만 유효)
- qlib integration (research-only, live trading 미연결)
- PMS / PortfolioConfig (미연결)

## Evaluation Rules
1. Only evaluate future candidates one variable at a time against the current baseline.
2. Do not combine new filters unless each candidate first beats the updated baseline on return and risk.
3. A candidate should not replace the baseline unless it improves return/risk and does not materially harm trade efficiency.

---

## Phase 0 — Prerequisite ✅ Complete

- [x] Regenerate baseline snapshot from current config (110 tickers)
- [x] Verify outputs with report
- [x] Baseline metrics confirmed:
  - total_return=67.76%, max_drawdown=-12.21%, trades=51, win_rate=45.10%, final_equity=$16,776.36
- [ ] Commit verified baseline artifacts

---

## Phase 1 — AI Model Enhancement ✅ Complete

- [x] Add new features to `src/features.py` (13 → 17 features):
  - `high_52w_ratio`: 52주 고점 대비 현재 위치
  - `low_52w_ratio`: 52주 저점 대비 현재 위치
  - `vix_level`: VIX 공포지수 (vix_df 제공 시 사용, 미제공 시 0)
  - `spy_rel_return_20d`: SPY 대비 상대 수익률 20일 (spy_df 제공 시 사용)
- [x] Replace RandomForest → LightGBM (n_estimators=500, max_depth=6, subsample=0.8)
- [x] Fix NaN handling for newly-listed tickers (ARM 등) in `build_features`
- [x] Retrain model: 110 tickers × 5y data, VIX + SPY context data
- [x] Backtest result confirmed improvement:
  - No AI: return=40.26%, MDD=-24.71%, trades=89, win_rate=41.57%
  - LightGBM AI (threshold=0.45): return=68.63%, MDD=-10.50%, trades=40, win_rate=57.50%
- [x] Build automated daily retraining pipeline (daily, not weekly — geopolitical volatility)
  - 06:00 ET (장 시작 3.5시간 전) 매 평일 자동 재학습
  - systemd user timer: `trading-bot-retrain.timer` 활성화 완료
  - 재학습 로그: `logs/retrain_history.csv` (timestamp, roc_auc, precision, elapsed)
  - 실행 로그: `logs/retrain_runs/retrain_YYYYMMDD_HHMMSS.log`

---

## Phase 2 — Real-time Monitoring Dashboard ✅ Complete

- [x] Built Streamlit dashboard (`src/dashboard.py`):
  - 계좌 현황: portfolio value, cash, buying power, positions (Alpaca)
  - 백테스트 성과: equity curve chart, trades table, summary metrics
  - AI 모델 성능: cross-validation fold별 ROC-AUC / precision / recall
  - 최근 시그널: BUY/SELL/HOLD 분류, 종목별 시그널
  - 최근 주문 내역: order log 테이블
  - 전략 설정 요약: expander로 상세 파라미터 표시
- [x] Reads from existing logs/CSV — no changes to `main.py`
- [x] Running at http://localhost:8501 (`streamlit run src/dashboard.py`)

---

## Phase 3 — Execution Layer Hardening ✅ Complete

- [x] Add limit order support: `submit_limit_buy_notional_order()` in `src/alpaca_client.py`
  - limit_price × (1 + slippage_pct=0.005) 로 수량 계산 후 지정가 주문
  - 시장가 대비 슬리피지 감소, 즉시 체결 가능성 유지
- [x] Sector concentration check: `src/sector.py`
  - 110개 티커 → 15개 섹터 매핑 (tech/semis/software/financials/healthcare 등)
  - `max_sector_positions=2` (settings로 조정 가능): 같은 섹터 최대 2개 보유
  - ETF/unknown 섹터는 제한 없음
  - `main.py` 매수 로직에 연동
- [x] Automated scheduler: systemd user timer (기존 인프라 활용)
  - 09:35 ET (장 오픈 5분 후) / 15:45 ET (장 마감 15분 전) 자동 실행
  - `systemctl --user enable --now trading-bot.timer` 로 활성화 완료
  - `config/scheduler_config.json` 으로 일정 조정 가능
- [ ] Wire `PortfolioConfig` into `main.py` — defer to Phase 4 (아키텍처 변경 필요)

---

## Phase 4 — Advanced Portfolio Optimization ✅ Complete

Goal: replace fixed-weight position sizing with model-driven allocation.

- [x] Implement Mean-Variance Optimization (MVO) for position sizing (`src/portfolio_optimizer.py`)
- [x] Implement Black-Letterman model (market equilibrium + AI-score views)
- [x] Backtest MVO/BL vs equal-weight baseline (`src/compare_allocation.py`)
- [x] Backtest result (2y, same signal conditions):
  - equal_weight: return=30.41%, MDD=-9.29%, Sharpe=1.092
  - **MVO**: return=31.33%, MDD=-8.30%, Sharpe=1.132 ✅ beats baseline on all metrics
  - BL+MVO: return=30.32%, MDD=-9.29%, Sharpe=1.091 (no improvement — AI pre-filtering reduces BL view value)
- [x] Wire MVO into `main.py` live trading (two-pass buy loop: collect → MVO weight → submit)
  - `allocation_method: str = "equal_weight"` added to StrategySettings (default: equal_weight for safety)
  - Set `"allocation_method": "mvo"` in config/strategy_config.json to activate

---

## Phase 5 — AI Exit + News/Event Features ✅ Complete

### 5-A: AI-based Exit Signal ✅ Complete
- [x] Add `ai_exit_enabled` / `ai_exit_threshold` to StrategySettings
- [x] Wire AI exit into portfolio_backtester.py (AI_EXIT reason)
- [x] Optimize threshold via `src/optimize_ai_exit.py` (2y backtest)
- [x] Wire into `main.py` live exit logic

### 5-B: News/Event Features ✅ Complete
- [x] Macro features 추가 (17 → 21 features): `src/macro_loader.py`
- [x] 뉴스 감성 분석 (라이브 전용): `src/news_sentiment.py`
- [x] `main.py` 연동

---

## Phase 6 — Model Architecture Overhaul ✅ Complete

### 6-A: Prediction Horizon 5일 → 20일
- [x] `src/train_ai_model.py`: prediction_horizon 5 → 20
- [x] `src/validate_model.py`: validation model도 20일로 통일
- [x] 재학습 완료 (2026-05-26): avg ROC-AUC ~0.513
- [x] 근거: 5일 예측은 실제 보유기간(수주~수개월)과 불일치 → 20일이 실제 트레이드 horizon에 부합

### 6-B: AI Exit 구조 재설계 — MA primary + VIX panic exit
- [x] 문제 진단: AI exit이 강세장에서 winner 조기 청산 (OOS: AI 21% vs MA 83%)
- [x] 해결 구조: 평소 MA exit, VIX>30 공황 시에만 AI score<0.45로 청산
  - `ai_exit_threshold=0.0` (중립: 사실상 비활성)
  - `ai_exit_vix_high=30.0` / `ai_exit_threshold_bear=0.45`
- [x] AI buy threshold 0.45 → 0.50 (20일 모델 기준 최적, Sharpe 기준)
- [x] OOS 검증 (2024-05-26 ~ 2026-05-26):
  - MA only: return=83.96%, MDD=-25.28%, Sharpe=1.474
  - **현재 AI**: return=71.56%, MDD=-8.85%, Sharpe=1.978 ✅ Sharpe 우위, MDD 3분의 1
  - 과적합 갭 42%p — daily 재학습으로 완화 (B=71.56%, A=29.33% 사이 수렴)

---

## Phase 7 — Live Performance & Risk Monitoring (Next)

### 7-A: Paper Trading 실적 분석
- [ ] Alpaca paper account 실제 거래 내역 vs 백테스트 비교 (`src/alpaca_client.py` 활용)
  - 슬리피지: 예상 가격 vs 실제 체결가 차이
  - 시그널 → 주문 → 체결 지연 시간 측정
  - 백테스트 대비 실제 win_rate / return 괴리 정량화
- [ ] 일별 P&L 리포트 자동화 (로그 → 요약 이메일 or 대시보드 추가)

### 7-B: 포트폴리오 리스크 한도
- [ ] 상관관계 기반 포지션 제한: 동일 팩터 노출 종목 동시 보유 제한
  - 예: NVDA + AMD + AVGO 상관계수 >0.85 → 1개만 보유
  - `src/correlation_guard.py` 구현, `main.py` 매수 루프에 연결
- [ ] Drawdown circuit breaker: 포트폴리오 -15% 이하 시 신규 매수 중단
  - Alpaca 잔고 기준 실시간 체크
  - `config/strategy_config.json`에 `max_portfolio_drawdown_pct` 추가

### 7-C: 알림 시스템
- [ ] VIX > 30 돌파 시 panic mode 진입 알림
- [ ] 모델 성능 저하 감지: retrain 후 ROC-AUC < 0.51 이면 경고
  - `logs/retrain_history.csv` 모니터링
- [ ] 알림 채널: 이메일 or Slack webhook (설정 가능하게)

---

## Phase 8 — Regime-Aware Modeling (중기)

### 8-A: 시장 레짐 분리 모델
- [ ] 레짐 분류: VIX + SPY 추세 기반으로 bull / neutral / bear 구분
- [ ] 레짐별 별도 모델 학습 및 저장
  - bull 모델: 모멘텀 강조
  - bear 모델: 방어적 피처 강조 (금, VIX percentile, yield spread)
- [ ] 현재 레짐에 맞는 모델 선택해서 inference
- [ ] OOS 갭 개선 목표: 현재 42%p → 20%p 이하

### 8-B: Walk-Forward 검증 자동화
- [ ] 월별 rolling OOS 검증 스크립트
  - 매월 train window 1개월씩 슬라이딩
  - 연속 OOS 수익률 곡선으로 모델 안정성 확인
- [ ] `src/walk_forward_validation.py` 구현

---

## Phase 9 — Signal Quality 개선 (장기)

### 9-A: 앙상블 모델
- [ ] LightGBM + XGBoost 앙상블 (soft voting)
- [ ] 백테스트로 단일 모델 대비 개선 확인 후 적용

### 9-B: 어닝 캘린더 필터
- [ ] 실적 발표 3일 전 ~ 1일 후 신규 매수 차단
  - `yfinance` calendar API 활용
  - 기존 보유 포지션은 유지 (exit 강제 없음)
- [ ] 백테스트 효과 검증 후 활성화

### 9-C: 옵션 시장 신호 (연구)
- [ ] Put/Call ratio, IV skew → AI 모델 피처 추가 후보
- [ ] 데이터 소스 확인 필요 (yfinance 또는 별도 API)

---

## Qlib Follow-up
1. Keep qlib scripts and snapshots for offline experimentation only.
2. Prefer the custom execution engine over TopkDropoutStrategy if qlib research continues.
3. Do not connect qlib results to the live trading path unless they beat the current baseline on return, drawdown, and trade efficiency.
