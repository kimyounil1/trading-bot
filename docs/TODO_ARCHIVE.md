# TODO Archive (Phase 0–19)

완료된 로드맵 요약. 상세 체크리스트는 git history의 `TODO.md` (2026-05-27 이전) 참고.

| Phase | Theme | Key deliverables |
|-------|--------|------------------|
| 0–6 | Foundation | Core bot, data, backtest, AI baseline |
| 7 | Live monitoring | `report_performance.py`, correlation guard, circuit breaker, Telegram alerts |
| 8 | Regime-aware | `market_regime.py`, regime models, walk-forward validation |
| 9 | Signal quality | LGBM+XGB ensemble, earnings filter, SKEW/VVIX features |
| 10 | Dynamic profiles | `strategy_profiles.json`, ULTRA_AGGRESSIVE |
| 11 | Execution intelligence | Partial profit-taking, LLM consensus (`llm_analyst.py`) |
| 12 | DL / RL infra | `deep_model.py`, `rl_portfolio.py` (not live-integrated) |
| 13 | Universe & leverage | Dynamic universe, buying power, pyramiding |
| 14 | Exit precision | Trailing stop, rebalance trim |
| 15 | Sector rotation | `sector_rotation.py` |
| 16 | Execution resilience | Idempotency, atomic state files, audit logging |
| 17 | Model governance | Champion/challenger, drift, LLM cache/degraded mode |
| 18 | Portfolio risk | Exposure guards, macro events, exit priority rules |
| 19 | Tests & docs | E2E tests, schema validation, `docs/runbook.md` |

**Milestone (2026-05-27):** Phase 0–19 closed per Definition of Done (code + pytest + runbook).

| Phase | Theme | Key deliverables |
|-------|--------|------------------|
| 20 | Portfolio validation | Promotion gates (OOS P&L/Sharpe), weekly slippage report, portfolio pytest gates |
| 21 | Model quality | ML quality/calibration reports, dual promotion gates, rollback mocks |
| 22 | Ops observability | Daily audit summary, retrain Telegram paths, macro/earnings skip rates |
| 23 | Risk reports | Crowding guard backtest impact, leverage stress scenarios, LLM cache monitoring |
