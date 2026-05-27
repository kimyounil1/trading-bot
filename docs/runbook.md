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

### 2.2 Retrain 실패 (Stale Model)
- **현상**: 매일 아침 06:00 ET에 실행되는 학습 타이머 실패 알림.
- **대응**:
    1. `logs/retrain_history.csv`에서 에러 로그 확인.
    2. 데이터 소스(yfinance) 차단 여부 확인.
    3. 모델 파일(`models/ai_score_model.joblib`)이 존재하면 봇은 기존 모델로 계속 동작함. 수동으로 `scripts/run_retrain.sh` 실행 시도.

### 2.3 Drawdown Circuit Breaker 발동
- **현상**: 포트폴리오 자산이 최고점 대비 15% 이상 하락하여 "New buys blocked" 알림 발생.
- **대응**:
    1. 현재 시장 레짐이 `BEAR`인지 확인.
    2. 포트폴리오 구성 종목의 개별 리스크(실적 악화 등) 재평가.
    3. 시장이 안정되었다고 판단되면 `config/strategy_config.json`의 `max_portfolio_drawdown_pct`를 일시적으로 상향 조정하여 가드 해제 가능.

### 2.4 데이터 최신성(Stale Data) 오류
- **현상**: `SKIP_BUY - stale price data` 로그 발생.
- **대응**:
    1. 특정 종목의 거래 정지 여부 확인.
    2. 전체 종목이 스킵된다면 yfinance API 지연 문제임. 30분~1시간 후 재실행.

---

## 📈 3. 주기적 점검 사항 (Maintenance)

- **일간**: Telegram 요약 리포트를 통해 실주문 수 및 스킵 사유 집계 확인.
- **주간**: `PYTHONPATH=. .venv/bin/python src/report_performance.py` 실행하여 실거래 vs 백테스트 괴리율(슬리피지) 점검.
- **월간**: `data/llm_cache.json` 및 오래된 로그 파일 정리 (용량 관리).

---

## 📞 4. 연락처 및 알림 설정
- 모든 치명적 에러는 **Telegram**으로 즉시 전송됩니다.
- 알림 설정 변경: `config/notification_config.json` 수정 후 봇 재실행.
