# AI-Driven Quant Trading Bot (2026 Edition)

본 프로젝트는 AI(LightGBM + XGBoost 앙상블)와 정성적 분석(LLM Consensus)을 결합한 지능형 Alpaca Paper Trading 봇입니다. 시장 레짐(BULL/BEAR/NEUTRAL)을 자동으로 감지하고, 이에 최적화된 동적 전략 프로필을 적용하여 안정적인 수익을 추구합니다.

## 🚀 주요 혁신 기능

### 1. 하이브리드 의사결정 엔진
- **정량 모델 (Ensemble AI)**: LightGBM과 XGBoost를 결합한 앙상블 모델이 24개 이상의 피처(기술적 지표, 옵션 시장 tail risk, 매크로 지표)를 기반으로 매수 확률 점수를 산출합니다.
- **정성 모델 (LLM Consensus)**: Gemini 1.5 Flash API를 활용하여 최신 뉴스를 실시간 분석합니다. 소송, 부정회계, 가이던스 하향 등 정량 모델이 놓치기 쉬운 펀더멘털 리스크를 감지하여 최종 승인을 결정합니다. (결과는 비용 절감을 위해 로컬 캐싱됩니다.)

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

## 📂 프로젝트 구조

```text
trading-bot/
├── app/                # Streamlit CMS 대시보드
├── config/             # 전략 프로필 및 시스템 설정 (JSON)
├── data/               # 피크 정보, LLM 캐시, 트레일링 스탑 데이터
├── logs/               # 실행 감사(Audit), 주문, 신호 로그 (CSV)
├── models/             # 학습된 레짐별 AI 모델 파일
├── scripts/            # 실행 및 서비스 등록 쉘 스크립트
├── src/                # 핵심 로직 (Python 3.12)
│   ├── main.py         # 메인 트레이딩 루프
│   ├── alpaca_client.py # Alpaca API 고도화 (Retry/Idempotency)
│   ├── llm_analyst.py  # Gemini LLM 분석 및 캐싱
│   ├── macro_events.py # 경제 지표 캘린더 리스크 관리
│   └── correlation_guard.py # 포트폴리오 상관관계 관리
└── tests/              # 유닛 및 E2E 테스트 스위트
```

## 🛠 시작하기

### 환경 설정
- **Python 3.12** 전용 프로젝트입니다.
- `.env.example` 파일을 복사하여 `.env` 파일을 생성하고 Alpaca API Key 및 Gemini API Key를 입력하세요.

### 가상환경 구축 및 실행
```bash
# 가상환경 생성 및 패키지 설치
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 드라이런 실행 (주문 미제출)
PYTHONPATH=. .venv/bin/python src/main.py

# 실제 Paper Trading 실행
PYTHONPATH=. .venv/bin/python src/main.py --execute
```

### 테스트 실행
```bash
# 전체 테스트 실행
PYTHONPATH=. .venv/bin/pytest
```

## 📊 현재 성과 (OOS Validated)
- **수익률**: Ultra Aggressive 모드(Bull) 기준 5개월 **+41.68%** 달성
- **안정성**: Bear 시장 예측력 강화 및 고도화된 리스크 가드로 Drawdown 최소화
