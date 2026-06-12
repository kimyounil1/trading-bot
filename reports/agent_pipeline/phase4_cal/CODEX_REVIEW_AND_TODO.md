The new optional feature-column support mishandles an explicit empty list, which can make experiment reports evaluate the wrong feature set. I could not run focused pytest locally because the read-only sandbox has no usable temporary directory.

Review comment:

- [P2] Preserve explicit empty feature lists — /home/kimyo/trading-bot/src/ml_model.py:491-491
  When a report-only experiment passes an explicit empty `feature_columns` list (for example, a bundle whose requested columns are absent), this falls back to the full `FEATURE_COLUMNS` set instead of returning no metrics. That makes `_evaluate_bundle` report a usable baseline-like result rather than the intended "no usable features" path, so sparse/custom datasets can produce misleading regime/fold experiment reports.
