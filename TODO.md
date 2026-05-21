# TODO

## Current Status
- Keep the existing baseline strategy as the default execution path.
- Treat the `qlib` integration as research-only for now.
- `SPY` 50/200 market regime filtering is implemented but should remain disabled by default because it reduced return materially in backtests.

## Next Priorities
1. Add stock-relative-strength features.
   Compare each ticker's recent return against the benchmark return and test whether it improves entry quality.
2. Add volume and volatility filters.
   Focus on simple, explainable filters before introducing higher-noise data sources.
3. Re-test the current strategy with one new variable at a time.
   Keep the existing baseline snapshot as the control and reject changes that do not improve return/risk together.

## Qlib Follow-up
1. Keep `qlib` scripts and snapshots for offline experimentation only.
2. Prefer the custom execution engine over `TopkDropoutStrategy` if `qlib` research continues.
3. Do not connect `qlib` results to the live trading path unless they beat the current baseline on return, drawdown, and trade efficiency.
