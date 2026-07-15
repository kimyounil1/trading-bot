The patch introduces at least two behavior mismatches between the candidate cache and the live trading path, and the new rank-AI settings are only partially wired up. Those issues are likely to produce misleading candidate decisions or ineffective configuration changes.

Full review comments:

- [P2] Avoid applying the sector bonus twice in candidate cache — /home/kimyo/trading-bot/src/candidate_cache.py:510-510
  `ai_score` is already adjusted by `apply_sector_score_bonus` a few lines above, so calling the same helper again here double-counts the sector uplift in cache generation. When sector rotation is enabled, a ticker can appear to clear `ai_score_buy_threshold` in `latest_buy.csv` even though the live path only applies a single bonus, which makes the cache disagree with actual execution behavior.

- [P2] Treat dust positions consistently in candidate cache — /home/kimyo/trading-bot/src/candidate_cache.py:483-489
  This cache path still decides "held vs new" from the raw `positions_by_symbol` entry, but `main.py` now normalizes through `effective_position(..., min_usd=dust_position_min_usd)`. If a symbol is only a dust remainder, the cache will route it through the add-to-position branch, skip the new-position buy guards/LLM path, and emit a different recommendation from the real trading loop.

- [P2] Honor the configured top-bucket setting in rank AI gating — /home/kimyo/trading-bot/src/rank_ai_gate.py:147-149
  The new settings surface both `rank_ai_buy_gate_top_bucket_pct` and `rank_ai_buy_gate_min_score_quantile`, but the runtime gate only reads the quantile cutoff here. As a result, changing the promoted model's top-bucket configuration has no effect on live/paper filtering, so the gate can silently drift from the experiment settings that produced `rank_models.joblib`.
