The patch adds useful rank-gate reporting, but it has a few compatibility and robustness regressions: the new report can crash on older candidate-cache files, it can misreport gate enablement from CSV strings, and audit logging now fails if the log file exists but is empty.

Full review comments:

- [P2] Handle candidate caches that predate the `risk_allowed` column — /home/kimyo/trading-bot/src/rank_ai_gate_impact_report.py:87-89
  `_candidate_cache_stats` assumes `df.get("risk_allowed", False)` returns a Series, but on older `latest_buy.csv` files it returns the scalar `False`, so the next line raises on `risk_allowed.dtype`. In the common compatibility scenario where someone runs this report against a cache produced before the new column existed, the entire rank-gate report crashes instead of returning zeros.

- [P2] Parse `rank_ai_gate_enabled` values instead of truthifying strings — /home/kimyo/trading-bot/src/rank_ai_gate_impact_report.py:91-91
  `bool(df.get("rank_ai_gate_enabled", ...).iloc[0])` treats any non-empty string as `True`, so a CSV row containing the text `False` or `false` is reported as gate-enabled. This makes the paper-ops/rank-gate summaries inaccurate for caches read back from CSV when pandas does not infer a boolean dtype for that column.

- [P2] Avoid indexing the first line of an empty audit file — /home/kimyo/trading-bot/src/logger.py:160-161
  The new schema-normalization path unconditionally reads `splitlines()[0]` whenever `execution_audit.csv` exists. If the file has been created but is still empty (for example after truncation/rotation or a pre-created artifact in CI), the first audit append now fails with `IndexError` before any row is written.
