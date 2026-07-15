# Backlog pass (TODO §6) — 3 self-contained items

## 1. Tournament sleeve report auto-verdict — `src/tournament_score_report.py`
- Adds verdict `PASS` / `FAIL` / `INSUFFICIENT_DATA` from tournament-sleeve excess
  return vs the best benchmark (SPY/QQQ/MTUM/EW). Threshold `--min-excess-return-pct`
  (default 0.0). `INSUFFICIENT_DATA` when sleeve/benchmark return is unavailable.
- `format_tournament_score_summary()` prints the pass/fail summary; `main()` prints it.
- Report keys are **additive only** — CMS consumer (`cms_sleeve_panel`) reads
  `tournament_sleeve.return_pct`, which is unchanged.

## 2. Gemini 429/quota resilience — `src/llm_analyst.py`
- New `_call_with_retry` wraps the Gemini call with **bounded** exponential backoff +
  jitter on retryable errors only (429 / RESOURCE_EXHAUSTED / 503 / quota / rate limit),
  honoring a server-suggested `retry_delay` when present. Auth errors (401/403/invalid
  key) are **never** retried.
- Fallback chain unchanged: Gemini(retry) → vLLM → degraded mode. The retry runs
  *inside* `_generate_gemini_text`, so `should_fallback_to_vllm` only sees exhausted
  retries (no double-retry).
- Env knobs (conservative defaults to bound live buy-gate latency):
  `LLM_MAX_RETRIES=2`, `LLM_RETRY_BASE_DELAY=2.0s`, `LLM_RETRY_MAX_DELAY=8.0s`.

## 3. `.gitignore` — stop tracking transient research noise
- `logs/ml/*` now ignored except curated records: `ai_model_metrics.csv`,
  `regime_weakness_report.json`, and the calibration runtime input
  `model_calibration_bins.csv`.
- Ignore `reports/agent_pipeline/<timestamp>/` (Codex run outputs) and `.claude-account-2/`.
- Untracked count 103 → 37 (remainder intentional: `.envrc`, named `phase*` dirs,
  `scripts/exp_*.py` per TODO §214).

## Tests
- `tests/test_tournament_score_report.py` (+6), `tests/test_llm_retry.py` (new, 9 incl.
  client integration). Full suite: **485 passed**.

## Review focus
- `llm_analyst` retry correctness: latency bound on the live LLM buy-gate path, no
  behavior change on the success path, retryable-error classification, no double-retry.
