# TODO

## Current Status
- Keep the existing baseline strategy as the default execution path.
- Treat the `qlib` integration as research-only for now.
- `SPY` 50/200 market regime filtering is implemented but should remain disabled by default because it reduced return materially in backtests.
- Stock-relative-strength filtering is implemented but disabled by default until it beats the current baseline.
- Stock-relative-strength no-AI and AI-enabled grid searches did not beat baseline return/risk.
- Stop-loss, take-profit, and trailing-stop exits are implemented in backtests but disabled by default; grid search reduced drawdown but did not beat baseline return/risk.
- Entry ranking grid search found return/risk improvements using momentum and volatility-aware ranking.
- Best entry-ranking profile is wired into the active config: trend=1.0, ai=0.0, momentum=0.5, volatility=1.0.
- Volume and volatility filters are implemented for live signals and portfolio backtests.
- Single-variable retest found the volume filter improved return and drawdown; active config now enables volume lookback=20, min ratio=1.0.
- Volatility-only grid search did not beat the current baseline on return and risk together, so it remains disabled.
- AI threshold retest did not find a better setting than the current 0.45 under the active volume/ranking config; 0.40 matched it, 0.50 reduced return while improving drawdown.
- Exit rule retest against the updated active config did not beat baseline on return and risk together, so stop-loss/take-profit/trailing-stop remain disabled in backtests.
- Relative strength retest against the updated active config did not beat baseline on return and risk together, so it remains disabled.
- Market regime retest against the updated active config did not beat baseline on return and risk together, so it remains disabled.
- Baseline snapshot was regenerated for the updated active config.
- The updated active config is the current baseline.

## Next Priorities
1. Only evaluate future candidates one variable at a time against the current baseline.
2. Do not combine new filters unless each candidate first beats the updated baseline on return and risk.

## Portfolio Management System (PMS) Implementation
- [x] Redesign Configuration structure (Strategy Profiles & Asset Allocation)
- [x] Implement Multi-Strategy Backtester (Portfolio-level simulation)
- [x] Develop Portfolio Rebalancing & Risk Management engine
- [x] Implement Asset Allocation logic (e.g., Risk-parity, Fixed-weight)

## Qlib Follow-up
1. Keep `qlib` scripts and snapshots for offline experimentation only.
2. Prefer the custom execution engine over `TopkDropoutStrategy` if `qlib` research continues.
3. Do not connect `qlib` results to the live trading path unless they beat the current baseline on return, drawdown, and trade efficiency.

## Advanced PMS Development (Future Roadmap)
- [ ] **Execution Layer**: Implement real-time order management (Alpaca/Binance API integration)
- [ ] **Advanced Optimization**: Implement Mean-Variance Optimization (MVO) and Black-Litterman models
- [ ] **Real-time Monitoring**: Develop live dashboard (Streamlit) and notification system (Telegram/Slack)
- [ ] **Data Pipeline**: Build real-time data ingestion and feature engineering pipeline
