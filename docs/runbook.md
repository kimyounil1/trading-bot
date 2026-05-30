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

### 2.4 데이터 최신성(Stale Data) 오류
- **현상**: `SKIP_BUY - stale price data` 로그 발생.
- **대응**:
    1. 특정 종목의 거래 정지 여부 확인.
    2. 전체 종목이 스킵된다면 yfinance API 지연 문제임. 30분~1시간 후 재실행.

---

## 📈 3. 주기적 점검 사항 (Maintenance)

- **일간·주간 ops 배치** (권장):
  ```bash
  bash scripts/run_ops_reports.sh              # audit + LLM cache
  bash scripts/run_ops_reports.sh --weekly     # + slippage
  bash scripts/run_ops_reports.sh --heavy      # + guard impact + leverage stress
  ```
  타이머 일괄 설치: `bash scripts/install_ops_report_timers.sh`  
  (슬리피지 주간 타이머는 별도: `bash scripts/install_slippage_report_timer.sh`)
- **일간**: Telegram 요약 + audit JSON
  ```bash
  bash scripts/run_daily_audit_summary.sh
  ```
  산출물: `logs/audit_daily/latest_summary.json` (`logs/execution_audit.csv` 기준)  
  CI smoke: `PYTHONPATH=. .venv/bin/python scripts/check_audit_daily_summary.py`
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
