# Trading Bot

AI score + MA/RSI 기반 Alpaca paper trading bot.

현재 목표는 실거래가 아니라, paper trading 환경에서 자동매매 파이프라인을 안전하게 검증하는 것이다.

## 주요 기능

- yfinance 기반 가격 데이터 수집
- MA/RSI 전략 신호 생성
- scikit-learn 기반 AI score 필터
- Alpaca paper trading 연동
- dry-run 기본 실행
- 시장 시간 체크
- 손절/익절/전략 매도 조건 점검
- 포지션 중복 매수 차단
- 주문 금액/주문 수 제한
- Telegram 알림
- Streamlit CMS
- 포트폴리오 백테스트
- AI threshold 최적화
- 백테스트 이력 관리

## 프로젝트 구조

```text
trading-bot/
  app/
    streamlit_app.py

  config/
    strategy_config.json
    notification_config.json
    execution_lock.json
    scheduler_config.json

  logs/
    trades.csv
    orders.csv
    backtests/
    portfolio_backtest/
    selected_strategy/
    optimization/
    ai_backtest/
    ai_threshold/
    dry_runs/
    config_history/
    backtest_runs/
    execution_runs/
    bot_runs/

  models/
    ai_score_model.joblib

  scripts/
    run_bot_once.sh
    install_user_timer.sh

  src/
    alpaca_client.py
    backtester.py
    check_ai_score.py
    check_alpaca.py
    check_market.py
    config.py
    data_loader.py
    execution_lock.py
    features.py
    logger.py
    main.py
    market_clock.py
    ml_model.py
    notification_settings.py
    notifier.py
    optimize_ai_threshold.py
    optimize_strategy.py
    portfolio_backtester.py
    report.py
    risk_manager.py
    settings.py
    strategy.py
    train_ai_model.py
