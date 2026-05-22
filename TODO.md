# TODO

## Current Status
- Keep the existing baseline strategy as the default execution path.
- Treat the `qlib` integration as research-only for now.
- `SPY` 50/200 market regime filtering is implemented but should remain disabled by default because it reduced return materially in backtests.
- Stock-relative-strength filtering is implemented but disabled by default until it beats the current baseline.
- Stock-relative-strength no-AI and AI-enabled grid searches did not beat baseline return/risk.
- Stop-loss, take-profit, and trailing-stop exits are implemented in backtests but disabled by default; grid search reduced drawdown but did not beat baseline return/risk.
- Entry ranking grid search found return/risk improvements using momentum and volatility-aware ranking.

## Next Priorities
1. Validate the best entry-ranking profile before enabling it by default.
   Current best: trend=1.0, ai=0.0, momentum=0.5, volatility=1.0; it improved return and drawdown in the 2y cached backtest.
2. Add volume and volatility filters.
   Focus on simple, explainable filters before introducing higher-noise data sources.
3. Re-test the current strategy with one new variable at a time.
   Keep the existing baseline snapshot as the control and reject changes that do not improve return/risk together.

## Qlib Follow-up
1. Keep `qlib` scripts and snapshots for offline experimentation only.
2. Prefer the custom execution engine over `TopkDropoutStrategy` if `qlib` research continues.
3. Do not connect `qlib` results to the live trading path unless they beat the current baseline on return, drawdown, and trade efficiency.
