# TODO Archive (Phase 0–39 + 2026-06/07 research pass)

완료된 로드맵 요약. 상세 체크리스트는 git history의 `TODO.md` 참고.

| Phase | Theme | Key deliverables |
|-------|--------|------------------|
| 0–6 | Foundation | Core bot, data, backtest, AI baseline |
| 7 | Live monitoring | `report_performance.py`, correlation guard, circuit breaker, Telegram alerts |
| 8 | Regime-aware | `market_regime.py`, regime models, walk-forward validation |
| 9 | Signal quality | LGBM+XGB ensemble, earnings filter, SKEW/VVIX features |
| 10 | Dynamic profiles | `strategy_profiles.json`, ULTRA_AGGRESSIVE |
| 11 | Execution intelligence | Partial profit-taking, LLM consensus (`llm_analyst.py`) |
| 12 | DL / RL infra | `deep_model.py`, `rl_portfolio.py` (not live — see `docs/RESEARCH_MODELS.md`) |
| 13 | Universe & leverage | Dynamic universe, buying power, pyramiding |
| 14 | Exit precision | Trailing stop, rebalance trim |
| 15 | Sector rotation | `sector_rotation.py` |
| 16 | Execution resilience | Idempotency, atomic state files, audit logging |
| 17 | Model governance | Champion/challenger, drift, LLM cache/degraded mode |
| 18 | Portfolio risk | Exposure guards, macro events, exit priority rules |
| 19 | Tests & docs | E2E tests, schema validation, `docs/runbook.md` |
| 20 | Portfolio validation | Promotion gates (OOS P&L/Sharpe), weekly slippage, portfolio pytest gates |
| 21 | Model quality | ML quality/calibration reports, dual promotion gates, rollback mocks |
| 22 | Ops observability | Daily audit summary, retrain Telegram paths, macro/earnings skip rates |
| 23 | Risk reports | Crowding backtest impact, leverage stress, LLM cache monitoring |
| 24 | Ops automation | `run_ops_reports.sh`, systemd timers, post-workflow audit smoke |
| 25 | Alpha / promotion quality | Fold variance report, promotion summary CLI, benchmark gap, champion governance |
| 26 | Live alignment (paper) | Crowding go/no-go, execution vs slippage diff, leverage/LLM cache alerts |
| 27 | Universe + instrument meta | Master CSV, UNIVERSE_PROFILE, leveraged ETF registry and buy gates |
| 28 | Margin leverage paper | Stress go/no-go gate, proposal caps, main buy block |
| 29 | Beat benchmark (alpha) | Promotion ≥ bench, EW benchmark fix, alpha/operational pipelines, LLM advisory-only, cache warmup |
| 30 | Paper ops maintenance | Bootstrap script, LLM advisory report wiring, crowding `--apply-config` (GO only), paper_ops summary |
| 31 | Extended hours & CMS parity | `buy_guards`, extended fill report, CMS reconcile, CI, `RUN_ID=phase31` Codex pass |
| 32 | Rank AI paper + LLM 강화 | rank buy/add gate ON + 14d 관측(`gate_ready=true` 06-16), `google.genai` + vLLM 폴백, crowding GO apply, paper validation trend, trailing 20% + SPY 벤치 |
| 33 | 고도화 검증 | rank forward-return, LLM block precision, calibration overlay, regime weakness, crowding reassessment, daily scheduler + Telegram fail alert |
| 34–35 | Live foundation | Broker v2 · FakeBroker · LiveSafetyGuard · LiveReadinessGate · OrderIntent · audit v2 · data health · dust parity · Alpaca order board |
| 36–38 | Portfolio sleeves | sleeve config/allocator · tournament profile + alpha adapter · CMS panel · `sleeve_runtime` · `main.py` split · position registry · drift trim · tournament buy path |
| 39 | Allocation rebalance + P&L | retag/rebalance plan + state · CMS sleeve actions · `portfolio_pnl_report` (FIFO realized) · tests · Codex clean |
| — | 2026-06 research 결론 | regime stop·intraday timing·promotion gates 결론 반영 / 모델 품질 트랙(calibration·regime feature·fold stability·gap_vol·3-track suite) → **exit params만 채택**(tr 0.15/tp 0.08, 06-24) / param sweep 5-B 거절 / live readiness 블로커 해소 / 현금 조사 → crowding 2→3 단독 적용(06-16) |
| — | 2026-07 리서치 소진 + 계측·하드닝 | 유니버스 110→255 A/B·실적 피처·VADER 뉴스·레짐 게이트 **전부 기각(6연속)** / 갭 어트리뷰션: 6월 paper +3.1% > 무제약 시뮬 +0.2% > SPY −0.9%, 최대 누수=슬리브 예산 / 증거 루프 3종(sleeve 데일리·레짐 스냅샷+전환알림·어트리뷰션 주간+8주 규칙) / 버그 4종 수리(ATR 크래시·sleeve 리포트 0-기록·트림 limit_price·테스트 로그 오염) / `universe_master.csv` 정리 / suite 503 green |

**Milestones**
- **2026-05-27:** Phase 0–19 closed (code + pytest + runbook).
- **2026-05-30:** Phase 20–23 closed; champion model git-untracked (`models/*.joblib` local-only).
- **2026-05-30:** Phase 24 closed; ops report batch + CI pytest/gates.
- **2026-05-30:** Phase 25 closed; promotion docs/CLI, fold variance, benchmark gap decomposition.
- **2026-05-30:** Phase 26 closed; paper crowding gate, execution alignment, stress/cache Telegram alerts.
- **2026-05-30:** Phase 27 closed; universe master/smoke/research profiles, instrument registry, leverage ETF gates.
- **2026-05-30:** Phase 28 closed; margin leverage paper gate wired to leverage stress + main.
- **2026-05-31:** Phase 29 closed; +96.8% vs B&H +65%, LLM advisory (no block), crowding paper gate NO_GO.
- **2026-06-01:** Phase 30 closed; paper ops bootstrap, advisory impact report, crowding apply-on-GO guard, `logs/paper_ops/latest_summary.json`.
- **2026-06-01:** Phase 31 closed; `buy_guards` main/cache parity, extended-hours fill report, CMS Alpaca reconcile, GitHub Actions CI (257 pytest), Codex phase31; crowding config stays off unless `APPLY_CROWDING_CONFIG=1`.
- **2026-06-11:** Live readiness 블로커 해소 (LLM precision 수리, ^VIX 오탐, verdict 파싱) — 시간 조건만 잔존.
- **2026-06-16:** Rank gate 14/14 관측 완료(`gate_ready=true`); crowding_max_positions 2→3 적용; live 전환은 paper 흑자까지 보류 결정.
- **2026-06-24:** Exit 파라미터 승격 (trailing 0.20→0.15, take_profit 0.10→0.08) — rank enhancement suite gate PASS. stop5_trail10 트라이얼은 이로써 superseded.
- **2026-07-06/07:** 리서치 레버 전수 검증·기각(6연속); 갭 어트리뷰션 + 증거 루프 3종 가동; 프로덕션 버그 4종 수리; **paper all-time +3.2% 흑자 전환**. 남은 판단은 ~09월(슬리브 배분·예산 A/B).
