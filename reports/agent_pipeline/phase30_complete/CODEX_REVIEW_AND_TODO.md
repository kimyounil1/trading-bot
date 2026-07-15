The zero-trade preservation logic can now exit before recreating the full backtest artifact bundle, which breaks consumers that require all three CSVs. I did not find another blocking issue in the reviewed diff.

Review comment:

- [P2] Keep writing missing backtest artifacts on zero-trade runs — /home/kimyo/trading-bot/src/portfolio_backtester.py:757-763
  When `result.trades == 0` and an old summary with trades exists, this new early `return` skips writing `portfolio_equity.csv` and `portfolio_trades.csv` entirely. That leaves the output bundle incomplete whenever only `portfolio_summary.csv` survived from the baseline (or the other two files were cleaned), and downstream validation in `validate_portfolio_backtest_artifacts()` will now fail with `Missing portfolio backtest artifact`. Preserving the prior summary is fine, but the function still needs to ensure the other required CSVs exist.
