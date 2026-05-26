# TODO

## Current Status
- Keep the existing baseline strategy as the default execution path.
- Treat the `qlib` integration as research-only for now.
- Active baseline config is restored in `config/strategy_config.json` and mirrored in `examples/strategy_config.example.json`.
- Active tickers are `NVDA`, `MSFT`, `GOOGL`, `AMZN`, and `AMD`.
- Active entry-ranking profile is wired into config: trend=1.0, ai=0.0, momentum=0.5, volatility=1.0.
- Volume and volatility filters are implemented for live signals and portfolio backtests.
- Active config enables the volume filter with lookback=20 and min ratio=1.0.
- `SPY` 50/200 market regime filtering is implemented but should remain disabled by default because it reduced return materially in backtests.
- Stock-relative-strength filtering is implemented but disabled by default until it beats the current baseline.
- Stock-relative-strength no-AI and AI-enabled grid searches did not beat baseline return/risk.
- Stop-loss, take-profit, and trailing-stop exits are implemented in backtests but disabled by default; grid search reduced drawdown but did not beat baseline return/risk.
- Volatility-only grid search did not beat the current baseline on return and risk together, so it remains disabled.
- AI threshold retest did not find a better setting than the current 0.45 under the active volume/ranking config; 0.40 matched it, 0.50 reduced return while improving drawdown.
- Exit rule retest against the updated active config did not beat baseline on return and risk together, so stop-loss/take-profit/trailing-stop remain disabled in backtests.
- Relative strength retest against the updated active config did not beat baseline on return and risk together, so it remains disabled.
- Market regime retest against the updated active config did not beat baseline on return and risk together, so it remains disabled.
- `settings.py` compatibility was restored for legacy single-strategy scripts via `StrategySettings`, `load_settings`, and `save_settings`.
- `strategy.add_indicators` compatibility was restored for both profile-based and `ma_fast`/`ma_slow` based callers.
- `qlib_backtest_runner.py` main-flow corruption was repaired, but qlib remains research-only.

## Immediate Next Steps
1. Regenerate the active baseline snapshot from the restored config:
   ```bash
   python -m src.generate_baseline_snapshot
   ```
2. Review the regenerated outputs:
   ```bash
   python -m src.report
   ```
3. Confirm these files are updated and internally consistent:
   - `logs/baselines/current_strategy/baseline_snapshot.json`
   - `logs/baselines/current_strategy/portfolio_summary.csv`
   - `logs/baselines/current_strategy/portfolio_equity.csv`
   - `logs/baselines/current_strategy/portfolio_trades.csv`
4. Commit regenerated baseline artifacts only after verifying return, max drawdown, trade count, and win rate match expectations.

## Evaluation Rules
1. Only evaluate future candidates one variable at a time against the current baseline.
2. Do not combine new filters unless each candidate first beats the updated baseline on return and risk.
3. A candidate should not replace the baseline unless it improves return/risk and does not materially harm trade efficiency.

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
