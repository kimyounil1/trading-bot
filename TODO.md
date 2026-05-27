# TODO

## Current Status (2026-05-27)

### Active Config
- Tickers: 110개 (`config/strategy_config.json`)
- AI model: **LightGBM + XGBoost Ensemble**, 24 features
- Regime-Aware: **BULL / BEAR / NEUTRAL** 별 독립 모델 및 프로필 가동
- Dynamic Profile: **ULTRA_AGGRESSIVE** (BULL 시 33% 비중 집중 투자)
- AI exit: **MA primary / VIX>30 공황 시에만 AI score<0.45 청산**
- Risk Guards: Circuit Breaker (-15%), Correlation Guard (0.85), Earnings Filter (+3/-1d)
- Daily retraining: 매 평일 06:00 ET (systemd timer)

### OOS Validated Performance (test: 2024-05-27 ~ 2026-05-27)
- **Ultra Aggressive (Bull)**: 5개월 수익률 **+41.68%**, Sharpe 2.51
- **Regime-Aware Ensemble**: Bear 시장 예측력(ROC-AUC 0.64) 대폭 강화
- 슬리피지: 평균 0.36% (안정적)

---

## Phase 0-6 ✅ Complete
(이전 단계 완료)

---

## Phase 7 — Live Performance & Risk Monitoring ✅ Complete

- [x] Alpaca paper account 실제 거래 내역 vs 백테스트 비교 리포트 (`src/report_performance.py`)
- [x] `src/logger.py`: 주문 로그 컬럼 일관성 수정
- [x] 상관관계 기반 포지션 제한 (`src/correlation_guard.py`)
- [x] Drawdown circuit breaker (-15%) 구현
- [x] VIX panic 및 모델 성능 저하 알림 (Telegram)

---

## Phase 8 — Regime-Aware Modeling ✅ Complete

- [x] 시장 레짐 분류 로직 (`src/market_regime.py`): VIX + SPY 추세 기반
- [x] 레짐별 별도 모델 학습 및 실시간 전환 로직 (`src/ml_model.py`)
- [x] Walk-Forward 검증 자동화 (`src/walk_forward_validation.py`)

---

## Phase 9 — Signal Quality 개선 ✅ Complete

- [x] LightGBM + XGBoost 앙상블 모델 (Soft Voting) 도입
- [x] 어닝 캘린더 필터 (`src/earnings.py`): 실적 발표 전후 매수 차단
- [x] 옵션 시장 신호 (`^SKEW`, `^VVIX`) 피처 추가 및 재학습

---

## Phase 10 — Dynamic Strategy Profiles ✅ Complete

- [x] 시장 레짐별 다이내믹 프로필 시스템 구축 (`config/strategy_profiles.json`)
- [x] **ULTRA_AGGRESSIVE** 모드 최적화: 강세장 수익률 극대화 (33% 집중 투자)
- [x] 수동 오버라이드 및 자동 전환 로직 검증 완료

---

## Phase 11 — 실행 고도화 및 지능화 ✅ Complete

- [x] **분할 매도 로직 (Partial Profit-Taking)**: 수익률 +15% 도달 시 비중의 50%를 선제적으로 익절하여 수익 보존 (`src/main.py`)
- [x] **LLM Consensus (Gemini)**: 매수 전 최신 뉴스를 LLM(Gemini)이 분석하여 정성적 리스크(부정적 공시, 소송 등) 감지 시 매수 차단 (`src/llm_analyst.py`)
- [x] **Consensus 로직**: 정량 모델(앙상블) + 정성 모델(LLM) 합의 시에만 최종 매수 결정하도록 통합 완료

---

## Phase 12 — 딥러닝 및 강화학습 ✅ Complete

- [x] **시계열 Transformer 인프라**: PyTorch 기반의 `SimpleTimeSeriesTransformer` 아키텍처 설계 및 구현 (`src/deep_model.py`)
- [x] **강화학습(RL) 포트폴리오 엔진**: Stable-Baselines3(PPO)를 활용한 동적 비중 조절 환경 및 에이전트 구축 (`src/rl_portfolio.py`)
- [x] **라이브러리 환경 구축**: `torch`, `stable-baselines3`, `gymnasium` 설치 및 연동 확인 완료

---

## Project Roadmap Finalized (2026-05-27)
- [x] Phase 0-12 전 과정 고도화 및 검증 완료
- [x] AI 기반 지능형 퀀트 시스템 구축 (Quantitative + Qualitative Hybrid)
- [x] 강세장 ULTRA_AGGRESSIVE 모드로 최고 수익률 세팅 탑재 완료

---

## Phase 13 — 다이내믹 유니버스 & 레버리지 ✅ Complete

- [x] **다이내믹 유니버스 (Dynamic Universe)**: 매일 실시간 인기 종목(Most Active) 50개를 자동 수집하여 분석 대상 확대 (총 160+ 종목)
- [x] **레버리지 가동**: 구매력(Buying Power) 증폭 로직 구현 완료
- [x] **추가 매수(Pyramiding) 허용**: 보유 종목이라도 비중이 낮으면 목표치까지 추가 매수하도록 개선

---

## Phase 14 — 수익 보존 및 정밀 엑싯 ✅ Complete

### 14-A: 지능형 트레일링 스탑 (Trailing Stop)
- [x] 주가 상승에 따라 손절 라인을 자동으로 올리는 로직 구현 (`src/main.py`, `src/backtester.py`)
- [x] 최고점 대비 X% 하락 시 익절하여 '줬다 뺏기는' 상황 방지

### 14-B: 다이내믹 포지션 리밸런싱
- [x] 목표 비중 대비 과대 보유 포지션 자동 Trim 로직 구현 (`src/main.py`)
- [x] 추가 매수 허용 로직과 연계한 목표 비중 복원 기반 리밸런싱 1차 적용 (`src/risk_manager.py`)

---

## Phase 15 — 시장 섹터 및 테마 분석 ✅ Complete

### 15-A: 섹터 순환매 (Sector Rotation) 감지
- [x] 11개 주요 ETF(XLK, XLF 등)의 모멘텀을 비교하여 주도 섹터 파악 (`src/sector_rotation.py`)
- [x] 주도 섹터 종목에 AI 점수 가산점 부여 (`src/main.py`, `src/sector_rotation.py`)

---

## Phase 16 — Execution Resilience & 운영 안정성 (Next)

### 16-A: 주문 실행 복원력
- [ ] 재시도/타임아웃 상황에서 중복 주문을 막는 idempotency key 또는 run-level dedupe 도입
- [ ] Alpaca 주문 제출, 체결 조회, 부분청산, trim 매도 경로별 공통 예외 처리/재시도 정책 정리
- [ ] 장중 네트워크 오류 시 `dry-run` 전환이 아니라 "실행 중단 + 경고"로 fail-safe 동작 통일

### 16-B: 상태 파일 및 데이터 무결성
- [x] `data/trailing_peaks.json` 읽기/쓰기 atomic 처리 및 손상 파일 복구 로직 추가
- [x] 매매 전 가격 데이터 최신 시각 검증 추가: stale/incomplete bar 감지 시 해당 티커 스킵
- [x] Dynamic Universe / candidate cache 산출물에 대해 "생성 시각, 소스, 누락 티커 수" 메타데이터 강제 기록

### 16-C: 실거래 감사 추적성
- [x] 주문 사유(reason), 적용 프로필, 레짐, AI score, LLM verdict를 한 row에서 추적 가능한 실행 audit 로그 정규화
- [x] partial exit / rebalance trim / full exit 를 동일한 이벤트 스키마로 로깅
- [x] 일별 실행 요약에 "실주문 수, 스킵 사유 집계, 데이터 오류 수, API 오류 수" 추가

---

## Phase 17 — Model Governance & 신호 품질 관리 (중기)

### 17-A: 모델 승격/강등 체계
- [x] 레짐별 모델 파일에 학습 기간, 피처 셋 버전, OOS 성능, 승격 시각 메타데이터 저장
- [x] 신규 모델 학습 후 자동 교체 대신 "챌린저 vs 챔피언" 비교 리포트 기반 승격 절차 추가
- [x] 최근 실거래/paper 성과가 기준 이하일 때 이전 안정 모델로 롤백하는 안전장치 도입

### 17-B: 드리프트 및 보정
- [x] 피처 분포 드리프트 감지(예: volatility, volume, macro feature) 및 알림
- [x] AI score calibration 점검: 확률 예측의 calibration curve / Brier score 리포트 자동화
- [x] 레짐별 buy/exit threshold를 고정값이 아니라 rolling OOS 기반으로 재튜닝하는 배치 추가

### 17-C: 정성 신호 통제
- [ ] LLM consensus 결과 캐시 및 재사용 정책 추가로 동일 티커 중복 호출 비용 절감
- [ ] 뉴스/LLM 실패 시 무조건 통과 또는 무조건 차단이 아니라 명시적 degraded mode 정책 정의
- [ ] 부정 이벤트 분류 사유를 구조화하여 "소송/실적경고/가이던스하향" 등 카테고리별 분석 가능하게 개선

---

## Phase 18 — Portfolio Risk Engine 고도화 (중기)

### 18-A: 포트폴리오 수준 익스포저 통제
- [x] leverage 사용 시 gross exposure, cash buffer, single-name max loss 기준을 함께 검증하는 포트폴리오 가드 추가
- [x] 섹터 한도 외에 factor/momentum crowding 기반 concentration guard 도입 검토
- [ ] 상관관계 가드를 단순 pairwise 기준에서 포트폴리오 전체 평균 상관/클러스터 기준으로 확장

### 18-B: 이벤트 리스크 캘린더
- [ ] Earnings 외에 FOMC, CPI, PPI, NFP 같은 매크로 이벤트 캘린더 반영
- [ ] 고변동 이벤트 전후 신규 진입 제한 또는 목표 비중 축소 규칙 추가
- [ ] 이벤트 결과 이후 regime/profile 재평가 배치를 별도 분리

### 18-C: Exit 정책 정밀화
- [x] trailing stop, AI exit, partial take-profit, rebalance trim 간 우선순위/충돌 규칙 명시화
- [ ] 종목별 ATR 또는 realized volatility 기반 adaptive trailing stop 검토
- [ ] 시간 기반 exit(보유 기간 초과, 신호 약화 지속) 규칙 추가 검토

---

## Phase 19 — 테스트/문서/설정 정합성 정리 (상시)

### 19-A: 테스트 보강
- [ ] `src/main.py` 실주문 흐름을 mock broker/mock LLM/mock news 기준으로 end-to-end 테스트 추가
- [ ] partial exit / trim / trailing stop / earnings filter 동시 발생 케이스 회귀 테스트 추가
- [ ] 장애 테스트 추가: 손상된 JSON 상태파일, 빈 데이터프레임, Alpaca timeout, LLM timeout

### 19-B: 설정 스키마 정리
- [x] `src/settings.py` 중복 필드(`trailing_stop_pct`) 및 레거시/신규 설정 혼재 정리
- [x] `strategy_config.json` / `strategy_profiles.json` 에 대한 schema validation 추가
- [ ] 미사용 설정값 및 문서와 어긋난 기본값 정리

### 19-C: 문서 최신화
- [ ] `README.md`를 현재 아키텍처 기준으로 업데이트: Regime-aware, ensemble, LLM consensus, dynamic universe 반영
- [ ] 운영 runbook 추가: retrain 실패, API 장애, drawdown breach, stale data 대응 절차
- [ ] `TODO.md` 완료 기준을 "코드 존재"가 아니라 "테스트/리포트/운영 검증 완료" 기준으로 재정의
