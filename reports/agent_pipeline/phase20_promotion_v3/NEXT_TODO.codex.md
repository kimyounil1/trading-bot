The patch does exclude the holdout from model fitting, but the promotion OOS backtest is run without required indicator warmup history, making the promotion gate unreliable in realistic configurations. It also persists misleading training-window metadata that includes the holdout.

Full review comments:

- [P1] Preserve pre-holdout history for OOS indicators — /home/kimyo/trading-bot/src/train_ai_model.py:676-683
  When the configured filters or indicators need lookback history (for example the default 200-day market-regime MA, 50-day slow MA, relative-strength/volume/volatility windows, or AI features), passing only `holdout_ticker_data` into `_run_retrain_oos_portfolio` makes the first part—or all—of the six-month holdout lack enough history. In common market-regime-enabled runs a six-month slice is shorter than the 200-day MA, so the OOS gate can produce no buy signals and reject/compare models on an artificially degraded backtest; use full price history with `evaluation_start/end` to restrict scoring while preserving warmup context.

- [P2] Build metadata from the actual fitting window — /home/kimyo/trading-bot/src/train_ai_model.py:659-666
  Although the model is now fit on `training_data_fit`, the bundle metadata is still built with full `training_data`, so promoted/challenger metadata reports a `training_window_end` that includes the holdout dates. For promotion governance this makes the saved model appear trained through the OOS holdout and can mask whether the holdout was actually excluded; pass `training_data_fit` here so persisted metadata matches the data used for fitting.
