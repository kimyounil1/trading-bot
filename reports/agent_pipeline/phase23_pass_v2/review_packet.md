# Agent Review Packet - Run: phase23_pass_v2

## Implementation Agent
cursor

## Task Description
Codex follow-up: model artifact untracked, phases 20-23 complete

## Changed Files
- .cursor/skills/pass-complete/SKILL.md
- .gitignore
- AGENTS.md
- AGY.md
- CURSOR.md
- GEMINI.md
- README.md
- TODO.md
- config/slippage_report_config.json
- docs/RESEARCH_MODELS.md
- docs/TODO_ARCHIVE.md
- docs/agent_review_harness.md
- docs/gemini_codex_harness.md
- docs/runbook.md
- models/.gitkeep
- models/ai_score_model.joblib
- prompts/agy/README.md
- prompts/agy/phase20_portfolio_gate.md
- prompts/agy/phase21_ml_quality.md
- prompts/agy/phase21_promotion_rollback.md
- scripts/agent_orchestrator.py
- scripts/agent_workload_report.py
- scripts/check_portfolio_backtest_gate.py
- scripts/install_slippage_report_timer.sh
- scripts/run_agy_slice.sh
- scripts/run_balanced_pass.sh
- scripts/run_daily_audit_summary.sh
- scripts/run_gemini_post_workflow.sh
- scripts/run_guard_impact_report.sh
- scripts/run_leverage_stress_report.sh
- scripts/run_llm_cache_report.sh
- scripts/run_model_quality_report.sh
- scripts/run_pass_complete.sh
- scripts/run_retrain.sh
- scripts/run_weekly_slippage_report.sh
- src/daily_audit_summary.py
- src/guard_impact_metrics.py
- src/guard_impact_report.py
- src/leverage_stress_report.py
- src/llm_cache_report.py
- src/ml_model.py
- src/ml_quality_report.py
- src/model_governance.py
- src/portfolio_backtest_validation.py
- src/portfolio_backtester.py
- src/report_performance.py
- src/retrain_holdout.py
- src/retrain_notifications.py
- src/train_ai_model.py
- src/walk_forward_validation.py
- tests/fixtures/audit_daily/golden_execution_audit.csv
- tests/fixtures/audit_daily/golden_latest_summary.json
- tests/fixtures/audit_daily/golden_output/skip_reasons_20260530.csv
- tests/fixtures/llm_monitoring/golden_llm_cache.json
- tests/fixtures/ml_quality/golden_fold_metrics.csv
- tests/fixtures/ml_quality/golden_fold_stability_report.json
- tests/fixtures/ml_quality/golden_model_calibration_bins.csv
- tests/fixtures/ml_quality/golden_model_calibration_report.json
- tests/fixtures/portfolio_backtest/portfolio_equity.csv
- tests/fixtures/portfolio_backtest/portfolio_summary.csv
- tests/fixtures/portfolio_backtest/portfolio_trades.csv
- tests/test_daily_audit_summary.py
- tests/test_daily_audit_summary_schema.py
- tests/test_guard_impact_report.py
- tests/test_leverage_stress_report.py
- tests/test_llm_cache_report_schema.py
- tests/test_ml_quality_report.py
- tests/test_ml_quality_report_schema.py
- tests/test_model_governance.py
- tests/test_model_governance_rollback.py
- tests/test_portfolio_backtest_gate.py
- tests/test_portfolio_backtest_golden.py
- tests/test_promotion_rollback_path.py
- tests/test_report_performance.py
- tests/test_retrain_holdout.py
- tests/test_retrain_notifications.py

## Git Diff Summary
```
 .cursor/skills/pass-complete/SKILL.md              |  81 ++++
 .gitignore                                         |   4 +
 AGENTS.md                                          |  11 +-
 AGY.md                                             |  48 +-
 CURSOR.md                                          |  24 +-
 GEMINI.md                                          |  14 +-
 README.md                                          |  21 +-
 TODO.md                                            | 240 +++-------
 config/slippage_report_config.json                 |   7 +
 docs/RESEARCH_MODELS.md                            |  10 +
 docs/TODO_ARCHIVE.md                               |  29 ++
 docs/agent_review_harness.md                       |  24 +-
 docs/gemini_codex_harness.md                       |   2 +-
 docs/runbook.md                                    |  31 +-
 models/.gitkeep                                    |   0
 models/ai_score_model.joblib                       | Bin 1757990 -> 0 bytes
 prompts/agy/README.md                              |  13 +
 prompts/agy/phase20_portfolio_gate.md              |  35 ++
 prompts/agy/phase21_ml_quality.md                  |  11 +
 prompts/agy/phase21_promotion_rollback.md          |  14 +
 scripts/agent_orchestrator.py                      |  60 ++-
 scripts/agent_workload_report.py                   | 247 ++++++++++
 scripts/check_portfolio_backtest_gate.py           |  81 ++++
 scripts/install_slippage_report_timer.sh           |  64 +++
 scripts/run_agy_slice.sh                           |  17 +
 scripts/run_balanced_pass.sh                       |  39 ++
 scripts/run_daily_audit_summary.sh                 |   9 +
 scripts/run_gemini_post_workflow.sh                |  21 +-
 scripts/run_guard_impact_report.sh                 |   9 +
 scripts/run_leverage_stress_report.sh              |   9 +
 scripts/run_llm_cache_report.sh                    |   9 +
 scripts/run_model_quality_report.sh                |  14 +
 scripts/run_pass_complete.sh                       |  81 ++++
 scripts/run_retrain.sh                             |  10 +
 scripts/run_weekly_slippage_report.sh              |  46 ++
 src/daily_audit_summary.py                         | 293 ++++++++++++
 src/guard_impact_metrics.py                        |  37 ++
 src/guard_impact_report.py                         | 179 ++++++++
 src/leverage_stress_report.py                      | 166 +++++++
 src/llm_cache_report.py                            | 149 ++++++
 src/ml_model.py                                    | 140 +++++-
 src/ml_quality_report.py                           | 497 ++++++++++++++++++++
 src/model_governance.py                            | 121 +++++
 src/portfolio_backtest_validation.py               | 236 ++++++++++
 src/portfolio_backtester.py                        |  11 +
 src/report_performance.py                          | 409 ++++++++++++++---
 src/retrain_holdout.py                             |  60 +++
 src/retrain_notifications.py                       |  41 ++
 src/train_ai_model.py                              | 403 ++++++++++-------
 src/walk_forward_validation.py                     |  53 ++-
 .../audit_daily/golden_execution_audit.csv         |   6 +
 .../audit_daily/golden_latest_summary.json         |  41 ++
 .../golden_output/skip_reasons_20260530.csv        |   5 +
 .../fixtures/llm_monitoring/golden_llm_cache.json  |  23 +
 tests/fixtures/ml_quality/golden_fold_metrics.csv  |   5 +
 .../ml_quality/golden_fold_stability_report.json   |  36 ++
 .../ml_quality/golden_model_calibration_bins.csv   |  21 +
 .../golden_model_calibration_report.json           |  15 +
 .../portfolio_backtest/portfolio_equity.csv        | 501 +++++++++++++++++++++
 .../portfolio_backtest/portfolio_summary.csv       |   2 +
 .../portfolio_backtest/portfolio_trades.csv        |  43 ++
 tests/test_daily_audit_summary.py                  |  82 ++++
 tests/test_daily_audit_summary_schema.py           |  83 ++++
 tests/test_guard_impact_report.py                  |  45 ++
 tests/test_leverage_stress_report.py               |  39 ++
 tests/test_llm_cache_report_schema.py              |  32 ++
 tests/test_ml_quality_report.py                    | 141 ++++++
 tests/test_ml_quality_report_schema.py             |  59 +++
 tests/test_model_governance.py                     | 116 ++++-
 tests/test_model_governance_rollback.py            |  65 +++
 tests/test_portfolio_backtest_gate.py              | 135 ++++++
 tests/test_portfolio_backtest_golden.py            |  42 ++
 tests/test_promotion_rollback_path.py              |  76 ++++
 tests/test_report_performance.py                   |  85 +++-
 tests/test_retrain_holdout.py                      |  35 ++
 tests/test_retrain_notifications.py                |  65 +++
 76 files changed, 5421 insertions(+), 507 deletions(-)
```

## Test Execution Results (runtime_harness.log)
```
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.0.3, pluggy-1.6.0
rootdir: /home/kimyo/trading-bot
plugins: anyio-4.13.0
collected 11 items

tests/test_report_performance.py .....                                   [ 45%]
tests/test_reappraise_regime.py ...                                      [ 72%]
tests/test_portfolio_backtest_golden.py ...                              [100%]

=============================== warnings summary ===============================
.venv/lib/python3.12/site-packages/websockets/legacy/__init__.py:6
  /home/kimyo/trading-bot/.venv/lib/python3.12/site-packages/websockets/legacy/__init__.py:6: DeprecationWarning: websockets.legacy is deprecated; see https://websockets.readthedocs.io/en/stable/howto/upgrade.html for upgrade instructions
    warnings.warn(  # deprecated in 14.0 - 2024-11-09

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 11 passed, 1 warning in 0.69s =========================
```

## Git Patch
```diff
diff --git a/.cursor/skills/pass-complete/SKILL.md b/.cursor/skills/pass-complete/SKILL.md
new file mode 100644
index 0000000..c0710d4
--- /dev/null
+++ b/.cursor/skills/pass-complete/SKILL.md
@@ -0,0 +1,81 @@
+---
+name: pass-complete
+description: >-
+  Close a Cursor+AGY development pass: run pytest, invoke the agent orchestrator
+  for Codex scoped review, read NEXT_TODO.codex.md, and loop on fixes. Use when
+  finishing implementation, after [AGY] tests, before marking TODO [x], or when
+  the user says pass complete, Codex review, or run_pass_complete.
+---
+# Pass complete (Cursor-first)
+
+Replace the legacy pattern where **Gemini CLI** called `agent_orchestrator.py --run-gemini`.
+In this repo **Cursor** implements, **AGY** owns `[AGY]` tests, **Codex** reviews via the orchestrator.
+
+## When to apply
+
+- After Cursor feature work **and** `[AGY]` pytest/harness work are done on the branch.
+- AGY tasks live under `prompts/agy/*.md` — run in a **separate AGY account session**, then return here.
+- Before checking `[x]` on any `TODO.md` item (Definition of Done §4).
+- When the user asks to close a pass, run Codex review, or check `NEXT_TODO`.
+
+## Do not
+
+- Run `--run-gemini` unless the user explicitly requests legacy headless mode.
+- Skip Codex because credits failed once — report failure and retry with `SKIP_PYTEST=1`.
+- Mark TODO complete without reading `NEXT_TODO.codex.md` when Codex succeeded.
+
+## Steps (execute in the shell)
+
+1. Choose `RUN_ID` (e.g. `phase20_ci`, `cursor_$(date +%Y%m%dT%H%M%S)`).
+
+2. Run **balanced pass** (AGY pytest + orchestrator + Codex) — preferred:
+
+```bash
+cd <repo-root>
+RUN_ID=<run_id> bash scripts/run_balanced_pass.sh
+# or: .venv/bin/python scripts/agent_orchestrator.py --run-id <run_id> --balanced-pass --task-file prompts/agy/<task>.md
+```
+
+Legacy (Codex only, tests already green):
+
+```bash
+RUN_ID=<run_id> bash scripts/run_pass_complete.sh "<one-line summary>"
+```
+
+Use `SKIP_PYTEST=1` only if pytest already passed in this session.  
+Use `FULL_PYTEST=1` only when the full ML stack (e.g. xgboost) is installed.
+
+3. Read outputs:
+   - `reports/agent_pipeline/<run_id>/NEXT_TODO.codex.md` — **primary queue**
+   - `reports/agent_pipeline/<run_id>/CODEX_REVIEW_AND_TODO.md` — full review if needed
+   - `reports/agent_pipeline/<run_id>/review_packet.md` — handoff context
+
+4. If Codex reports blocking issues (P0/P1 or test failures):
+   - Fix in Cursor (or delegate `[AGY]` items to an AGY session).
+   - Re-run step 2 with the same or new `RUN_ID` until clean or user stops.
+
+5. Record workload (optional):
+
+```bash
+PYTHONPATH=. .venv/bin/python scripts/agent_workload_report.py --record
+```
+
+6. Tag commits: `[cursor]` for production code, `[agy]` for test-only commits.
+
+## AGY is not invoked by the orchestrator
+
+The orchestrator **does not** open AGY. Before step 2, for **multi-account token balancing** (preferred):
+- User runs a **separate AGY session** for `[AGY]` tests after Cursor commits (do not duplicate tests in Cursor).
+- Cursor may write tests only when AGY quota is exhausted for the week or the change is trivial (≤2 test files, no `main.py`).
+
+Check balance: `PYTHONPATH=. .venv/bin/python scripts/agent_workload_report.py`
+
+## Phase report to user
+
+When all items in a Phase section are `[x]` and Codex is clean, summarize for the user:
+- what shipped, test commands run, `RUN_ID`(s), and residual risks from Codex.
+
+## Reference
+
+- `scripts/run_pass_complete.sh` — pytest + `agent_orchestrator.py --run-codex-review --scoped-review --ignore-artifacts`
+- `docs/agent_review_harness.md`, `CURSOR.md`, `AGY.md`
diff --git a/.gitignore b/.gitignore
index 843aa73..c4cf60c 100644
--- a/.gitignore
+++ b/.gitignore
@@ -30,6 +30,10 @@ logs/*
 !logs/portfolio_backtest/
 !logs/portfolio_backtest/*summary*.csv
 
+# Champion model binaries are local-only (retrain + promotion); never commit ad-hoc retrains.
+models/*
+!models/.gitkeep
+
 # Never commit bulky/generated trading artifacts.
 logs/**/portfolio_equity.csv
 logs/**/portfolio_trades.csv
diff --git a/AGENTS.md b/AGENTS.md
index a593d61..7823fd0 100644
--- a/AGENTS.md
+++ b/AGENTS.md
@@ -89,18 +89,19 @@ Ask the user only before:
 ## Cursor / Codex / AGY Review Harness
 - **Cursor IDE** is the primary interactive implementation environment. Follow `CURSOR.md` when implementing in Cursor.
 - **Codex** is the default reviewer, verifier, and planning agent unless the user explicitly asks Codex to implement fixes.
-- **AGY** is an optional secondary reviewer for architecture, strategy, risk, and alternative designs (`AGY.md`).
-- **Gemini CLI** is an optional legacy headless implementer (`--run-gemini`); do not run it on the same branch while Cursor is editing.
+- **AGY** owns **`[AGY]` test and harness slices** (preferred over Gemini CLI); optional reviewer for architecture, strategy, and risk (`AGY.md`).
+- **Gemini CLI** is legacy headless (`--run-gemini`), **docs/low-risk only** — weaker default model than AGY; do not use for pytest or trading paths.
 - The review harness lives in `docs/agent_review_harness.md` and `codex_harness/agent_contract.json` (when present).
-- After Cursor (or any single implementer) finishes work, run `bash scripts/run_cursor_post_workflow.sh` to collect diffs, test logs, a Codex review packet, and a draft `NEXT_TODO.md` under `reports/agent_pipeline/<run_id>/`.
-- For **review-only** after Cursor edits: `.venv/bin/python scripts/agent_orchestrator.py --run-codex-review --scoped-review`.
+- After Cursor + `[AGY]` tests, run **`bash scripts/run_pass_complete.sh`** (preferred) or follow project skill `.cursor/skills/pass-complete/SKILL.md`.
+- Legacy packet-only: `bash scripts/run_cursor_post_workflow.sh` (insufficient alone for Definition of Done).
+- For **review-only** without the wrapper: `.venv/bin/python scripts/agent_orchestrator.py --run-id <id> --run-codex-review --scoped-review --ignore-artifacts`.
 - For legacy headless implement + review: `.venv/bin/python scripts/agent_orchestrator.py --task "..." --run-gemini --run-codex-review`.
 - When changing `AGENTS.md`, `CURSOR.md`, `AGY.md`, `GEMINI.md`, workflow docs, guardrails, handoff rules, or eval cases, run `bash scripts/run_gemini_review_harness.sh` (legacy script name).
 - **README Maintenance**: During review, verify if `README.md` needs updates. If missing, flag and include required text in the next plan.
 - Before final reporting on broad agent-harness work, prefer `bash scripts/codex_pre_final_check.sh` when available.
 
 ### Multi-agent working tree rule
-Only one implementation agent may edit the working tree at a time. Default: Cursor edits; Codex reviews read-only; AGY reviews read-only or plan-only. Codex or AGY may implement fixes only when explicitly asked, preferably on a separate branch.
+Only one implementation agent may edit the working tree at a time. Default: Cursor edits production code; **AGY edits tests when assigned `[AGY]`**; Codex reviews read-only. AGY or Codex may touch non-test code only when explicitly asked, preferably on a separate branch.
 
 ### Codex (review-only)
 When reviewing implementation work:
diff --git a/AGY.md b/AGY.md
index c7eb2a2..acc8e7c 100644
--- a/AGY.md
+++ b/AGY.md
@@ -1,26 +1,41 @@
 # AGY.md
 
-Optional secondary review rules for **AGY** (Antigravity / Gemini-based design assistant). AGY is **not** the primary implementer in this repository.
+Rules for **AGY** (Antigravity / stronger Gemini-tier assistant). AGY is **not** the primary production implementer, but it **is** the preferred agent for **test and harness work** in this repo.
+
+**Model note:** AGY sessions typically use a stronger model (e.g. Gemini Pro tier) than **Gemini CLI** headless defaults (often Flash-class). Prefer AGY over Gemini CLI for anything that must be correct on first try (tests, risk regressions, calibration reports).
 
 ## Role
 
-| Agent | Role |
-|-------|------|
-| **Cursor** | Primary interactive implementation (IDE) |
-| **Codex** | Default read-only reviewer, verifier, planner |
-| **AGY** | Optional second opinion on architecture, strategy, and risk |
-| **Gemini CLI** | Optional legacy headless implementer (`--run-gemini`) |
+| Agent | Role | Typical share (target) |
+|-------|------|-------------------------|
+| **Cursor** | Primary implementation: `main.py`, orders, integration, config wiring | ~60–70% |
+| **Codex** | Read-only review, test verification, `NEXT_TODO` per pass | ~15–20% |
+| **AGY** | **Tests & harness** (`[AGY]` slices); optional architecture/strategy/risk review | ~20–30% (별도 AGY 계정·쿼터) |
+| **Gemini CLI** | Legacy, low-risk only (`--run-gemini`); avoid for tests | ~0–5% |
 
-## When to Involve AGY
+## When to Involve AGY (review)
 
-Request AGY review when changes touch:
+Request AGY **review** when changes touch:
 - trading strategy semantics (buy/sell gates, regime logic, profile switching);
 - portfolio or execution risk (leverage, concentration, circuit breakers, correlation);
 - model governance (promotion, rollback, calibration, drift);
 - large refactors that span multiple core modules;
 - alternative designs worth comparing before merge.
 
-Skip AGY for: typo fixes, pure test additions, README-only updates, or changes already fully covered by Codex review.
+## When to Assign AGY (implement — `[AGY]`)
+
+Route **implementation** to AGY (explicit invoke; separate branch or sequential pass; still only one implementer at a time) for:
+- new or extended **pytest** for behavior Cursor just added (mock broker, mock LLM, fault injection);
+- **regression tests** for partial exit / trim / trailing / earnings / macro skip combinations;
+- **harness scripts** under `tests/harness/` and calibration/backtest **report generators** that do not touch live order paths;
+- portfolio/walk-forward **validation scripts** and golden-file checks on `logs/` outputs;
+- property-style tests on pure functions (`risk_manager`, `correlation_guard`, schema validators).
+
+**Cursor keeps:** `main.py` integration, Alpaca order paths, profile/regime wiring, and merging AGY test PRs after green pytest.
+
+**Do not assign AGY:** live order submission changes, secrets, `.env`, or same-branch concurrent edits with Cursor.
+
+Skip AGY entirely for: typo-only README, comment-only diffs already approved by Codex with no behavioral gap.
 
 ## Default AGY Stance
 
@@ -32,10 +47,19 @@ AGY should:
 5. End with a short, actionable plan — not a full reimplementation unless asked.
 
 AGY must **not**:
-- edit the working tree during review unless explicitly asked;
+- edit the working tree during **review** unless explicitly asked;
 - place or enable live trades;
 - edit secrets, `.env`, or production deployment configs;
-- run concurrently with Cursor or Gemini CLI as a second implementer on the same branch.
+- run concurrently with Cursor or Gemini CLI as a second implementer on the same branch;
+- replace Codex for `NEXT_TODO` drafting (Codex stays the per-pass queue owner).
+
+### AGY test implementation handoff
+
+1. Cursor lands feature code + minimal smoke test if needed.
+2. User invokes AGY with `[AGY]` task file (scope: tests only, files list, interfaces to mock).
+3. AGY adds tests; runs `PYTHONPATH=. .venv/bin/python -m pytest <paths>`.
+4. Cursor merges or rebases; runs full suite.
+5. **패스 마감:** `RUN_ID=<pass> bash scripts/run_pass_complete.sh` → Codex 리뷰 → `NEXT_TODO.codex.md` 확인 (AGY 테스트만 끝내고 리뷰 생략 금지).
 
 ## Handoff Format
 
diff --git a/CURSOR.md b/CURSOR.md
index 4491207..69ebbf5 100644
--- a/CURSOR.md
+++ b/CURSOR.md
@@ -71,19 +71,20 @@ Include:
 
 Codex reviews with `docs/agent_review_harness.md` and `AGENTS.md` (review-only section).
 
-When the implementation pass is complete, run:
+When **Cursor implementation + `[AGY]` tests** are complete, close the pass (do not skip Codex):
 
 ```bash
-RUN_ID=cursor_$(date +%Y%m%dT%H%M%S) bash scripts/run_cursor_post_workflow.sh
+RUN_ID=cursor_$(date +%Y%m%dT%H%M%S) bash scripts/run_pass_complete.sh "summary of this pass"
 ```
 
-Then ask Codex to review:
+This runs pytest → `review_packet.md` → Codex scoped review → writes `NEXT_TODO.codex.md`.
 
-```text
-reports/agent_pipeline/<run_id>/review_packet.md
-```
+Read `reports/agent_pipeline/<run_id>/NEXT_TODO.codex.md` before starting the next feature.  
+If Codex fails (credits/CLI), fix and re-run with `SKIP_PYTEST=1` after local pytest is already green.
+
+Legacy (packet only, no Codex): `bash scripts/run_cursor_post_workflow.sh`
 
-Use `NEXT_TODO.codex.md` (or Codex's rewritten `NEXT_TODO.md`) as the next work queue.
+**Cursor automation:** apply project skill `.cursor/skills/pass-complete/SKILL.md` at the end of every implementation pass (replaces Gemini CLI auto-calling the orchestrator).
 
 **Review-only (no headless implementer):**
 
@@ -135,9 +136,12 @@ Never let multiple agents edit the same branch concurrently.
 - **Performance Reporting**: Run `PYTHONPATH=. .venv/bin/python src/report_performance.py` for slippage and P&L analysis.
 - **Fault Injection**: Any new risk logic or API interaction must be tested against `tests/harness/test_fault_injection.py`.
 
-## Task Ownership Labels (with Gemini CLI)
+## Task Ownership Labels
 
 When splitting work across agents, label tasks in `TODO.md` or task files:
-- `[Cursor]` — main integration, `main.py`, orders, portfolio/risk guards.
-- `[Gemini]` — isolated modules, tests, docs, CMS (headless via `--run-gemini`).
+- `[Cursor]` — main integration, `main.py`, orders, portfolio/risk guards, config wiring.
+- `[AGY]` — **pytest**, `tests/harness/`, regression/fault-injection, calibration & backtest report scripts (no live order paths). Invoke AGY explicitly after Cursor lands the feature under test.
+- `[Gemini]` — **deprecated for tests**; docs-only or mechanical non-trading edits via `--run-gemini` if no AGY session available.
 - `[Either]` — README or non-risk utilities (still only one implementer at a time).
+
+**Suggested split per feature:** Cursor implements → AGY test pass → Codex review → Cursor merge fixes.
diff --git a/GEMINI.md b/GEMINI.md
index 5fe8717..c1d10e6 100644
--- a/GEMINI.md
+++ b/GEMINI.md
@@ -1,6 +1,8 @@
 # GEMINI.md
 
-> **Primary implementer:** use [`CURSOR.md`](CURSOR.md) for Cursor (IDE). This file applies to **Gemini CLI** only (optional legacy headless implementer via `--run-gemini`).
+> **Primary implementer:** [`CURSOR.md`](CURSOR.md) (Cursor IDE). **Tests & harness:** [`AGY.md`](AGY.md) (`[AGY]`). This file applies to **Gemini CLI** only — **legacy, lowest priority.**
+
+**Quality warning:** Gemini CLI headless runs often default to a **faster/weaker** model than AGY (Pro-tier) sessions. Do **not** use Gemini CLI for trading tests, risk regressions, or model-governance logic. Use **AGY** for `[AGY]` test slices; use Cursor for production code.
 
 Behavioral guidelines to reduce common LLM coding mistakes and ensure the Trading Bot's reliability. These rules govern how **Gemini CLI** operates within this workspace when used as a headless implementation agent.
 
@@ -82,7 +84,15 @@ For a headless Gemini ↔ Codex loop:
 .venv/bin/python scripts/agent_orchestrator.py --task-file <task.md> --run-gemini --run-codex-review
 ```
 
-Only one implementer (Cursor **or** Gemini CLI) may edit the branch at a time. See `CURSOR.md` § Multi-Agent Working Tree Rule.
+Only one implementer (Cursor, **AGY**, or Gemini CLI) may edit the branch at a time. See `CURSOR.md` § Multi-Agent Working Tree Rule.
+
+## Allowed Gemini CLI scope (if used at all)
+
+- README / runbook wording, non-trading docs;
+- mechanical refactors with **zero** behavior change and Codex review immediately after;
+- one-off scripts explicitly marked `[Gemini]` and **outside** `src/main.py`, `src/alpaca_client.py`, risk guards.
+
+**Forbidden for Gemini CLI:** new pytest suites, harness evals, champion/challenger logic, order/idempotency paths — assign **`[AGY]`** instead.
 
 ### 6. Automatic Documentation Maintenance
 **Keep the entry point (README.md) synchronized with code changes.**
diff --git a/README.md b/README.md
index 77faba7..922c922 100644
--- a/README.md
+++ b/README.md
@@ -31,7 +31,7 @@ trading-bot/
 ├── config/             # 전략 프로필 및 시스템 설정 (JSON)
 ├── data/               # 피크 정보, LLM 캐시, 트레일링 스탑 데이터
 ├── logs/               # 실행 감사(Audit), 주문, 신호 로그 (CSV)
-├── models/             # 학습된 레짐별 AI 모델 파일
+├── models/             # 챔피언 모델 (로컬, git 미추적 — retrain·승격 후 생성)
 ├── scripts/            # 실행, 서비스 등록 및 에이전트 오케스트레이터
 │   ├── agent_orchestrator.py # Codex 리뷰 / optional Gemini CLI 루프
 │   ├── run_cursor_post_workflow.sh # Cursor 구현 후 리뷰 패킷 수집
@@ -51,17 +51,20 @@ trading-bot/
 
 | 역할 | 담당 | 규칙 문서 |
 |------|------|-----------|
-| **Cursor** | 메인 구현 (WSL Remote IDE) | [`CURSOR.md`](CURSOR.md) |
-| **Codex** | read-only 리뷰, 검증, `NEXT_TODO` | [`AGENTS.md`](AGENTS.md) |
-| **AGY** | (선택) 설계·전략·리스크 2차 검토 | [`AGY.md`](AGY.md) |
-| **Gemini CLI** | (선택) headless 구현 (`--run-gemini`) | [`GEMINI.md`](GEMINI.md) |
+| **Cursor** | 메인 구현 (~60–70%) | [`CURSOR.md`](CURSOR.md) |
+| **Codex** | read-only 리뷰, `NEXT_TODO` (~15–20%) | [`AGENTS.md`](AGENTS.md) |
+| **AGY** | **`[AGY]` 테스트·하네스** + 전략/리스크 검토 (~15–25%) | [`AGY.md`](AGY.md) |
+| **Gemini CLI** | 레거시·문서만 (~0–5%, 테스트 금지) | [`GEMINI.md`](GEMINI.md) |
 
 **평소 흐름**
 
-1. Cursor에서 구현 및 `pytest` 실행
-2. `RUN_ID=my_feature bash scripts/run_cursor_post_workflow.sh` 로 리뷰 패킷 생성
-3. `.venv/bin/python scripts/agent_orchestrator.py --run-codex-review --scoped-review` 로 Codex 리뷰
-4. 전략/리스크 대형 변경 시 AGY 추가 검토
+1. Cursor에서 기능 구현 (핵심 경로)
+2. **AGY**에 `[AGY]` 테스트 슬라이스 위임 → `pytest` green
+3. **패스 마감 (필수):** `RUN_ID=my_feature bash scripts/run_pass_complete.sh`
+4. `reports/agent_pipeline/<run_id>/NEXT_TODO.codex.md` 확인 후 Cursor가 follow-up 반영
+5. 전략/리스크 대형 변경 시 AGY 설계 리뷰 추가
+
+작업량 비율: `PYTHONPATH=. .venv/bin/python scripts/agent_workload_report.py --record` (커밋 메시지 `[cursor]` / `[agy]` 태그)
 
 상세: [docs/agent_review_harness.md](docs/agent_review_harness.md) (구 [gemini_codex_harness.md](docs/gemini_codex_harness.md))
 
diff --git a/TODO.md b/TODO.md
index 56cfaf8..fd7720a 100644
--- a/TODO.md
+++ b/TODO.md
@@ -1,216 +1,114 @@
 # TODO
 
 ## Definition of Done (완료 기준)
-본 프로젝트의 모든 TODO 항목은 단순히 **"코드 작성/존재"**만으로 완료 처리하지 않으며, 다음 **3가지 검증 조건**을 모두 충족해야 완료(`[x]`)로 표시합니다:
-1. **코드 구현 (Code Existence)**: 요구사항에 부합하는 소스 코드가 스타일 가이드를 준수하여 작성되어야 함.
-2. **테스트 검증 (Test Verification)**: 신규 기능 및 수정 본에 대한 단위/통합 테스트 코드가 작성되어야 하며, 전체 pytest Suite가 100% 통과해야 함.
-3. **운영 및 보고서 검증 (Operations & Report Validation)**: 
-   - 필요 시 백테스트 실행 및 성능 요약 리포트(P&L, 슬리피지 등)를 자동으로 생성하거나 확인해야 함.
-   - `bash scripts/run_cursor_post_workflow.sh` 후 Codex 리뷰를 통해 오류나 경고가 없이 **APPROVED**를 획득해야 함.
-
----
-
-## Agent Workflow (Cursor-First)
-
-| 역할 | 담당 | 문서 |
-|------|------|------|
-| **Cursor** | 메인 구현·통합·`main.py`/주문·리스크 | `CURSOR.md` |
-| **Codex** | read-only 리뷰·테스트 검증·`NEXT_TODO` | `AGENTS.md`, `docs/agent_review_harness.md` |
-| **AGY** | (선택) 설계·전략·리스크·대안 검토 | `AGY.md` |
-| **Gemini CLI** | (선택) headless 슬라이스 구현 | `GEMINI.md`, `--run-gemini` |
-
-**규칙:** 한 브랜치에서 구현 에이전트는 동시에 하나만 (Cursor **또는** Gemini CLI).
-
-**작업 라벨:** 신규 Phase 항목에 `[Cursor]` / `[Gemini]` / `[Either]` 를 붙여 분담.
-
-**리뷰 패킷:**
+항목을 `[x]`로 두려면 다음을 **모두** 충족:
+1. **코드** — 요구사항 반영, 프로젝트 스타일 준수
+2. **테스트** — 관련 pytest 추가·통과, 전체 suite green
+3. **운영** — 필요 시 백테스트/리포트 확인
+4. **Codex 리뷰 (필수)** — Cursor 구현 + `[AGY]` 테스트까지 끝난 뒤 **반드시** 패스 마감:
 
 ```bash
-RUN_ID=phase20_a bash scripts/run_cursor_post_workflow.sh
-.venv/bin/python scripts/agent_orchestrator.py --run-id phase20_a --run-codex-review --scoped-review
+RUN_ID=<pass_id> bash scripts/run_pass_complete.sh "무엇을 했는지 한 줄"
+# → review_packet.md 생성 → Codex scoped review → NEXT_TODO.codex.md 확인
+# blocking 이슈 없을 때만 [x]. 실패 시 Codex 지적 반영 후 재실행.
 ```
 
 ---
 
-## Current Status (2026-05-27)
-
-### Active Config
-- Tickers: 110개 (`config/strategy_config.json`)
-- AI model: **LightGBM + XGBoost Ensemble**, 24 features
-- Regime-Aware: **BULL / BEAR / NEUTRAL** 별 독립 모델 및 프로필 가동
-- Dynamic Profile: **ULTRA_AGGRESSIVE** (BULL 시 33% 비중 집중 투자)
-- AI exit: **MA primary / VIX>30 공황 시에만 AI score<0.45 청산**
-- Risk Guards: Circuit Breaker (-15%), Correlation Guard (0.85), Earnings Filter (+3/-1d)
-- Daily retraining: 매 평일 06:00 ET (systemd timer)
-
-### OOS Validated Performance (test: 2024-05-27 ~ 2026-05-27)
-- **Ultra Aggressive (Bull)**: 5개월 수익률 **+41.68%**, Sharpe 2.51
-- **Regime-Aware Ensemble**: Bear 시장 예측력(ROC-AUC 0.64) 대폭 강화
-- 슬리피지: 평균 0.36% (안정적)
-
----
-
-## Phase 0-6 ✅ Complete
-(이전 단계 완료)
-
----
-
-## Phase 7 — Live Performance & Risk Monitoring ✅ Complete
-
-- [x] Alpaca paper account 실제 거래 내역 vs 백테스트 비교 리포트 (`src/report_performance.py`)
-- [x] `src/logger.py`: 주문 로그 컬럼 일관성 수정
-- [x] 상관관계 기반 포지션 제한 (`src/correlation_guard.py`)
-- [x] Drawdown circuit breaker (-15%) 구현
-- [x] VIX panic 및 모델 성능 저하 알림 (Telegram)
-
----
-
-## Phase 8 — Regime-Aware Modeling ✅ Complete
-
-- [x] 시장 레짐 분류 로직 (`src/market_regime.py`): VIX + SPY 추세 기반
-- [x] 레짐별 별도 모델 학습 및 실시간 전환 로직 (`src/ml_model.py`)
-- [x] Walk-Forward 검증 자동화 (`src/walk_forward_validation.py`)
-
----
+## Who owns what (TODO 담당)
 
-## Phase 9 — Signal Quality 개선 ✅ Complete
+| 문서 | 역할 | 누가 쓰나 |
+|------|------|-----------|
+| **`TODO.md`** (이 파일) | 중기 로드맵·Phase | **사용자 + Cursor**가 Phase/우선순위 갱신. 전략·리스크는 **AGY** 검토, **테스트는 `[AGY]`** |
+| **`reports/.../NEXT_TODO.md`** | 이번 PR/패스 직후 작업 큐 | `run_cursor_post_workflow.sh`가 **초안** 생성 |
+| **`NEXT_TODO.codex.md`** | 리뷰 후 다음 구현 큐 | **Codex**가 리뷰 끝에 작성 (`# NEXT_TODO for Cursor`) |
+| **완료 Phase 기록** | 토큰 절약용 요약 | **`docs/TODO_ARCHIVE.md`** — Phase 0–19 요약만 유지 |
 
-- [x] LightGBM + XGBoost 앙상블 모델 (Soft Voting) 도입
-- [x] 어닝 캘린더 필터 (`src/earnings.py`): 실적 발표 전후 매수 차단
-- [x] 옵션 시장 신호 (`^SKEW`, `^VVIX`) 피처 추가 및 재학습
+**루프:** Cursor 구현 → post-workflow → Codex 리뷰·`NEXT_TODO` → Cursor가 다음 슬라이스. 장기 Phase는 Codex 출력을 보고 **사용자가 `TODO.md`에 반영**하는 것이 기본(자동 merge 아님).
 
 ---
 
-## Phase 10 — Dynamic Strategy Profiles ✅ Complete
-
-- [x] 시장 레짐별 다이내믹 프로필 시스템 구축 (`config/strategy_profiles.json`)
-- [x] **ULTRA_AGGRESSIVE** 모드 최적화: 강세장 수익률 극대화 (33% 집중 투자)
-- [x] 수동 오버라이드 및 자동 전환 로직 검증 완료
-
----
+## Agent Workflow (Cursor-First)
 
-## Phase 11 — 실행 고도화 및 지능화 ✅ Complete
+| 역할 | 담당 |
+|------|------|
+| **Cursor** | 메인 구현 (`CURSOR.md`) |
+| **Codex** | read-only 리뷰, `NEXT_TODO` (~15–20%) |
+| **AGY** | **`[AGY]` 테스트·하네스** + (선택) 전략·리스크 검토 (~15–25%) |
+| **Gemini CLI** | 레거시·문서만 (~0–5%, Flash급 — 테스트 금지) |
 
-- [x] **분할 매도 로직 (Partial Profit-Taking)**: 수익률 +15% 도달 시 비중의 50%를 선제적으로 익절하여 수익 보존 (`src/main.py`)
-- [x] **LLM Consensus (Gemini)**: 매수 전 최신 뉴스를 LLM(Gemini)이 분석하여 정성적 리스크(부정적 공시, 소송 등) 감지 시 매수 차단 (`src/llm_analyst.py`)
-- [x] **Consensus 로직**: 정량 모델(앙상블) + 정성 모델(LLM) 합의 시에만 최종 매수 결정하도록 통합 완료
+### 멀티 계정·토큰 균형 (운영 의도)
 
----
+Cursor / AGY / Codex를 **서로 다른 구독·계정**으로 쓰는 경우, 작업을 고르게 나누는 것이 맞습니다.
 
-## Phase 12 — 딥러닝 및 강화학습 ✅ Complete
+| 계정 | 패스당 역할 | 토큰을 쓰는 타이밍 |
+|------|-------------|-------------------|
+| **Cursor** | `src/` 구현·통합·설정·리뷰 반영 | 기능 개발 턴 |
+| **AGY** | `[AGY]` pytest·fixture·harness만 | Cursor 커밋 직후 **별도 AGY 세션** |
+| **Codex** | scoped 리뷰·`NEXT_TODO` | `run_pass_complete.sh` 1~2회/패스 |
 
-- [x] **시계열 Transformer 인프라**: PyTorch 기반의 `SimpleTimeSeriesTransformer` 아키텍처 설계 및 구현 (`src/deep_model.py`)
-- [x] **강화학습(RL) 포트폴리오 엔진**: Stable-Baselines3(PPO)를 활용한 동적 비중 조절 환경 및 에이전트 구축 (`src/rl_portfolio.py`)
-- [x] **라이브러리 환경 구축**: `torch`, `stable-baselines3`, `gymnasium` 설치 및 연동 확인 완료
+**균형 목표 (주간, `agent_workload_report.py`):** 구현 라인 ~**55–65% Cursor**, 테스트 라인 ~**20–30% AGY**, 리뷰 ~**15–20% Codex** (Codex는 커밋 수보다 **호출 횟수**로 보면 됨).
 
----
+**AGY 세션 생략 가능:** `main.py`/주문 경로 변경 없음, 테스트 추가 ≤2파일, harness만 — 단, **이번 주 AGY 비중이 목표보다 10%p 이상 낮으면** 다음 `[AGY]` 항목은 AGY 세션으로 처리.
 
-## Project Roadmap Finalized (2026-05-27)
-- [x] Phase 0-12 전 과정 고도화 및 검증 완료
-- [x] AI 기반 지능형 퀀트 시스템 구축 (Quantitative + Qualitative Hybrid)
-- [x] 강세장 ULTRA_AGGRESSIVE 모드로 최고 수익률 세팅 탑재 완료
+**중복 금지:** 같은 테스트를 Cursor·AGY **둘 다** 작성하지 않음 (한 패스 = 한 구현 계정 + 한 테스트 계정).
 
----
+**패스 마감 (필수):** Cursor 구현 → **AGY 테스트** → `bash scripts/run_pass_complete.sh` → **`NEXT_TODO.codex.md` 확인** → Cursor 수정.
 
-## Phase 13 — 다이내믹 유니버스 & 레버리지 ✅ Complete
+**작업량 집계:** `PYTHONPATH=. .venv/bin/python scripts/agent_workload_report.py --record`  
+커밋 메시지에 `[cursor]` / `[agy]` / `[codex]` 태그 → `logs/agent_workload_history.csv`에 스냅샷 누적.
 
-- [x] **다이내믹 유니버스 (Dynamic Universe)**: 매일 실시간 인기 종목(Most Active) 50개를 자동 수집하여 분석 대상 확대 (총 160+ 종목)
-- [x] **레버리지 가동**: 구매력(Buying Power) 증폭 로직 구현 완료
-- [x] **추가 매수(Pyramiding) 허용**: 보유 종목이라도 비중이 낮으면 목표치까지 추가 매수하도록 개선
+```bash
+RUN_ID=phase20_a bash scripts/run_cursor_post_workflow.sh
+.venv/bin/python scripts/agent_orchestrator.py --run-id phase20_a --run-codex-review --scoped-review
+```
 
 ---
 
-## Phase 14 — 수익 보존 및 정밀 엑싯 ✅ Complete
-
-### 14-A: 지능형 트레일링 스탑 (Trailing Stop)
-- [x] 주가 상승에 따라 손절 라인을 자동으로 올리는 로직 구현 (`src/main.py`, `src/backtester.py`)
-- [x] 최고점 대비 X% 하락 시 익절하여 '줬다 뺏기는' 상황 방지
+## Current Status (2026-05-30)
 
-### 14-B: 다이내믹 포지션 리밸런싱
-- [x] 목표 비중 대비 과대 보유 포지션 자동 Trim 로직 구현 (`src/main.py`)
-- [x] 추가 매수 허용 로직과 연계한 목표 비중 복원 기반 리밸런싱 1차 적용 (`src/risk_manager.py`)
+- **Tickers:** 110 (`config/strategy_config.json`) + dynamic universe
+- **Models:** Regime-aware LGBM+XGB ensemble; last retrain `logs/retrain_history.csv` (ROC-AUC ~0.51)
+- **Walk-forward (5-fold):** ROC-AUC 0.45–0.55 — fold 간 편차 큼 (`logs/ml/ai_model_metrics.csv`)
+- **Portfolio backtest (recent):** total return **+50.7%**, benchmark **+58.2%**, max DD **-10.2%**, 42 trades (`logs/portfolio_backtest/`)
+- **Not in live path:** `deep_model.py`, `rl_portfolio.py` (Phase 12 infra only)
 
----
-
-## Phase 15 — 시장 섹터 및 테마 분석 ✅ Complete
-
-### 15-A: 섹터 순환매 (Sector Rotation) 감지
-- [x] 11개 주요 ETF(XLK, XLF 등)의 모멘텀을 비교하여 주도 섹터 파악 (`src/sector_rotation.py`)
-- [x] 주도 섹터 종목에 AI 점수 가산점 부여 (`src/main.py`, `src/sector_rotation.py`)
+**Completed roadmap:** Phase 0–23 → [`docs/TODO_ARCHIVE.md`](docs/TODO_ARCHIVE.md)  
+**Last pass:** `phase23_pass` (Codex scoped review, 2026-05-30)
 
 ---
 
-## Phase 16 — Execution Resilience & 운영 안정성 ✅ Complete
+## Phase 20 — Portfolio validation & 벤치마크 정합성
 
-### 16-A: 주문 실행 복원력
-- [x] 재시도/타임아웃 상황에서 중복 주문을 막는 idempotency key 또는 run-level dedupe 도입
-- [x] Alpaca 주문 제출, 체결 조회, 부분청산, trim 매도 경로별 공통 예외 처리/재시도 정책 정리
-- [x] 장중 네트워크 오류 시 `dry-run` 전환이 아니라 "실행 중단 + 경고"로 fail-safe 동작 통일
-
-### 16-B: 상태 파일 및 데이터 무결성
-- [x] `data/trailing_peaks.json` 읽기/쓰기 atomic 처리 및 손상 파일 복구 로직 추가
-- [x] 매매 전 가격 데이터 최신 시각 검증 추가: stale/incomplete bar 감지 시 해당 티커 스킵
-- [x] Dynamic Universe / candidate cache 산출물에 대해 "생성 시각, 소스, 누락 티커 수" 메타데이터 강제 기록
-
-### 16-C: 실거래 감사 추적성
-- [x] 주문 사유(reason), 적용 프로필, 레짐, AI score, LLM verdict를 한 row에서 추적 가능한 실행 audit 로그 정규화
-- [x] partial exit / rebalance trim / full exit 를 동일한 이벤트 스키마로 로깅
-- [x] 일별 실행 요약에 "실주문 수, 스킵 사유 집계, 데이터 오류 수, API 오류 수" 추가
+- [x] `[Cursor]` post-workflow/CI 훅에서 `portfolio_summary.csv` 임계값(벤치마크 대비, max DD) 체크 연동
+- [x] `[AGY]` `tests/test_portfolio_backtest_gate.py` — `prompts/agy/phase20_portfolio_gate.md`
+- [x] `[Cursor]` retrain 후 **포트폴리오 수준** 승격 기준을 AUC 단독이 아닌 OOS P&L·Sharpe와 연동
+- [x] `[Cursor]` `report_performance.py` paper vs signal 슬리피지 주간 자동화(스크립트 또는 timer)
+- [x] `[AGY]` portfolio backtest golden test: fixture equity/trades vs `logs/portfolio_backtest/` 스키마·핵심 메트릭 회귀
 
 ---
 
-## Phase 17 — Model Governance & 신호 품질 관리 (중기) ✅ Complete
-
-### 17-A: 모델 승격/강등 체계
-- [x] 레짐별 모델 파일에 학습 기간, 피처 셋 버전, OOS 성능, 승격 시각 메타데이터 저장
-- [x] 신규 모델 학습 후 자동 교체 대신 "챌린저 vs 챔피언" 비교 리포트 기반 승격 절차 추가
-- [x] 최근 실거래/paper 성과가 기준 이하일 때 이전 안정 모델로 롤백하는 안전장치 도입
-
-### 17-B: 드리프트 및 보정
-- [x] 피처 분포 드리프트 감지(예: volatility, volume, macro feature) 및 알림
-- [x] AI score calibration 점검: 확률 예측의 calibration curve / Brier score 리포트 자동화
-- [x] 레짐별 buy/exit threshold를 고정값이 아니라 rolling OOS 기반으로 재튜닝하는 배치 추가
-
-### 17-C: 정성 신호 통제
-- [x] LLM consensus 결과 캐시 및 재사용 정책 추가로 동일 티커 중복 호출 비용 절감
-- [x] 뉴스/LLM 실패 시 무조건 통과 또는 무조건 차단이 아니라 명시적 degraded mode 정책 정의
-- [x] 부정 이벤트 분류 사유를 구조화하여 "소송/실적경고/가이던스하향" 등 카테고리별 분석 가능하게 개선
+## Phase 21 — 신호·모델 품질 (fold 안정화)
 
+- [x] `[Cursor]` Walk-forward fold별 ROC-AUC 편차 분석 및 calibration 리포트 **생성 경로** 구현
+- [x] `[AGY]` calibration/Brier 리포트 출력에 대한 pytest + fold별 메트릭 CSV 스키마 회귀 테스트
+- [x] `[Cursor]` 챔피언 승격: `train_ai_model` 메트릭 + 포트폴리오 백테스트 **둘 다** 통과해야 교체
+- [x] `[AGY]` 승격/롤백 decision path mock 테스트 (챌린저 거절·롤백 시나리오)
+- [x] `[Cursor]` Transformer / RL research-only — `docs/RESEARCH_MODELS.md`
 
 ---
 
-## Phase 18 — Portfolio Risk Engine 고도화 (중기) ✅ Complete
-
-### 18-A: 포트폴리오 수준 익스포저 통제
-- [x] leverage 사용 시 gross exposure, cash buffer, single-name max loss 기준을 함께 검증하는 포트폴리오 가드 추가
-- [x] 섹터 한도 외에 factor/momentum crowding 기반 concentration guard 도입 검토
-- [x] 상관관계 가드를 단순 pairwise 기준에서 포트폴리오 전체 평균 상관/클러스터 기준으로 확장 (`src/correlation_guard.py`)
+## Phase 22 — 운영 관측 & 실행 품질
 
-### 18-B: 이벤트 리스크 캘린더
-- [x] Earnings 외에 FOMC, CPI, PPI, NFP 같은 매크로 이벤트 캘린더 반영 (`src/macro_events.py`)
-- [x] 고변동 이벤트 전후 신규 진입 제한 또는 목표 비중 축소 규칙 추가 (`src/main.py`)
-- [x] 이벤트 결과 이후 regime/profile 재평가 배치를 별도 분리 (`src/reappraise_regime.py`)
-
-### 18-C: Exit 정책 정밀화
-- [x] trailing stop, AI exit, partial take-profit, rebalance trim 간 우선순위/충돌 규칙 명시화
-- [x] 종목별 ATR 또는 realized volatility 기반 adaptive trailing stop 검토 (`src/strategy.py`, `src/main.py`)
-- [x] 시간 기반 exit(보유 기간 초과, 신호 약화 지속) 규칙 추가 검토 (`src/main.py`, `src/alpaca_client.py`)
+- [x] `[Cursor]` 일별 audit 요약(스킵 사유, API 오류, stale bar) 집계 — `src/daily_audit_summary.py`, `scripts/run_daily_audit_summary.sh`
+- [x] `[AGY]` audit 집계 출력·스키마 — `tests/test_daily_audit_summary_schema.py`, `tests/fixtures/audit_daily/`
+- [x] `[Cursor]` Retrain 실패·부분 성공 Telegram/runbook — `run_retrain_cli`, `docs/runbook.md` §2.2
+- [x] `[AGY]` macro/earnings 스킵 비율 — `context_skip_*` in `daily_audit_summary` + golden fixture
 
 ---
 
-## Phase 19 — 테스트/문서/설정 정합성 정리 ✅ Complete
-
-### 19-A: 테스트 보강
-- [x] `src/main.py` 실주문 흐름을 mock broker/mock LLM/mock news 기준으로 end-to-end 테스트 추가 (`tests/test_main_e2e.py`)
-- [x] partial exit / trim / trailing stop / earnings filter 동시 발생 케이스 회귀 테스트 추가
-- [x] 장애 테스트 추가: 손상된 JSON 상태파일, 빈 데이터프레임, Alpaca timeout, LLM timeout
-
-### 19-B: 설정 스키마 정리
-- [x] `src/settings.py` 중복 필드(`trailing_stop_pct`) 및 레거시/신규 설정 혼재 정리
-- [x] `strategy_config.json` / `strategy_profiles.json` 에 대한 schema validation 추가
-- [x] 미사용 설정값 및 문서와 어긋난 기본값 정리
+## Phase 23 — 전략·리스크 리포트
 
-### 19-C: 문서 최신화
-- [x] `README.md`를 현재 아키텍처 기준으로 업데이트: Regime-aware, ensemble, LLM consensus, dynamic universe 반영
-- [x] 운영 runbook 추가: retrain 실패, API 장애, drawdown breach, stale data 대응 절차 (`docs/runbook.md`)
-- [x] TODO.md 완료 기준을 "코드 존재"가 아니라 "테스트/리포트/운영 검증 완료" 기준으로 재정의
+- [x] `[Cursor]` Factor/crowding guard 백테스트 영향도 — `src/guard_impact_report.py`, backtester `crowding_guard_enabled`
+- [x] `[Cursor]` Leverage stress (gap down, correlation spike) — `src/leverage_stress_report.py`
+- [x] `[AGY]` LLM cache hit rate 모니터링 — `src/llm_cache_report.py`, `tests/test_llm_cache_report_schema.py`
diff --git a/config/slippage_report_config.json b/config/slippage_report_config.json
new file mode 100644
index 0000000..4634d1e
--- /dev/null
+++ b/config/slippage_report_config.json
@@ -0,0 +1,7 @@
+{
+  "timezone": "America/New_York",
+  "on_calendar_times": ["Sun 18:00:00"],
+  "lookback_days": 7,
+  "output_dir": "logs/slippage_reports",
+  "notify_telegram": true
+}
diff --git a/docs/RESEARCH_MODELS.md b/docs/RESEARCH_MODELS.md
new file mode 100644
index 0000000..3161f78
--- /dev/null
+++ b/docs/RESEARCH_MODELS.md
@@ -0,0 +1,10 @@
+# Research-only models (not live)
+
+`src/deep_model.py` (Transformer/GRU) and `src/rl_portfolio.py` (PPO) are **experimental infrastructure only**.
+
+| Module | Status | Live path |
+|--------|--------|-----------|
+| `deep_model.py` | PyTorch prototype | **Not imported** by `main.py`, `train_ai_model.py`, or promotion |
+| `rl_portfolio.py` | Gymnasium/PPO prototype | **Not imported** by production entrypoints |
+
+Production signals use regime-aware **LightGBM + XGBoost** (`src/ml_model.py`). Do not enable deep/RL modules in `config/strategy_config.json` until a dedicated promotion path exists.
diff --git a/docs/TODO_ARCHIVE.md b/docs/TODO_ARCHIVE.md
new file mode 100644
index 0000000..cfd048c
--- /dev/null
+++ b/docs/TODO_ARCHIVE.md
@@ -0,0 +1,29 @@
+# TODO Archive (Phase 0–19)
+
+완료된 로드맵 요약. 상세 체크리스트는 git history의 `TODO.md` (2026-05-27 이전) 참고.
+
+| Phase | Theme | Key deliverables |
+|-------|--------|------------------|
+| 0–6 | Foundation | Core bot, data, backtest, AI baseline |
+| 7 | Live monitoring | `report_performance.py`, correlation guard, circuit breaker, Telegram alerts |
+| 8 | Regime-aware | `market_regime.py`, regime models, walk-forward validation |
+| 9 | Signal quality | LGBM+XGB ensemble, earnings filter, SKEW/VVIX features |
+| 10 | Dynamic profiles | `strategy_profiles.json`, ULTRA_AGGRESSIVE |
+| 11 | Execution intelligence | Partial profit-taking, LLM consensus (`llm_analyst.py`) |
+| 12 | DL / RL infra | `deep_model.py`, `rl_portfolio.py` (not live-integrated) |
+| 13 | Universe & leverage | Dynamic universe, buying power, pyramiding |
+| 14 | Exit precision | Trailing stop, rebalance trim |
+| 15 | Sector rotation | `sector_rotation.py` |
+| 16 | Execution resilience | Idempotency, atomic state files, audit logging |
+| 17 | Model governance | Champion/challenger, drift, LLM cache/degraded mode |
+| 18 | Portfolio risk | Exposure guards, macro events, exit priority rules |
+| 19 | Tests & docs | E2E tests, schema validation, `docs/runbook.md` |
+
+**Milestone (2026-05-27):** Phase 0–19 closed per Definition of Done (code + pytest + runbook).
+
+| Phase | Theme | Key deliverables |
+|-------|--------|------------------|
+| 20 | Portfolio validation | Promotion gates (OOS P&L/Sharpe), weekly slippage report, portfolio pytest gates |
+| 21 | Model quality | ML quality/calibration reports, dual promotion gates, rollback mocks |
+| 22 | Ops observability | Daily audit summary, retrain Telegram paths, macro/earnings skip rates |
+| 23 | Risk reports | Crowding guard backtest impact, leverage stress scenarios, LLM cache monitoring |
diff --git a/docs/agent_review_harness.md b/docs/agent_review_harness.md
index 6892dea..5a93af8 100644
--- a/docs/agent_review_harness.md
+++ b/docs/agent_review_harness.md
@@ -2,7 +2,7 @@
 
 This harness defines how **Codex** (and optionally **AGY**) review, validate, and plan follow-up work after an implementation agent has changed this repository. It is not the trading runtime harness and it is not a "Codex implements everything" workflow.
 
-**Default flow:** Cursor implements in the IDE → post-workflow collects artifacts → Codex reviews read-only → optional AGY for architecture/risk.
+**Default flow:** Cursor implements → **AGY adds `[AGY]` tests** → post-workflow → Codex reviews read-only → optional AGY for architecture/risk on large strategy diffs.
 
 ## Roles
 
@@ -24,8 +24,8 @@ Only one implementation agent may edit the working tree at a time.
 Default:
 - **Cursor** edits.
 - **Codex** reviews in read-only mode.
-- **AGY** reviews in read-only or plan-only mode.
-- **Gemini CLI** (`--run-gemini`) is optional legacy headless implementer.
+- **AGY** implements **`[AGY]` test/harness slices** when invoked; otherwise read-only/plan-only for strategy/risk.
+- **Gemini CLI** (`--run-gemini`) is legacy, **docs/low-risk only** — not for tests (weaker default model than AGY).
 
 Codex or AGY may implement fixes only when explicitly asked, and preferably on a separate branch.
 Never let multiple agents edit the same branch concurrently.
@@ -85,12 +85,14 @@ It collects:
 
 The intended loop is:
 
-1. **Cursor** implements the change in the IDE (WSL remote or local).
-2. `scripts/run_cursor_post_workflow.sh` runs review/runtime checks and creates a packet.
-3. The user asks **Codex** to review `review_packet.md`.
-4. Codex leads with findings and produces `NEXT_TODO.codex.md` or rewrites `NEXT_TODO.md`.
-5. **Cursor** (or optional **Gemini CLI** for `[Gemini]`-labeled slices) works the next queue.
-6. Repeat after the next implementation pass.
+1. **Cursor** implements the change in the IDE (production paths).
+2. **AGY** implements `[AGY]` pytest/harness work (sequential; one implementer at a time).
+3. **`bash scripts/run_pass_complete.sh`** (required): pytest → post-workflow packet → **Codex** scoped review.
+4. Read **`NEXT_TODO.codex.md`** — confirm no blocking findings; implement follow-ups in Cursor.
+5. Repeat. Do **not** mark TODO `[x]` or start the next feature until step 3–4 succeed.
+6. Use **Gemini CLI** only for explicit `[Gemini]` docs/mechanical tasks if AGY is unavailable.
+
+Shortcut for packet-only (no Codex): `run_cursor_post_workflow.sh` — not sufficient for Definition of Done.
 
 This repository does not automatically invoke Cursor from the orchestrator. Cursor is IDE-driven; the pipeline only collects diffs and runs checks.
 
@@ -190,7 +192,7 @@ The orchestrator stops the loop automatically if:
 
 ## Optional AGY Review
 
-After Codex review, invoke AGY when strategy, risk, or architecture changed materially. AGY reads the same `review_packet.md` and follows `AGY.md`. AGY does not replace Codex for test verification or `NEXT_TODO` drafting unless you prefer that split.
+After Codex review, invoke AGY for **strategy/risk/architecture** when diffs are material. For **test gaps**, assign a follow-up `[AGY]` slice instead of Gemini CLI. AGY does not replace Codex for `NEXT_TODO` drafting.
 
 ## Review Output
 
@@ -200,7 +202,7 @@ A good Codex review should include:
 - tests run and actual results;
 - tests not run and why;
 - whether the implementer's claims were verified;
-- a short next-step plan with stop conditions and `[Cursor]` / `[Gemini]` labels where helpful;
+- a short next-step plan with stop conditions and `[Cursor]` / `[AGY]` labels where helpful;
 - residual risk.
 
 ## Guardrails
diff --git a/docs/gemini_codex_harness.md b/docs/gemini_codex_harness.md
index 71e61f9..9f71657 100644
--- a/docs/gemini_codex_harness.md
+++ b/docs/gemini_codex_harness.md
@@ -2,4 +2,4 @@
 
 This document was renamed to **[agent_review_harness.md](agent_review_harness.md)**.
 
-The repository uses a **Cursor-first** workflow: Cursor implements in the IDE, Codex reviews read-only, AGY is optional for architecture/risk, and Gemini CLI remains an optional legacy headless implementer (`--run-gemini`).
+The repository uses a **Cursor-first** workflow: Cursor implements, **AGY owns `[AGY]` tests/harness**, Codex reviews read-only, AGY optionally reviews architecture/risk, and Gemini CLI is legacy docs-only (`--run-gemini`, not for tests).
diff --git a/docs/runbook.md b/docs/runbook.md
index 8b1d1a1..fe8fc43 100644
--- a/docs/runbook.md
+++ b/docs/runbook.md
@@ -30,12 +30,17 @@
     2. 네트워크 상태 확인 후 수동으로 `src/main.py`를 실행하여 정상 동작 확인.
     3. LLM 할당량 초과 시 `config/strategy_config.json`에서 `llm_degraded_mode`를 `"PASS"`로 설정하여 정량 모델만으로 운용 가능.
 
-### 2.2 Retrain 실패 (Stale Model)
-- **현상**: 매일 아침 06:00 ET에 실행되는 학습 타이머 실패 알림.
+### 2.2 Retrain 실패·부분 성공 (Stale Model)
+- **현상**: 매일 아침 06:00 ET retrain 타이머 실패, 또는 학습은 됐으나 챔피언 유지.
+- **Telegram 알림** (`src/train_ai_model.py`):
+    - **실패**: `AI Retrain Failed` — `logs/retrain_history.csv`에 `status=failure` 기록.
+    - **부분 성공**(학습·리포트 완료, 승격 없음): `Retrain finished; champion retained` — `logs/ml/model_promotion_report.json`의 `decision`이 `RETAIN_CHAMPION`.
+    - **품질 경고**(학습 성공 중): feature drift, calibration(Brier), fold ROC 분산 — 각각 별도 `notify_info`.
+    - **성능 저하**: 평균 ROC-AUC < 0.51이면 `AI Model Performance Degradation`.
 - **대응**:
-    1. `logs/retrain_history.csv`에서 에러 로그 확인.
+    1. `logs/retrain_runs/retrain_*.log` 및 `logs/retrain_history.csv` 확인.
     2. 데이터 소스(yfinance) 차단 여부 확인.
-    3. 모델 파일(`models/ai_score_model.joblib`)이 존재하면 봇은 기존 모델로 계속 동작함. 수동으로 `scripts/run_retrain.sh` 실행 시도.
+    3. `models/ai_score_model.joblib`은 **로컬 전용**(git 미추적). `model_promotion_report.json`에서 `decision=PROMOTE`일 때만 챔피언 파일을 교체하고, ROC-AUC < 0.51이면 커밋·배포하지 않음. 수동: `bash scripts/run_retrain.sh`.
 
 ### 2.3 Drawdown Circuit Breaker 발동
 - **현상**: 포트폴리오 자산이 최고점 대비 15% 이상 하락하여 "New buys blocked" 알림 발생.
@@ -55,8 +60,24 @@
 ## 📈 3. 주기적 점검 사항 (Maintenance)
 
 - **일간**: Telegram 요약 리포트를 통해 실주문 수 및 스킵 사유 집계 확인.
-- **주간**: `PYTHONPATH=. .venv/bin/python src/report_performance.py` 실행하여 실거래 vs 백테스트 괴리율(슬리피지) 점검.
+  ```bash
+  bash scripts/run_daily_audit_summary.sh
+  # 특정일: bash scripts/run_daily_audit_summary.sh --date 2026-05-30
+  ```
+  산출물: `logs/audit_daily/latest_summary.json`, `audit_YYYYMMDD.json` (`logs/execution_audit.csv` 기준)
+- **주간**: paper 체결 vs 시그널 슬리피지 자동 리포트
+  ```bash
+  bash scripts/run_weekly_slippage_report.sh
+  # 또는: PYTHONPATH=. .venv/bin/python -m src.report_performance --weekly
+  ```
+  산출물: `logs/slippage_reports/latest_summary.json` (타이머 설치: `bash scripts/install_slippage_report_timer.sh`)
 - **월간**: `data/llm_cache.json` 및 오래된 로그 파일 정리 (용량 관리).
+- **리스크 리포트 (수동/주간)**:
+  ```bash
+  bash scripts/run_guard_impact_report.sh      # logs/guard_impact/latest_summary.json
+  bash scripts/run_leverage_stress_report.sh   # logs/leverage_stress/latest_summary.json
+  bash scripts/run_llm_cache_report.sh         # logs/llm_monitoring/latest_summary.json
+  ```
 
 ---
 
diff --git a/models/.gitkeep b/models/.gitkeep
new file mode 100644
index 0000000..e69de29
diff --git a/models/ai_score_model.joblib b/models/ai_score_model.joblib
deleted file mode 100644
index 4cc580d..0000000
Binary files a/models/ai_score_model.joblib and /dev/null differ
diff --git a/prompts/agy/README.md b/prompts/agy/README.md
new file mode 100644
index 0000000..1143815
--- /dev/null
+++ b/prompts/agy/README.md
@@ -0,0 +1,13 @@
+# AGY session prompts
+
+Copy a task file into Antigravity/AGY after **Cursor** commits `[cursor]` implementation.
+
+**Do not** implement `src/main.py` or order paths in AGY. Commit results with `[agy]` tag.
+
+After AGY pytest is green:
+
+```bash
+RUN_ID=<same_pass_id> bash scripts/run_pass_complete.sh
+```
+
+Then read `reports/agent_pipeline/<run_id>/NEXT_TODO.codex.md` in Cursor.
diff --git a/prompts/agy/phase20_portfolio_gate.md b/prompts/agy/phase20_portfolio_gate.md
new file mode 100644
index 0000000..76f42ba
--- /dev/null
+++ b/prompts/agy/phase20_portfolio_gate.md
@@ -0,0 +1,35 @@
+# [AGY] Phase 20 — portfolio backtest gate tests
+
+## Context
+
+Cursor added (do not modify unless tests require it):
+
+- `src/portfolio_backtest_validation.py` — `check_portfolio_backtest_thresholds`, `PortfolioBacktestThresholds`
+- `scripts/check_portfolio_backtest_gate.py` — CLI used in post-workflow
+- Post-workflow calls gate when `logs/portfolio_backtest/` exists
+
+## Your scope (tests only)
+
+1. Add `tests/test_portfolio_backtest_gate.py`:
+   - pass: summary fixture with acceptable DD and benchmark gap
+   - fail: max_drawdown worse than floor
+   - fail: return vs benchmark below min gap
+   - CLI: `check_portfolio_backtest_gate.py` exit 0/1 with tmp dir fixtures
+
+2. Do **not** change production logic in `src/main.py` or trading paths.
+
+## Verify
+
+```bash
+PYTHONPATH=. .venv/bin/python -m pytest tests/test_portfolio_backtest_gate.py -q
+```
+
+## After tests exist
+
+Orchestrator (Cursor terminal):
+
+```bash
+RUN_ID=phase20_portfolio_gate bash scripts/run_balanced_pass.sh
+```
+
+Commit message must include `[agy]`.
diff --git a/prompts/agy/phase21_ml_quality.md b/prompts/agy/phase21_ml_quality.md
new file mode 100644
index 0000000..d0174be
--- /dev/null
+++ b/prompts/agy/phase21_ml_quality.md
@@ -0,0 +1,11 @@
+# [AGY] Phase 21 — ML quality report schema regression
+
+## Scope
+- `tests/test_ml_quality_report_schema.py`
+- Fixtures under `tests/fixtures/ml_quality/` (generated by tests)
+- Validates `fold_metrics.csv`, `fold_stability_report.json`, calibration JSON/bins
+
+## Run
+```bash
+PYTHONPATH=. .venv/bin/python -m pytest tests/test_ml_quality_report_schema.py tests/test_ml_quality_report.py -q
+```
diff --git a/prompts/agy/phase21_promotion_rollback.md b/prompts/agy/phase21_promotion_rollback.md
new file mode 100644
index 0000000..becd820
--- /dev/null
+++ b/prompts/agy/phase21_promotion_rollback.md
@@ -0,0 +1,14 @@
+# [AGY] Phase 21 — Promotion reject & rollback path mocks
+
+## Scope
+- `tests/test_promotion_rollback_path.py`
+- `resolve_rollback_decision()` in `src/train_ai_model.py`
+
+## Scenarios
+- Challenger rejected: weak AUC, portfolio gate fail, high fold variance
+- Rollback: skip after PROMOTE, NO_ROLLBACK_NEEDED, ROLLBACK_TO_ARCHIVED_CHAMPION, NO_ROLLBACK_AVAILABLE
+
+## Run
+```bash
+PYTHONPATH=. .venv/bin/python -m pytest tests/test_model_governance_rollback.py tests/test_promotion_rollback_path.py -q
+```
diff --git a/scripts/agent_orchestrator.py b/scripts/agent_orchestrator.py
index 221eb0c..05b51d8 100755
--- a/scripts/agent_orchestrator.py
+++ b/scripts/agent_orchestrator.py
@@ -85,6 +85,27 @@ def parse_args() -> argparse.Namespace:
         default=240,
         help="Timeout for the Codex review step.",
     )
+    parser.add_argument(
+        "--ignore-artifacts",
+        action="store_true",
+        help="Allow Codex review when models/logs are in the diff (pass closure).",
+    )
+    parser.add_argument(
+        "--balanced-pass",
+        action="store_true",
+        help="Run AGY pytest slice, then post-workflow + Codex scoped review.",
+    )
+    parser.add_argument(
+        "--agy-prompt",
+        type=Path,
+        default=Path("prompts/agy/phase20_portfolio_gate.md"),
+        help="AGY task file copied into the run directory (with --balanced-pass).",
+    )
+    parser.add_argument(
+        "--agy-test-paths",
+        default="tests/test_portfolio_backtest_gate.py",
+        help="Comma-separated pytest paths for the AGY slice.",
+    )
     parser.add_argument(
         "--dry-run",
         action="store_true",
@@ -188,7 +209,11 @@ def write_json(path: Path, data: dict) -> None:
 
 
 def check_stop_conditions(
-    out_dir: Path, max_changed_files: int, history: list[dict]
+    out_dir: Path,
+    max_changed_files: int,
+    history: list[dict],
+    *,
+    ignore_artifacts: bool = False,
 ) -> str | None:
     changed_files_path = out_dir / "changed_files.txt"
     if changed_files_path.exists():
@@ -201,7 +226,7 @@ def check_stop_conditions(
             for f in changed_files
             if any(p in f for p in ["models/", "logs/", "reports/", ".pytest_cache/"])
         ]
-        if artifacts:
+        if artifacts and not ignore_artifacts:
             return f"Generated artifacts detected in diff (excluded from review loop): {artifacts}"
 
         sensitive = [
@@ -259,6 +284,30 @@ def main() -> int:
         print("Refusing Gemini yolo mode in this orchestrator.", file=sys.stderr)
         return 2
 
+    if args.balanced_pass:
+        args.run_codex_review = True
+        args.ignore_artifacts = True
+        pre_dir = REPORT_ROOT / (args.run_id or dt.datetime.now().strftime("%Y%m%dT%H%M%S"))
+        pre_dir.mkdir(parents=True, exist_ok=True)
+        if args.agy_prompt.is_file():
+            (pre_dir / "AGY_TASK.md").write_text(
+                args.agy_prompt.read_text(encoding="utf-8"), encoding="utf-8"
+            )
+        agy_env = os.environ.copy()
+        agy_env["AGY_PROMPT"] = str(args.agy_prompt)
+        agy_env["AGY_TEST_PATHS"] = args.agy_test_paths.replace(",", " ")
+        print("--- Balanced pass: AGY pytest slice ---")
+        agy_code = run_command(
+            ["bash", "scripts/run_agy_slice.sh"],
+            log_path=pre_dir / "agy_slice.log",
+            env=agy_env,
+            dry_run=args.dry_run,
+        )
+        if agy_code != 0:
+            print(f"AGY slice failed with exit code {agy_code}", file=sys.stderr)
+            return agy_code
+        os.environ.setdefault("IMPLEMENTATION_AGENT", "cursor+agy")
+
     history: list[dict] = []
     
     for i in range(args.max_iterations):
@@ -303,7 +352,12 @@ def main() -> int:
         )
 
         # Check stop conditions after Gemini + Post-workflow
-        stop_reason = check_stop_conditions(out_dir, args.max_changed_files, history)
+        stop_reason = check_stop_conditions(
+            out_dir,
+            args.max_changed_files,
+            history,
+            ignore_artifacts=args.ignore_artifacts,
+        )
         if stop_reason:
             print(f"STOP CONDITION: {stop_reason}")
             break
diff --git a/scripts/agent_workload_report.py b/scripts/agent_workload_report.py
new file mode 100644
index 0000000..4170219
--- /dev/null
+++ b/scripts/agent_workload_report.py
@@ -0,0 +1,247 @@
+#!/usr/bin/env python3
+"""Summarize planned vs actual agent workload for token balancing."""
+
+from __future__ import annotations
+
+import argparse
+import csv
+import json
+import re
+import subprocess
+from collections import defaultdict
+from datetime import datetime, timezone
+from pathlib import Path
+
+ROOT = Path(__file__).resolve().parents[1]
+TODO_PATH = ROOT / "TODO.md"
+REPORT_ROOT = ROOT / "reports" / "agent_pipeline"
+HISTORY_PATH = ROOT / "logs" / "agent_workload_history.csv"
+
+AGENT_TAGS = ("cursor", "agy", "codex", "gemini", "manual")
+TAG_RE = re.compile(r"\[(cursor|agy|codex|gemini)\]", re.IGNORECASE)
+TODO_LABEL_RE = re.compile(r"`\[(Cursor|AGY|Gemini|Either)\]`", re.IGNORECASE)
+OPEN_ITEM_RE = re.compile(r"^- \[([ xX])\]\s+(.*)$")
+
+
+def _git(*args: str) -> str:
+    return subprocess.check_output(
+        ["git", "-C", str(ROOT), *args],
+        text=True,
+        stderr=subprocess.DEVNULL,
+    ).strip()
+
+
+def parse_todo(path: Path) -> dict[str, dict[str, int]]:
+    counts: dict[str, dict[str, int]] = {
+        agent: {"open": 0, "done": 0} for agent in ("cursor", "agy", "gemini", "either", "unlabeled")
+    }
+    if not path.is_file():
+        return counts
+
+    for line in path.read_text().splitlines():
+        m = OPEN_ITEM_RE.match(line)
+        if not m:
+            continue
+        done = m.group(1).lower() == "x"
+        body = m.group(2)
+        label_m = TODO_LABEL_RE.search(body)
+        if label_m:
+            agent = label_m.group(1).lower()
+        elif "[agy]" in body.lower() and "검토" in body:
+            agent = "agy"
+        else:
+            agent = "unlabeled"
+        key = "done" if done else "open"
+        counts[agent][key] += 1
+    return counts
+
+
+def git_commit_stats(since: str | None) -> dict[str, dict[str, float]]:
+    commit_sep = "@@@COMMIT@@@"
+    args = ["log", "--numstat", f"--format={commit_sep}%n%H%x00%s", "--no-merges"]
+    if since:
+        args.append(f"--since={since}")
+    try:
+        raw = _git(*args)
+    except subprocess.CalledProcessError:
+        return {a: {"commits": 0, "files": 0, "lines_added": 0, "lines_deleted": 0} for a in AGENT_TAGS}
+
+    stats: dict[str, dict[str, float]] = defaultdict(
+        lambda: {"commits": 0, "files": 0, "lines_added": 0, "lines_deleted": 0}
+    )
+    unlabeled = {"commits": 0, "files": 0, "lines_added": 0, "lines_deleted": 0}
+
+    for block in raw.split(commit_sep) if raw else []:
+        lines = [ln for ln in block.splitlines() if ln.strip()]
+        if not lines:
+            continue
+        header = lines[0]
+        if "\x00" not in header:
+            continue
+        _, subject = header.split("\x00", 1)
+        tag_m = TAG_RE.search(subject)
+        agent = tag_m.group(1).lower() if tag_m else None
+
+        added = deleted = files = 0
+        for ln in lines[1:]:
+            parts = ln.split("\t")
+            if len(parts) != 3:
+                continue
+            a, d, _path = parts
+            if a == "-" or d == "-":
+                continue
+            files += 1
+            added += int(a)
+            deleted += int(d)
+
+        bucket = stats[agent] if agent else unlabeled
+        bucket["commits"] += 1
+        bucket["files"] += files
+        bucket["lines_added"] += added
+        bucket["lines_deleted"] += deleted
+
+    stats["unlabeled"] = unlabeled
+    return dict(stats)
+
+
+def pipeline_runs() -> dict[str, int]:
+    counts: dict[str, int] = defaultdict(int)
+    if not REPORT_ROOT.is_dir():
+        return dict(counts)
+    for packet in REPORT_ROOT.glob("*/review_packet.md"):
+        text = packet.read_text(errors="replace")
+        impl = "unknown"
+        for line in text.splitlines():
+            if line.startswith("## Implementation Agent"):
+                continue
+            if impl == "unknown" and line.strip() and not line.startswith("#"):
+                impl = line.strip().lower()
+                break
+        counts[impl] += 1
+    return dict(counts)
+
+
+def pct(part: float, total: float) -> float:
+    return round(100.0 * part / total, 1) if total else 0.0
+
+
+def build_report(since: str | None) -> dict:
+    todo = parse_todo(TODO_PATH)
+    git_stats = git_commit_stats(since)
+    pipeline = pipeline_runs()
+
+    planned_open = sum(todo[a]["open"] for a in todo)
+    planned_by_agent = {
+        a: todo[a]["open"] for a in ("cursor", "agy", "gemini", "either", "unlabeled")
+    }
+
+    agents_all = [*AGENT_TAGS, "unlabeled"]
+    git_commits_total = sum(git_stats.get(a, {}).get("commits", 0) for a in agents_all)
+    git_lines_total = sum(
+        git_stats.get(a, {}).get("lines_added", 0) + git_stats.get(a, {}).get("lines_deleted", 0)
+        for a in agents_all
+    )
+
+    return {
+        "generated_at": datetime.now(timezone.utc).isoformat(),
+        "since": since,
+        "planned_todo_open": planned_by_agent,
+        "planned_todo_open_total": planned_open,
+        "planned_todo_pct": {
+            k: pct(v, planned_open) for k, v in planned_by_agent.items() if planned_open
+        },
+        "todo_done_open": {a: todo[a] for a in todo},
+        "git": git_stats,
+        "git_commit_share_pct": {
+            a: pct(git_stats.get(a, {}).get("commits", 0), git_commits_total) for a in agents_all
+        },
+        "git_line_share_pct": {
+            a: pct(
+                git_stats.get(a, {}).get("lines_added", 0)
+                + git_stats.get(a, {}).get("lines_deleted", 0),
+                git_lines_total,
+            )
+            for a in agents_all
+        },
+        "pipeline_implementation_agent_runs": pipeline,
+    }
+
+
+def print_human(report: dict) -> None:
+    print("=== Agent workload report ===")
+    print(f"Generated: {report['generated_at']}")
+    if report.get("since"):
+        print(f"Git since: {report['since']}")
+
+    print("\n-- Planned (TODO open items) --")
+    for agent, n in sorted(report["planned_todo_open"].items(), key=lambda x: -x[1]):
+        if n:
+            pct_v = report["planned_todo_pct"].get(agent, 0)
+            print(f"  {agent:10} {n:3} items  ({pct_v}%)")
+
+    print("\n-- Actual (git commits by message tag [cursor]/[agy]/...) --")
+    for agent in (*AGENT_TAGS, "unlabeled"):
+        g = report["git"].get(agent, {})
+        if not g.get("commits"):
+            continue
+        print(
+            f"  {agent:10} commits={int(g['commits']):3}  "
+            f"lines+/-={int(g['lines_added'])+int(g['lines_deleted']):5}  "
+            f"({report['git_commit_share_pct'].get(agent, 0)}% commits, "
+            f"{report['git_line_share_pct'].get(agent, 0)}% lines)"
+        )
+
+    if report["pipeline_implementation_agent_runs"]:
+        print("\n-- Pipeline runs (review_packet implementation agent) --")
+        for agent, n in report["pipeline_implementation_agent_runs"].items():
+            print(f"  {agent:10} {n} runs")
+
+    print("\nTip: tag commits e.g. `feat(test): golden backtest [agy]`")
+    print("     re-run: PYTHONPATH=. .venv/bin/python scripts/agent_workload_report.py --record")
+
+
+def append_history(report: dict) -> None:
+    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
+    write_header = not HISTORY_PATH.is_file()
+    row = {
+        "timestamp": report["generated_at"],
+        "since": report.get("since") or "",
+        "todo_open_cursor": report["planned_todo_open"].get("cursor", 0),
+        "todo_open_agy": report["planned_todo_open"].get("agy", 0),
+        "git_commits_cursor": int(report["git"].get("cursor", {}).get("commits", 0)),
+        "git_commits_agy": int(report["git"].get("agy", {}).get("commits", 0)),
+        "git_lines_cursor": int(report["git"].get("cursor", {}).get("lines_added", 0))
+        + int(report["git"].get("cursor", {}).get("lines_deleted", 0)),
+        "git_lines_agy": int(report["git"].get("agy", {}).get("lines_added", 0))
+        + int(report["git"].get("agy", {}).get("lines_deleted", 0)),
+    }
+    with HISTORY_PATH.open("a", newline="") as f:
+        w = csv.DictWriter(f, fieldnames=list(row.keys()))
+        if write_header:
+            w.writeheader()
+        w.writerow(row)
+
+
+def main() -> None:
+    parser = argparse.ArgumentParser(description=__doc__)
+    parser.add_argument("--since", default="2026-05-01", help="Git log start (default: 2026-05-01)")
+    parser.add_argument("--json", action="store_true", help="Print JSON only")
+    parser.add_argument(
+        "--record",
+        action="store_true",
+        help="Append snapshot to logs/agent_workload_history.csv",
+    )
+    args = parser.parse_args()
+
+    report = build_report(args.since)
+    if args.record:
+        append_history(report)
+
+    if args.json:
+        print(json.dumps(report, indent=2))
+    else:
+        print_human(report)
+
+
+if __name__ == "__main__":
+    main()
diff --git a/scripts/check_portfolio_backtest_gate.py b/scripts/check_portfolio_backtest_gate.py
new file mode 100755
index 0000000..7c333eb
--- /dev/null
+++ b/scripts/check_portfolio_backtest_gate.py
@@ -0,0 +1,81 @@
+#!/usr/bin/env python3
+"""CI/post-workflow gate for logs/portfolio_backtest/portfolio_summary.csv."""
+
+from __future__ import annotations
+
+import argparse
+import os
+import sys
+from pathlib import Path
+
+ROOT = Path(__file__).resolve().parents[1]
+if str(ROOT) not in sys.path:
+    sys.path.insert(0, str(ROOT))
+
+from src.portfolio_backtest_validation import (  # noqa: E402
+    PortfolioBacktestThresholds,
+    check_portfolio_backtest_thresholds,
+)
+
+
+def _env_float(name: str, default: float) -> float:
+    raw = os.environ.get(name)
+    return float(raw) if raw is not None else default
+
+
+def main() -> int:
+    parser = argparse.ArgumentParser(description=__doc__)
+    parser.add_argument(
+        "--dir",
+        type=Path,
+        default=Path("logs/portfolio_backtest"),
+        help="Directory with portfolio_* CSV outputs",
+    )
+    parser.add_argument(
+        "--max-drawdown-floor",
+        type=float,
+        default=None,
+        help="Fail if max_drawdown is below this (default: env or -0.20)",
+    )
+    parser.add_argument(
+        "--min-return-vs-benchmark",
+        type=float,
+        default=None,
+        help="Fail if (total_return - benchmark_return) below this (default: -0.15)",
+    )
+    parser.add_argument(
+        "--min-sharpe",
+        type=float,
+        default=None,
+        help="Optional minimum sharpe_ratio",
+    )
+    args = parser.parse_args()
+
+    thresholds = PortfolioBacktestThresholds(
+        max_drawdown_floor=args.max_drawdown_floor
+        if args.max_drawdown_floor is not None
+        else _env_float("PORTFOLIO_MAX_DRAWDOWN_FLOOR", -0.20),
+        min_return_vs_benchmark=args.min_return_vs_benchmark
+        if args.min_return_vs_benchmark is not None
+        else _env_float("PORTFOLIO_MIN_RETURN_VS_BENCHMARK", -0.15),
+        min_sharpe=args.min_sharpe,
+    )
+
+    result = check_portfolio_backtest_thresholds(args.dir, thresholds)
+    summary = result.summary
+    print(
+        f"portfolio gate: total_return={summary['total_return']:.4f} "
+        f"benchmark={summary['benchmark_return']:.4f} "
+        f"max_drawdown={summary['max_drawdown']:.4f} "
+        f"sharpe={summary['sharpe_ratio']:.4f}"
+    )
+    for w in result.warnings:
+        print(f"WARNING: {w}")
+    for f in result.failures:
+        print(f"FAIL: {f}", file=sys.stderr)
+
+    return 0 if result.passed else 1
+
+
+if __name__ == "__main__":
+    raise SystemExit(main())
diff --git a/scripts/install_slippage_report_timer.sh b/scripts/install_slippage_report_timer.sh
new file mode 100755
index 0000000..945ee39
--- /dev/null
+++ b/scripts/install_slippage_report_timer.sh
@@ -0,0 +1,64 @@
+#!/usr/bin/env bash
+set -euo pipefail
+
+PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
+CONFIG_FILE="$PROJECT_DIR/config/slippage_report_config.json"
+SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
+mkdir -p "$SYSTEMD_USER_DIR"
+
+SERVICE_FILE="$SYSTEMD_USER_DIR/trading-bot-slippage-report.service"
+TIMER_FILE="$SYSTEMD_USER_DIR/trading-bot-slippage-report.timer"
+
+ON_CALENDAR_LINES="$("$PROJECT_DIR/.venv/bin/python" - <<PY
+import json
+from pathlib import Path
+config = json.loads(Path("$CONFIG_FILE").read_text())
+timezone = str(config.get("timezone", "")).strip()
+times = config.get("on_calendar_times", ["Sun 18:00:00"])
+for item in times:
+    value = str(item).strip()
+    if timezone and "/" not in value:
+        value = f"{value} {timezone}"
+    print(f"OnCalendar={value}")
+PY
+)"
+
+chmod +x "$PROJECT_DIR/scripts/run_weekly_slippage_report.sh"
+
+cat > "$SERVICE_FILE" <<SERVICE
+[Unit]
+Description=Trading Bot weekly paper vs signal slippage report
+
+[Service]
+Type=oneshot
+WorkingDirectory=$PROJECT_DIR
+ExecStart=$PROJECT_DIR/scripts/run_weekly_slippage_report.sh
+SERVICE
+
+cat > "$TIMER_FILE" <<TIMER
+[Unit]
+Description=Weekly slippage report (paper fills vs signal price)
+
+[Timer]
+$ON_CALENDAR_LINES
+Persistent=true
+AccuracySec=1min
+
+[Install]
+WantedBy=timers.target
+TIMER
+
+systemctl --user daemon-reload
+
+echo "Created:"
+echo "  $SERVICE_FILE"
+echo "  $TIMER_FILE"
+echo
+echo "Schedule:"
+echo "$ON_CALENDAR_LINES"
+echo
+echo "To enable:"
+echo "  systemctl --user enable --now trading-bot-slippage-report.timer"
+echo
+echo "Manual run:"
+echo "  bash scripts/run_weekly_slippage_report.sh"
diff --git a/scripts/run_agy_slice.sh b/scripts/run_agy_slice.sh
new file mode 100755
index 0000000..b52de0a
--- /dev/null
+++ b/scripts/run_agy_slice.sh
@@ -0,0 +1,17 @@
+#!/usr/bin/env bash
+# Run the [AGY] test slice for a pass (pytest only; no main.py edits).
+set -euo pipefail
+
+ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
+cd "$ROOT"
+
+AGY_PROMPT="${AGY_PROMPT:-${1:-}}"
+TEST_PATHS="${AGY_TEST_PATHS:-tests/test_portfolio_backtest_gate.py}"
+
+if [[ -n "$AGY_PROMPT" && -f "$AGY_PROMPT" ]]; then
+  echo "AGY prompt: $AGY_PROMPT"
+fi
+
+echo "=== AGY slice: pytest ==="
+PYTHONPATH=. .venv/bin/python -m pytest -q $TEST_PATHS
+echo "AGY slice pytest: OK"
diff --git a/scripts/run_balanced_pass.sh b/scripts/run_balanced_pass.sh
new file mode 100755
index 0000000..a81fb17
--- /dev/null
+++ b/scripts/run_balanced_pass.sh
@@ -0,0 +1,39 @@
+#!/usr/bin/env bash
+# Balanced multi-account pass: AGY tests → orchestrator (post-workflow + Codex).
+#
+# Usage:
+#   RUN_ID=phase20_portfolio_gate bash scripts/run_balanced_pass.sh
+#   RUN_ID=phase20_portfolio_gate AGY_PROMPT=prompts/agy/phase20_portfolio_gate.md bash scripts/run_balanced_pass.sh
+#
+# Optional: AGY_USE_GEMINI=1 with `gemini` on PATH to implement tests from prompt (legacy).
+set -euo pipefail
+
+ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
+cd "$ROOT"
+
+RUN_ID="${RUN_ID:?Set RUN_ID}"
+AGY_PROMPT="${AGY_PROMPT:-prompts/agy/phase20_portfolio_gate.md}"
+OUT_DIR="reports/agent_pipeline/${RUN_ID}"
+mkdir -p "$OUT_DIR"
+
+if [[ -f "$AGY_PROMPT" ]]; then
+  cp "$AGY_PROMPT" "$OUT_DIR/AGY_TASK.md"
+fi
+
+echo "=== Balanced pass: $RUN_ID ==="
+
+if [[ "${AGY_USE_GEMINI:-}" == "1" ]] && command -v gemini >/dev/null 2>&1; then
+  echo "=== [AGY] Gemini CLI slice (AGY_USE_GEMINI=1) ==="
+  gemini --skip-trust --approval-mode auto_edit --prompt "$(cat "$AGY_PROMPT")"
+elif [[ "${SKIP_AGY:-}" == "1" ]]; then
+  echo "SKIP_AGY=1 — skipping AGY pytest slice"
+else
+  AGY_PROMPT="$AGY_PROMPT" bash scripts/run_agy_slice.sh
+fi
+
+exec .venv/bin/python scripts/agent_orchestrator.py \
+  --run-id "$RUN_ID" \
+  --balanced-pass \
+  --agy-prompt "$AGY_PROMPT" \
+  --task-file "$OUT_DIR/AGY_TASK.md" \
+  ${AGY_TEST_PATHS:+--agy-test-paths "$AGY_TEST_PATHS"}
diff --git a/scripts/run_daily_audit_summary.sh b/scripts/run_daily_audit_summary.sh
new file mode 100755
index 0000000..8e51ad8
--- /dev/null
+++ b/scripts/run_daily_audit_summary.sh
@@ -0,0 +1,9 @@
+#!/usr/bin/env bash
+set -euo pipefail
+ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
+cd "$ROOT"
+PYTHON="${ROOT}/.venv/bin/python"
+if [[ ! -x "$PYTHON" ]]; then
+  PYTHON=python3
+fi
+exec "$PYTHON" -m src.daily_audit_summary "$@"
diff --git a/scripts/run_gemini_post_workflow.sh b/scripts/run_gemini_post_workflow.sh
index c228a48..54f1eff 100755
--- a/scripts/run_gemini_post_workflow.sh
+++ b/scripts/run_gemini_post_workflow.sh
@@ -40,9 +40,23 @@ HARNESS_EXIT=$?
 cp "$OUT_DIR/review_harness.log" "$OUT_DIR/gemini_review_harness.log" 2>/dev/null || true
 
 echo "Running runtime tests..."
-.venv/bin/python -m pytest tests/test_report_performance.py tests/test_reappraise_regime.py > "$OUT_DIR/runtime_harness.log" 2>&1
+.venv/bin/python -m pytest \
+  tests/test_report_performance.py \
+  tests/test_reappraise_regime.py \
+  tests/test_portfolio_backtest_golden.py \
+  > "$OUT_DIR/runtime_harness.log" 2>&1
 RUNTIME_EXIT=$?
 
+echo "Running portfolio backtest gate (if outputs exist)..."
+GATE_EXIT=0
+if [ -f logs/portfolio_backtest/portfolio_summary.csv ]; then
+  PYTHONPATH=. .venv/bin/python scripts/check_portfolio_backtest_gate.py \
+    >> "$OUT_DIR/review_harness.log" 2>&1 || GATE_EXIT=$?
+else
+  echo "skip: logs/portfolio_backtest/portfolio_summary.csv not found" \
+    >> "$OUT_DIR/review_harness.log"
+fi
+
 echo "Generating review packet..."
 cat <<EOF > "$OUT_DIR/review_packet.md"
 # Agent Review Packet - Run: $RUN_ID
@@ -78,9 +92,10 @@ echo -e "# NEXT_TODO\n\n- [ ] Codex review pending for implementation agent: $IM
 echo "Creating summary.json..."
 cat <<EOF > "$OUT_DIR/summary.json"
 {
-  "overall_status": "$([ $HARNESS_EXIT -eq 0 ] && [ $RUNTIME_EXIT -eq 0 ] && echo "pass" || echo "fail")",
+  "overall_status": "$([ $HARNESS_EXIT -eq 0 ] && [ $RUNTIME_EXIT -eq 0 ] && [ $GATE_EXIT -eq 0 ] && echo "pass" || echo "fail")",
   "gemini_review_harness_exit_code": $HARNESS_EXIT,
-  "runtime_harness_exit_code": $RUNTIME_EXIT
+  "runtime_harness_exit_code": $RUNTIME_EXIT,
+  "portfolio_gate_exit_code": $GATE_EXIT
 }
 EOF
 
diff --git a/scripts/run_guard_impact_report.sh b/scripts/run_guard_impact_report.sh
new file mode 100755
index 0000000..00500f5
--- /dev/null
+++ b/scripts/run_guard_impact_report.sh
@@ -0,0 +1,9 @@
+#!/usr/bin/env bash
+set -euo pipefail
+ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
+cd "$ROOT"
+PYTHON="${ROOT}/.venv/bin/python"
+if [[ ! -x "$PYTHON" ]]; then
+  PYTHON=python3
+fi
+exec "$PYTHON" -m src.guard_impact_report "$@"
diff --git a/scripts/run_leverage_stress_report.sh b/scripts/run_leverage_stress_report.sh
new file mode 100755
index 0000000..9b3d3c7
--- /dev/null
+++ b/scripts/run_leverage_stress_report.sh
@@ -0,0 +1,9 @@
+#!/usr/bin/env bash
+set -euo pipefail
+ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
+cd "$ROOT"
+PYTHON="${ROOT}/.venv/bin/python"
+if [[ ! -x "$PYTHON" ]]; then
+  PYTHON=python3
+fi
+exec "$PYTHON" -m src.leverage_stress_report "$@"
diff --git a/scripts/run_llm_cache_report.sh b/scripts/run_llm_cache_report.sh
new file mode 100755
index 0000000..ae6342f
--- /dev/null
+++ b/scripts/run_llm_cache_report.sh
@@ -0,0 +1,9 @@
+#!/usr/bin/env bash
+set -euo pipefail
+ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
+cd "$ROOT"
+PYTHON="${ROOT}/.venv/bin/python"
+if [[ ! -x "$PYTHON" ]]; then
+  PYTHON=python3
+fi
+exec "$PYTHON" -m src.llm_cache_report "$@"
diff --git a/scripts/run_model_quality_report.sh b/scripts/run_model_quality_report.sh
new file mode 100755
index 0000000..4cfb6e4
--- /dev/null
+++ b/scripts/run_model_quality_report.sh
@@ -0,0 +1,14 @@
+#!/usr/bin/env bash
+set -euo pipefail
+
+PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
+cd "$PROJECT_DIR"
+
+METRICS_PATH="${1:-logs/ml/fold_metrics.csv}"
+if [[ ! -f "$METRICS_PATH" && -f logs/ml/ai_model_metrics.csv ]]; then
+  METRICS_PATH="logs/ml/ai_model_metrics.csv"
+fi
+
+PYTHONPATH=. "$PROJECT_DIR/.venv/bin/python" -m src.ml_quality_report \
+  --metrics "$METRICS_PATH" \
+  --output-dir logs/ml
diff --git a/scripts/run_pass_complete.sh b/scripts/run_pass_complete.sh
new file mode 100755
index 0000000..7d238b5
--- /dev/null
+++ b/scripts/run_pass_complete.sh
@@ -0,0 +1,81 @@
+#!/usr/bin/env bash
+# Close one dev pass: pytest → review packet → Codex scoped review → NEXT_TODO.
+#
+# Usage:
+#   RUN_ID=phase20_golden bash scripts/run_pass_complete.sh
+#   RUN_ID=phase20_golden bash scripts/run_pass_complete.sh "Cursor feature + AGY golden tests"
+#   RUN_ID=phase20_golden TASK_FILE=prompts/my_pass.md bash scripts/run_pass_complete.sh
+#
+# Requires: .venv, Codex CLI with credits for step 3.
+# FULL_PYTEST=1 for entire suite; SKIP_PYTEST=1 if already green.
+set -euo pipefail
+
+ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
+cd "$ROOT"
+
+RUN_ID="${RUN_ID:?Set RUN_ID, e.g. RUN_ID=phase20_golden}"
+IMPLEMENTATION_AGENT="${IMPLEMENTATION_AGENT:-cursor}"
+OUT_DIR="reports/agent_pipeline/${RUN_ID}"
+mkdir -p "$OUT_DIR"
+
+if [[ -n "${1:-}" ]]; then
+  printf '%s\n' "$1" >"$OUT_DIR/TASK.md"
+elif [[ -n "${TASK_FILE:-}" && -f "$TASK_FILE" ]]; then
+  cp "$TASK_FILE" "$OUT_DIR/TASK.md"
+elif [[ ! -f "$OUT_DIR/TASK.md" ]]; then
+  printf 'Pass %s: Cursor implementation + AGY tests complete. Request Codex review.\n' "$RUN_ID" >"$OUT_DIR/TASK.md"
+fi
+
+echo "=== [1/3] pytest ==="
+if [[ "${SKIP_PYTEST:-}" == "1" ]]; then
+  echo "SKIP_PYTEST=1 — skipped"
+elif [[ "${FULL_PYTEST:-}" == "1" ]]; then
+  PYTHONPATH=. .venv/bin/python -m pytest -q
+else
+  # Default: harness-aligned subset (fast, no optional qlib/xgboost stack required).
+  PYTHONPATH=. .venv/bin/python -m pytest -q \
+    tests/test_report_performance.py \
+    tests/test_reappraise_regime.py \
+    tests/test_portfolio_backtest_golden.py \
+    tests/test_portfolio_backtest_gate.py
+fi
+
+echo "=== [2/3] Codex review via orchestrator (post-workflow + scoped review) ==="
+export IMPLEMENTATION_AGENT
+CODEX_EXIT=0
+.venv/bin/python scripts/agent_orchestrator.py \
+  --run-id "$RUN_ID" \
+  --task-file "$OUT_DIR/TASK.md" \
+  --run-codex-review \
+  --scoped-review \
+  --ignore-artifacts \
+  || CODEX_EXIT=$?
+
+echo ""
+echo "=== [3/3] Pass outputs ==="
+echo "  Review packet:  $OUT_DIR/review_packet.md"
+echo "  Draft TODO:     $OUT_DIR/NEXT_TODO.md"
+if [[ -f "$OUT_DIR/NEXT_TODO.codex.md" ]]; then
+  echo "  Codex TODO:     $OUT_DIR/NEXT_TODO.codex.md  ← read this next"
+  echo ""
+  echo "--- NEXT_TODO.codex.md (preview) ---"
+  head -40 "$OUT_DIR/NEXT_TODO.codex.md" || true
+else
+  echo "  Codex TODO:     (missing — Codex did not finish)"
+  if [[ -f "$OUT_DIR/codex_review_command.log" ]]; then
+    echo ""
+    echo "--- codex_review_command.log (tail) ---"
+    tail -15 "$OUT_DIR/codex_review_command.log" || true
+  fi
+fi
+
+echo ""
+if [[ "$CODEX_EXIT" -ne 0 ]] || [[ ! -f "$OUT_DIR/NEXT_TODO.codex.md" ]]; then
+  echo "Codex review incomplete (exit ${CODEX_EXIT:-?}). Fix credits/CLI, then re-run:"
+  echo "  RUN_ID=$RUN_ID SKIP_PYTEST=1 bash scripts/run_pass_complete.sh"
+  exit "${CODEX_EXIT:-1}"
+fi
+
+echo "Pass complete. Implement items from NEXT_TODO.codex.md in Cursor, then repeat."
+PYTHONPATH=. .venv/bin/python scripts/agent_workload_report.py --record 2>/dev/null || true
+exit 0
diff --git a/scripts/run_retrain.sh b/scripts/run_retrain.sh
index 90fdab4..10be94a 100755
--- a/scripts/run_retrain.sh
+++ b/scripts/run_retrain.sh
@@ -9,11 +9,21 @@ LOG_DIR="$PROJECT_DIR/logs/retrain_runs"
 mkdir -p "$LOG_DIR"
 LOG_FILE="$LOG_DIR/retrain_${TIMESTAMP}.log"
 
+set +e
 {
   echo "timestamp=$TIMESTAMP"
   echo "project_dir=$PROJECT_DIR"
   echo "--------------------------------------------------------------------------------"
   "$PROJECT_DIR/.venv/bin/python" -m src.train_ai_model
 } > "$LOG_FILE" 2>&1
+EXIT_CODE=$?
+set -e
+
+if [[ "$EXIT_CODE" -ne 0 ]]; then
+  echo "Retrain FAILED (exit=$EXIT_CODE): $LOG_FILE"
+  echo "Check logs/retrain_history.csv (status=failure) and Telegram for 'AI Retrain Failed'."
+  exit "$EXIT_CODE"
+fi
 
 echo "Retrain completed: $LOG_FILE"
+echo "On champion retained (not promoted), Telegram sends 'Retrain finished; champion retained'."
diff --git a/scripts/run_weekly_slippage_report.sh b/scripts/run_weekly_slippage_report.sh
new file mode 100755
index 0000000..193c9ee
--- /dev/null
+++ b/scripts/run_weekly_slippage_report.sh
@@ -0,0 +1,46 @@
+#!/usr/bin/env bash
+set -euo pipefail
+
+PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
+cd "$PROJECT_DIR"
+
+TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
+LOG_DIR="$PROJECT_DIR/logs/slippage_report_runs"
+mkdir -p "$LOG_DIR"
+LOG_FILE="$LOG_DIR/slippage_${TIMESTAMP}.log"
+
+LOOKBACK_DAYS="$("$PROJECT_DIR/.venv/bin/python" - <<'PY'
+import json
+from pathlib import Path
+path = Path("config/slippage_report_config.json")
+if path.is_file():
+    print(int(json.loads(path.read_text()).get("lookback_days", 7)))
+else:
+    print(7)
+PY
+)"
+
+TELEGRAM_FLAG=""
+if "$PROJECT_DIR/.venv/bin/python" - <<'PY'
+import json
+from pathlib import Path
+path = Path("config/slippage_report_config.json")
+if path.is_file() and json.loads(path.read_text()).get("notify_telegram"):
+    raise SystemExit(0)
+raise SystemExit(1)
+PY
+then
+  TELEGRAM_FLAG="--telegram"
+fi
+
+{
+  echo "timestamp=$TIMESTAMP"
+  echo "lookback_days=$LOOKBACK_DAYS"
+  echo "--------------------------------------------------------------------------------"
+  PYTHONPATH=. "$PROJECT_DIR/.venv/bin/python" -m src.report_performance \
+    --weekly \
+    --days "$LOOKBACK_DAYS" \
+    $TELEGRAM_FLAG
+} >"$LOG_FILE" 2>&1
+
+echo "Weekly slippage report completed: $LOG_FILE"
diff --git a/src/daily_audit_summary.py b/src/daily_audit_summary.py
new file mode 100644
index 0000000..be8a761
--- /dev/null
+++ b/src/daily_audit_summary.py
@@ -0,0 +1,293 @@
+"""Aggregate daily execution audit logs (skips, API errors, stale data)."""
+
+from __future__ import annotations
+
+import argparse
+import json
+from collections import Counter
+from datetime import date, datetime, timezone
+from pathlib import Path
+from typing import Any
+
+import pandas as pd
+
+from src.config import EXECUTION_AUDIT_LOG_PATH
+
+DEFAULT_OUTPUT_DIR = Path("logs/audit_daily")
+
+SKIP_EVENT_TYPES = frozenset({"SKIP_BUY", "SKIP_EXIT"})
+API_ERROR_EVENT_TYPES = frozenset({"BUY_ERROR", "EXIT_ERROR"})
+ORDER_SUBMITTED_EVENT_TYPES = frozenset({"BUY_SUBMITTED", "FULL_EXIT", "PARTIAL_EXIT"})
+
+DAILY_AUDIT_SUMMARY_KEYS = (
+    "generated_at",
+    "row_count",
+    "event_type_counts",
+    "skip_by_event",
+    "skip_reason_counts",
+    "api_error_count",
+    "api_error_samples",
+    "stale_bar_count",
+    "orders_submitted_count",
+    "unique_tickers",
+    "context_skip_counts",
+    "context_skip_rate_of_skips",
+)
+
+SKIP_REASONS_CSV_COLUMNS = ("reason", "count")
+
+CONTEXT_SKIP_BUCKETS = ("earnings", "macro_event", "stale", "other")
+
+
+def _utc_now_iso() -> str:
+    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
+
+
+def _parse_audit_timestamps(series: pd.Series) -> pd.Series:
+    return pd.to_datetime(series, errors="coerce", utc=True)
+
+
+def load_execution_audit(
+    audit_path: str | Path = EXECUTION_AUDIT_LOG_PATH,
+    *,
+    day: date | None = None,
+    lookback_days: int | None = None,
+) -> pd.DataFrame:
+    path = Path(audit_path)
+    if not path.is_file():
+        return pd.DataFrame()
+
+    df = pd.read_csv(path)
+    if df.empty or "timestamp" not in df.columns:
+        return df
+
+    df = df.copy()
+    df["_ts"] = _parse_audit_timestamps(df["timestamp"])
+    df = df.dropna(subset=["_ts"])
+
+    if day is not None:
+        start = pd.Timestamp(day, tz="UTC")
+        end = start + pd.Timedelta(days=1)
+        df = df[(df["_ts"] >= start) & (df["_ts"] < end)]
+    elif lookback_days is not None and lookback_days > 0:
+        cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=lookback_days)
+        df = df[df["_ts"] >= cutoff]
+
+    return df.drop(columns=["_ts"])
+
+
+def _normalize_skip_reason(reason: str) -> str:
+    text = str(reason or "").strip()
+    if not text:
+        return "unknown"
+    lower = text.lower()
+    if "stale" in lower:
+        return "stale_price_data"
+    if "dry_run" in lower or "dry-run" in lower:
+        return "dry_run_only"
+    if "cooldown" in lower:
+        return "cooldown"
+    if "max orders" in lower:
+        return "max_orders"
+    if "regime" in lower or "bear" in lower:
+        return "regime_or_signal"
+    if "llm" in lower or "reject" in lower:
+        return "llm_or_policy"
+    return text[:80]
+
+
+def _classify_context_skip(reason: str) -> str:
+    lower = str(reason or "").lower()
+    if "earnings" in lower:
+        return "earnings"
+    if "macro event" in lower or "macro_event" in lower:
+        return "macro_event"
+    if "stale" in lower:
+        return "stale"
+    return "other"
+
+
+def aggregate_context_skips(df: pd.DataFrame) -> tuple[dict[str, int], dict[str, float]]:
+    if df is None or df.empty or "event_type" not in df.columns:
+        empty = {bucket: 0 for bucket in CONTEXT_SKIP_BUCKETS}
+        return empty, {bucket: 0.0 for bucket in CONTEXT_SKIP_BUCKETS}
+
+    event_types = df["event_type"].astype(str)
+    reasons = df["reason"].astype(str) if "reason" in df.columns else pd.Series(dtype=str)
+    skip_mask = event_types.isin(SKIP_EVENT_TYPES)
+    skip_reasons = reasons[skip_mask].tolist()
+    counts = Counter(_classify_context_skip(r) for r in skip_reasons)
+    total_skips = max(len(skip_reasons), 1)
+    context_counts = {bucket: int(counts.get(bucket, 0)) for bucket in CONTEXT_SKIP_BUCKETS}
+    context_rates = {
+        bucket: round(context_counts[bucket] / total_skips, 4) for bucket in CONTEXT_SKIP_BUCKETS
+    }
+    return context_counts, context_rates
+
+
+def validate_daily_audit_summary(report: dict[str, Any]) -> dict[str, Any]:
+    for key in DAILY_AUDIT_SUMMARY_KEYS:
+        if key not in report:
+            raise ValueError(f"Missing daily audit summary key: {key}")
+    if not isinstance(report["row_count"], int) or report["row_count"] < 0:
+        raise ValueError("row_count must be a non-negative int")
+    if not isinstance(report["api_error_count"], int) or report["api_error_count"] < 0:
+        raise ValueError("api_error_count must be a non-negative int")
+    for bucket in CONTEXT_SKIP_BUCKETS:
+        if bucket not in report["context_skip_counts"]:
+            raise ValueError(f"Missing context skip bucket: {bucket}")
+    return report
+
+
+def validate_skip_reasons_csv(path: str | Path) -> pd.DataFrame:
+    frame = pd.read_csv(path)
+    missing = [col for col in SKIP_REASONS_CSV_COLUMNS if col not in frame.columns]
+    if missing:
+        raise ValueError(f"skip_reasons CSV missing columns: {missing}")
+    if (frame["count"] < 0).any():
+        raise ValueError("skip_reasons count must be non-negative")
+    return frame
+
+
+def aggregate_execution_audit(df: pd.DataFrame) -> dict[str, Any]:
+    if df is None or df.empty:
+        return {
+            "generated_at": _utc_now_iso(),
+            "row_count": 0,
+            "event_type_counts": {},
+            "skip_by_event": {},
+            "skip_reason_counts": {},
+            "api_error_count": 0,
+            "api_error_samples": [],
+            "stale_bar_count": 0,
+            "orders_submitted_count": 0,
+            "unique_tickers": 0,
+            "context_skip_counts": {bucket: 0 for bucket in CONTEXT_SKIP_BUCKETS},
+            "context_skip_rate_of_skips": {bucket: 0.0 for bucket in CONTEXT_SKIP_BUCKETS},
+        }
+
+    event_types = df["event_type"].astype(str) if "event_type" in df.columns else pd.Series(dtype=str)
+    reasons = df["reason"].astype(str) if "reason" in df.columns else pd.Series(dtype=str)
+
+    skip_mask = event_types.isin(SKIP_EVENT_TYPES)
+    skip_reasons = Counter(
+        _normalize_skip_reason(r) for r in reasons[skip_mask].tolist()
+    )
+    skip_by_event = Counter(event_types[skip_mask].tolist())
+
+    api_mask = event_types.isin(API_ERROR_EVENT_TYPES)
+    api_error_count = int(api_mask.sum())
+
+    stale_mask = reasons.str.contains("stale", case=False, na=False)
+    stale_bar_count = int(stale_mask.sum())
+
+    orders_submitted = int(event_types.isin(ORDER_SUBMITTED_EVENT_TYPES).sum())
+    tickers = df["ticker"].astype(str).nunique() if "ticker" in df.columns else 0
+
+    api_samples = (
+        df.loc[api_mask, ["timestamp", "event_type", "ticker", "reason"]]
+        .head(10)
+        .to_dict(orient="records")
+        if api_mask.any()
+        else []
+    )
+    context_counts, context_rates = aggregate_context_skips(df)
+
+    return {
+        "generated_at": _utc_now_iso(),
+        "row_count": int(len(df)),
+        "event_type_counts": dict(Counter(event_types.tolist())),
+        "skip_by_event": dict(skip_by_event),
+        "skip_reason_counts": dict(skip_reasons.most_common()),
+        "api_error_count": api_error_count,
+        "api_error_samples": api_samples,
+        "stale_bar_count": stale_bar_count,
+        "orders_submitted_count": orders_submitted,
+        "unique_tickers": int(tickers),
+        "context_skip_counts": context_counts,
+        "context_skip_rate_of_skips": context_rates,
+    }
+
+
+def format_daily_audit_report(report: dict[str, Any]) -> str:
+    lines = [
+        "=== Daily Execution Audit Summary ===",
+        f"Rows: {report.get('row_count', 0)} | Tickers: {report.get('unique_tickers', 0)}",
+        f"Orders submitted (buy/exit events): {report.get('orders_submitted_count', 0)}",
+        f"API errors: {report.get('api_error_count', 0)} | Stale bar mentions: {report.get('stale_bar_count', 0)}",
+    ]
+    skip_by = report.get("skip_by_event") or {}
+    if skip_by:
+        lines.append("Skips by event: " + ", ".join(f"{k}={v}" for k, v in sorted(skip_by.items())))
+    skip_reasons = report.get("skip_reason_counts") or {}
+    if skip_reasons:
+        top = ", ".join(f"{k}={v}" for k, v in list(skip_reasons.items())[:8])
+        lines.append(f"Top skip reasons: {top}")
+    context = report.get("context_skip_counts") or {}
+    if any(context.values()):
+        lines.append(
+            "Context skips: "
+            + ", ".join(f"{k}={v}" for k, v in sorted(context.items()) if v)
+        )
+    return "\n".join(lines)
+
+
+def write_daily_audit_artifacts(
+    report: dict[str, Any],
+    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
+    *,
+    day: date | None = None,
+) -> Path:
+    output_dir = Path(output_dir)
+    output_dir.mkdir(parents=True, exist_ok=True)
+    stamp = (day or date.today()).strftime("%Y%m%d")
+    day_path = output_dir / f"audit_{stamp}.json"
+    day_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
+    latest = output_dir / "latest_summary.json"
+    latest.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
+    if report.get("skip_reason_counts"):
+        pd.DataFrame(
+            [{"reason": k, "count": v} for k, v in report["skip_reason_counts"].items()]
+        ).to_csv(output_dir / f"skip_reasons_{stamp}.csv", index=False)
+    return day_path
+
+
+def run_daily_audit_summary(
+    *,
+    audit_path: str | Path = EXECUTION_AUDIT_LOG_PATH,
+    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
+    day: date | None = None,
+    lookback_days: int | None = None,
+) -> dict[str, Any]:
+    df = load_execution_audit(audit_path, day=day, lookback_days=lookback_days)
+    report = aggregate_execution_audit(df)
+    validate_daily_audit_summary(report)
+    write_daily_audit_artifacts(report, output_dir, day=day or date.today())
+    return report
+
+
+def main() -> None:
+    parser = argparse.ArgumentParser(description="Daily execution audit aggregation")
+    parser.add_argument("--audit-path", default=EXECUTION_AUDIT_LOG_PATH)
+    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
+    parser.add_argument("--date", help="UTC date YYYY-MM-DD (default: today)")
+    parser.add_argument("--days", type=int, help="Lookback days instead of single day")
+    args = parser.parse_args()
+
+    day = None
+    if args.date:
+        day = date.fromisoformat(args.date)
+    lookback = args.days if not args.date else None
+
+    report = run_daily_audit_summary(
+        audit_path=args.audit_path,
+        output_dir=args.output_dir,
+        day=day,
+        lookback_days=lookback,
+    )
+    print(format_daily_audit_report(report))
+    print(f"\nWrote summary under {args.output_dir}")
+
+
+if __name__ == "__main__":
+    main()
diff --git a/src/guard_impact_metrics.py b/src/guard_impact_metrics.py
new file mode 100644
index 0000000..68cdb8f
--- /dev/null
+++ b/src/guard_impact_metrics.py
@@ -0,0 +1,37 @@
+"""Pure helpers for guard impact report (no backtest imports)."""
+
+from __future__ import annotations
+
+from typing import Any
+
+GUARD_IMPACT_REPORT_KEYS = (
+    "generated_at",
+    "baseline",
+    "with_crowding_guard",
+    "delta",
+    "crowding_guard_enabled_in_config",
+)
+
+
+def result_metrics(result) -> dict[str, Any]:
+    return {
+        "total_return_pct": round(float(result.total_return) * 100.0, 4),
+        "max_drawdown_pct": round(float(result.max_drawdown) * 100.0, 4),
+        "sharpe_ratio": round(float(result.sharpe_ratio), 4),
+        "trade_count": int(result.trades),
+        "win_rate_pct": round(float(result.win_rate) * 100.0, 4),
+    }
+
+
+def delta_metrics(baseline: dict[str, Any], guarded: dict[str, Any]) -> dict[str, Any]:
+    return {
+        key: round(guarded[key] - baseline[key], 4)
+        for key in ("total_return_pct", "max_drawdown_pct", "sharpe_ratio", "trade_count", "win_rate_pct")
+    }
+
+
+def validate_guard_impact_report(report: dict[str, Any]) -> dict[str, Any]:
+    for key in GUARD_IMPACT_REPORT_KEYS:
+        if key not in report:
+            raise ValueError(f"Missing guard impact report key: {key}")
+    return report
diff --git a/src/guard_impact_report.py b/src/guard_impact_report.py
new file mode 100644
index 0000000..29dadbc
--- /dev/null
+++ b/src/guard_impact_report.py
@@ -0,0 +1,179 @@
+"""Compare portfolio backtest metrics with factor/crowding guard on vs off."""
+
+from __future__ import annotations
+
+import argparse
+import json
+from dataclasses import replace
+from datetime import datetime, timezone
+from pathlib import Path
+from typing import Any
+from unittest.mock import patch
+
+import pandas as pd
+
+from src.data_loader import load_price_data_batch
+from src.macro_loader import load_macro_data
+from src.portfolio_backtester import build_ai_score_frames, run_portfolio_backtest
+from src.settings import StrategySettings, load_settings
+
+from src.guard_impact_metrics import (
+    GUARD_IMPACT_REPORT_KEYS,
+    delta_metrics,
+    result_metrics,
+    validate_guard_impact_report,
+)
+
+DEFAULT_OUTPUT_DIR = Path("logs/guard_impact")
+
+
+def _utc_now_iso() -> str:
+    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
+
+
+def build_guard_impact_report(
+    *,
+    settings: StrategySettings,
+    ticker_data: dict[str, pd.DataFrame],
+    benchmark_df: pd.DataFrame | None,
+    relative_strength_benchmark_df: pd.DataFrame | None,
+    vix_df: pd.DataFrame | None,
+    macro_df: pd.DataFrame | None,
+    ai_score_frames: dict[str, pd.DataFrame] | None,
+) -> dict[str, Any]:
+    common_kwargs = dict(
+        ticker_data=ticker_data,
+        benchmark_df=benchmark_df,
+        relative_strength_benchmark_df=relative_strength_benchmark_df,
+        initial_cash=10000.0,
+        max_positions=settings.max_total_positions,
+        target_position_pct=settings.max_position_pct,
+        transaction_cost_pct=0.001,
+        ma_fast=settings.ma_fast,
+        ma_slow=settings.ma_slow,
+        rsi_buy_limit=settings.rsi_buy_limit,
+        use_ai_score=settings.use_ai_score,
+        ai_score_buy_threshold=settings.ai_score_buy_threshold,
+        market_regime_filter_enabled=settings.market_regime_filter_enabled,
+        market_regime_ma_fast=settings.market_regime_ma_fast,
+        market_regime_ma_slow=settings.market_regime_ma_slow,
+        relative_strength_filter_enabled=settings.relative_strength_filter_enabled,
+        relative_strength_lookback_days=settings.relative_strength_lookback_days,
+        relative_strength_min_excess_return=settings.relative_strength_min_excess_return,
+        volume_filter_enabled=settings.volume_filter_enabled,
+        volume_lookback_days=settings.volume_lookback_days,
+        min_volume_ratio=settings.min_volume_ratio,
+        volatility_filter_enabled=settings.volatility_filter_enabled,
+        volatility_lookback_days=settings.volatility_lookback_days,
+        max_volatility=settings.max_volatility,
+        rank_trend_weight=settings.rank_trend_weight,
+        rank_ai_weight=settings.rank_ai_weight,
+        rank_momentum_weight=settings.rank_momentum_weight,
+        rank_volatility_weight=settings.rank_volatility_weight,
+        ai_exit_enabled=getattr(settings, "ai_exit_enabled", False),
+        ai_exit_threshold=getattr(settings, "ai_exit_threshold", 0.35),
+        ai_exit_dynamic_enabled=getattr(settings, "ai_exit_dynamic_enabled", False),
+        ai_exit_vix_low=getattr(settings, "ai_exit_vix_low", 15.0),
+        ai_exit_vix_high=getattr(settings, "ai_exit_vix_high", 25.0),
+        ai_exit_threshold_bull=getattr(settings, "ai_exit_threshold_bull", 0.55),
+        ai_exit_threshold_bear=getattr(settings, "ai_exit_threshold_bear", 0.28),
+        vix_df=vix_df,
+        macro_df=macro_df,
+        ai_score_frames=ai_score_frames,
+    )
+
+    settings_off = replace(settings, crowding_guard_enabled=False)
+    settings_on = replace(settings, crowding_guard_enabled=True)
+
+    with patch("src.risk_manager.load_settings", return_value=settings_off):
+        baseline_result, _, baseline_trades = run_portfolio_backtest(
+            **common_kwargs,
+            crowding_guard_enabled=False,
+        )
+    with patch("src.risk_manager.load_settings", return_value=settings_on):
+        guarded_result, _, guarded_trades = run_portfolio_backtest(
+            **common_kwargs,
+            crowding_guard_enabled=True,
+        )
+
+    baseline = result_metrics(baseline_result)
+    guarded = result_metrics(guarded_result)
+    blocked_buys = max(0, len(baseline_trades) - len(guarded_trades))
+
+    guarded["estimated_crowding_blocked_trades"] = blocked_buys
+    delta = delta_metrics(baseline, guarded)
+
+    return validate_guard_impact_report(
+        {
+            "generated_at": _utc_now_iso(),
+            "baseline": baseline,
+            "with_crowding_guard": guarded,
+            "delta": delta,
+            "crowding_guard_enabled_in_config": bool(settings.crowding_guard_enabled),
+        }
+    )
+
+
+def write_guard_impact_artifacts(report: dict[str, Any], output_dir: Path = DEFAULT_OUTPUT_DIR) -> Path:
+    output_dir.mkdir(parents=True, exist_ok=True)
+    path = output_dir / "latest_summary.json"
+    path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
+    return path
+
+
+def run_guard_impact_report() -> dict[str, Any]:
+    settings = load_settings()
+    tickers_to_load = list(settings.tickers)
+    if settings.market_regime_filter_enabled:
+        tickers_to_load.append(settings.market_regime_ticker)
+    if settings.relative_strength_filter_enabled:
+        tickers_to_load.append(settings.relative_strength_benchmark_ticker)
+    if settings.use_ai_score and "^VIX" not in tickers_to_load:
+        tickers_to_load.append("^VIX")
+    tickers_to_load = list(dict.fromkeys(tickers_to_load))
+    loaded = load_price_data_batch(tickers_to_load, period="2y")
+    ticker_data = {t: loaded[t] for t in settings.tickers if t in loaded}
+    vix_df = loaded.get("^VIX")
+    macro_df = load_macro_data(period="2y") if settings.use_ai_score else None
+    benchmark_df = (
+        loaded.get(settings.market_regime_ticker)
+        if settings.market_regime_filter_enabled
+        else None
+    )
+    rs_df = (
+        loaded.get(settings.relative_strength_benchmark_ticker)
+        if settings.relative_strength_filter_enabled
+        else None
+    )
+    ai_score_frames = None
+    if settings.use_ai_score:
+        ai_score_frames = build_ai_score_frames(
+            ticker_data=ticker_data,
+            vix_df=vix_df,
+            macro_df=macro_df,
+        )
+
+    report = build_guard_impact_report(
+        settings=settings,
+        ticker_data=ticker_data,
+        benchmark_df=benchmark_df,
+        relative_strength_benchmark_df=rs_df,
+        vix_df=vix_df,
+        macro_df=macro_df,
+        ai_score_frames=ai_score_frames,
+    )
+    write_guard_impact_artifacts(report)
+    return report
+
+
+def main() -> None:
+    parser = argparse.ArgumentParser(description="Crowding guard backtest impact report")
+    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
+    args = parser.parse_args()
+    report = run_guard_impact_report()
+    write_guard_impact_artifacts(report, Path(args.output_dir))
+    print(json.dumps(report, indent=2))
+
+
+if __name__ == "__main__":
+    main()
diff --git a/src/leverage_stress_report.py b/src/leverage_stress_report.py
new file mode 100644
index 0000000..5d9c843
--- /dev/null
+++ b/src/leverage_stress_report.py
@@ -0,0 +1,166 @@
+"""Stress portfolio equity under gap-down and correlation-spike scenarios."""
+
+from __future__ import annotations
+
+import argparse
+import json
+from datetime import datetime, timezone
+from pathlib import Path
+from typing import Any
+
+import pandas as pd
+
+DEFAULT_OUTPUT_DIR = Path("logs/leverage_stress")
+DEFAULT_EQUITY_PATH = Path("logs/portfolio_backtest/portfolio_equity.csv")
+
+LEVERAGE_STRESS_REPORT_KEYS = (
+    "generated_at",
+    "input",
+    "scenarios",
+)
+
+STRESS_SCENARIOS = (
+    {"name": "gap_down_5pct", "gap_down_pct": 0.05, "correlation_multiplier": 1.0},
+    {"name": "gap_down_10pct", "gap_down_pct": 0.10, "correlation_multiplier": 1.0},
+    {"name": "correlation_spike_1p5x", "gap_down_pct": 0.0, "correlation_multiplier": 1.5},
+    {"name": "gap_down_10pct_corr_1p5x", "gap_down_pct": 0.10, "correlation_multiplier": 1.5},
+)
+
+
+def _utc_now_iso() -> str:
+    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
+
+
+def load_equity_series(path: str | Path = DEFAULT_EQUITY_PATH) -> pd.Series:
+    frame = pd.read_csv(path)
+    if "equity" not in frame.columns:
+        raise ValueError("equity CSV must contain an 'equity' column")
+    date_col = "date" if "date" in frame.columns else frame.columns[0]
+    series = pd.to_numeric(frame["equity"], errors="coerce").dropna()
+    series.index = pd.to_datetime(frame[date_col], errors="coerce")
+    return series.sort_index()
+
+
+def stress_equity_series(
+    equity: pd.Series,
+    *,
+    gap_down_pct: float,
+    leverage: float,
+    correlation_multiplier: float,
+) -> pd.Series:
+    if equity.empty:
+        raise ValueError("equity series must not be empty")
+    returns = equity.pct_change().fillna(0.0).astype(float)
+    if gap_down_pct > 0:
+        shock_idx = returns.idxmin() if len(returns) > 1 else returns.index[0]
+        returns = returns.copy()
+        returns.loc[shock_idx] = float(returns.loc[shock_idx]) - gap_down_pct * leverage
+    if correlation_multiplier != 1.0:
+        returns = returns.apply(
+            lambda value: float(value) * correlation_multiplier if value < 0 else float(value)
+        )
+    stressed = (1.0 + returns).cumprod() * float(equity.iloc[0])
+    stressed.name = "stressed_equity"
+    return stressed
+
+
+def max_drawdown_pct(equity: pd.Series) -> float:
+    running_max = equity.cummax()
+    drawdown = equity / running_max - 1.0
+    return round(float(drawdown.min()) * 100.0, 4)
+
+
+def build_leverage_stress_report(
+    equity: pd.Series,
+    *,
+    leverage: float = 1.0,
+    scenarios: tuple[dict[str, Any], ...] = STRESS_SCENARIOS,
+) -> dict[str, Any]:
+    if leverage <= 0:
+        raise ValueError("leverage must be positive")
+
+    baseline_final = float(equity.iloc[-1])
+    baseline_dd = max_drawdown_pct(equity)
+    scenario_rows: list[dict[str, Any]] = []
+
+    for scenario in scenarios:
+        stressed = stress_equity_series(
+            equity,
+            gap_down_pct=float(scenario["gap_down_pct"]),
+            leverage=leverage,
+            correlation_multiplier=float(scenario["correlation_multiplier"]),
+        )
+        final_equity = float(stressed.iloc[-1])
+        scenario_rows.append(
+            {
+                "name": scenario["name"],
+                "gap_down_pct": scenario["gap_down_pct"],
+                "correlation_multiplier": scenario["correlation_multiplier"],
+                "final_equity": round(final_equity, 2),
+                "final_equity_delta_pct": round((final_equity / baseline_final - 1.0) * 100.0, 4),
+                "max_drawdown_pct": max_drawdown_pct(stressed),
+                "max_drawdown_delta_pct": round(max_drawdown_pct(stressed) - baseline_dd, 4),
+            }
+        )
+
+    report = {
+        "generated_at": _utc_now_iso(),
+        "input": {
+            "rows": int(len(equity)),
+            "leverage": leverage,
+            "baseline_final_equity": round(baseline_final, 2),
+            "baseline_max_drawdown_pct": baseline_dd,
+        },
+        "scenarios": scenario_rows,
+    }
+    validate_leverage_stress_report(report)
+    return report
+
+
+def validate_leverage_stress_report(report: dict[str, Any]) -> dict[str, Any]:
+    for key in LEVERAGE_STRESS_REPORT_KEYS:
+        if key not in report:
+            raise ValueError(f"Missing leverage stress report key: {key}")
+    if not report["scenarios"]:
+        raise ValueError("scenarios must not be empty")
+    return report
+
+
+def write_leverage_stress_artifacts(
+    report: dict[str, Any],
+    output_dir: Path = DEFAULT_OUTPUT_DIR,
+) -> Path:
+    output_dir.mkdir(parents=True, exist_ok=True)
+    path = output_dir / "latest_summary.json"
+    path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
+    return path
+
+
+def run_leverage_stress_report(
+    equity_path: str | Path = DEFAULT_EQUITY_PATH,
+    *,
+    leverage: float = 1.0,
+    output_dir: Path = DEFAULT_OUTPUT_DIR,
+) -> dict[str, Any]:
+    equity = load_equity_series(equity_path)
+    report = build_leverage_stress_report(equity, leverage=leverage)
+    write_leverage_stress_artifacts(report, output_dir)
+    return report
+
+
+def main() -> None:
+    parser = argparse.ArgumentParser(description="Leverage stress scenarios on portfolio equity")
+    parser.add_argument("--equity-path", default=str(DEFAULT_EQUITY_PATH))
+    parser.add_argument("--leverage", type=float, default=1.0)
+    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
+    args = parser.parse_args()
+    report = run_leverage_stress_report(
+        args.equity_path,
+        leverage=args.leverage,
+        output_dir=Path(args.output_dir),
+    )
+    print(json.dumps(report, indent=2))
+
+
+if __name__ == "__main__":
+    main()
diff --git a/src/llm_cache_report.py b/src/llm_cache_report.py
new file mode 100644
index 0000000..f12037c
--- /dev/null
+++ b/src/llm_cache_report.py
@@ -0,0 +1,149 @@
+"""Monitor LLM consensus cache size, coverage, and reuse (hit proxy)."""
+
+from __future__ import annotations
+
+import argparse
+import json
+from collections import Counter
+from datetime import datetime, timezone
+from pathlib import Path
+from typing import Any
+
+DEFAULT_CACHE_PATH = Path("data/llm_cache.json")
+DEFAULT_OUTPUT_DIR = Path("logs/llm_monitoring")
+
+LLM_CACHE_REPORT_KEYS = (
+    "generated_at",
+    "cache_path",
+    "entry_count",
+    "unique_tickers",
+    "unique_days",
+    "approved_count",
+    "rejected_count",
+    "estimated_cache_hit_rate",
+    "entries_per_ticker_day",
+    "top_tickers",
+)
+
+
+def _utc_now_iso() -> str:
+    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
+
+
+def load_llm_cache(cache_path: str | Path = DEFAULT_CACHE_PATH) -> dict[str, Any]:
+    path = Path(cache_path)
+    if not path.is_file():
+        return {}
+    try:
+        return json.loads(path.read_text(encoding="utf-8"))
+    except json.JSONDecodeError:
+        return {}
+
+
+def _parse_cache_key(cache_key: str) -> tuple[str, str]:
+    if "_" not in cache_key:
+        return cache_key, "unknown"
+    ticker, day = cache_key.rsplit("_", 1)
+    return ticker, day
+
+
+def summarize_llm_cache(cache: dict[str, Any]) -> dict[str, Any]:
+    if not cache:
+        return {
+            "generated_at": _utc_now_iso(),
+            "cache_path": str(DEFAULT_CACHE_PATH),
+            "entry_count": 0,
+            "unique_tickers": 0,
+            "unique_days": 0,
+            "approved_count": 0,
+            "rejected_count": 0,
+            "estimated_cache_hit_rate": 0.0,
+            "entries_per_ticker_day": 0.0,
+            "top_tickers": [],
+        }
+
+    tickers: list[str] = []
+    days: set[str] = set()
+    approved = 0
+    rejected = 0
+    ticker_counter: Counter[str] = Counter()
+
+    for key, payload in cache.items():
+        ticker, day = _parse_cache_key(str(key))
+        tickers.append(ticker)
+        days.add(day)
+        ticker_counter[ticker] += 1
+        if bool(payload.get("is_approved")):
+            approved += 1
+        else:
+            rejected += 1
+
+    entry_count = len(cache)
+    unique_tickers = len(set(tickers))
+    unique_days = len(days)
+    # One cache row per ticker-day when live runs once per day → reuse rate proxy.
+    possible_slots = max(unique_tickers * unique_days, 1)
+    hit_rate = round(min(entry_count / possible_slots, 1.0), 4)
+
+    return {
+        "generated_at": _utc_now_iso(),
+        "cache_path": str(DEFAULT_CACHE_PATH),
+        "entry_count": entry_count,
+        "unique_tickers": unique_tickers,
+        "unique_days": unique_days,
+        "approved_count": approved,
+        "rejected_count": rejected,
+        "estimated_cache_hit_rate": hit_rate,
+        "entries_per_ticker_day": round(entry_count / possible_slots, 4),
+        "top_tickers": [
+            {"ticker": ticker, "count": count}
+            for ticker, count in ticker_counter.most_common(10)
+        ],
+    }
+
+
+def validate_llm_cache_report(report: dict[str, Any]) -> dict[str, Any]:
+    for key in LLM_CACHE_REPORT_KEYS:
+        if key not in report:
+            raise ValueError(f"Missing LLM cache report key: {key}")
+    if report["entry_count"] < 0:
+        raise ValueError("entry_count must be non-negative")
+    return report
+
+
+def build_llm_cache_report(cache_path: str | Path = DEFAULT_CACHE_PATH) -> dict[str, Any]:
+    report = summarize_llm_cache(load_llm_cache(cache_path))
+    report["cache_path"] = str(cache_path)
+    return validate_llm_cache_report(report)
+
+
+def write_llm_cache_artifacts(
+    report: dict[str, Any],
+    output_dir: Path = DEFAULT_OUTPUT_DIR,
+) -> Path:
+    output_dir.mkdir(parents=True, exist_ok=True)
+    path = output_dir / "latest_summary.json"
+    path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
+    return path
+
+
+def run_llm_cache_report(
+    cache_path: str | Path = DEFAULT_CACHE_PATH,
+    output_dir: Path = DEFAULT_OUTPUT_DIR,
+) -> dict[str, Any]:
+    report = build_llm_cache_report(cache_path)
+    write_llm_cache_artifacts(report, output_dir)
+    return report
+
+
+def main() -> None:
+    parser = argparse.ArgumentParser(description="LLM cache monitoring report")
+    parser.add_argument("--cache-path", default=str(DEFAULT_CACHE_PATH))
+    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
+    args = parser.parse_args()
+    report = run_llm_cache_report(args.cache_path, Path(args.output_dir))
+    print(json.dumps(report, indent=2))
+
+
+if __name__ == "__main__":
+    main()
diff --git a/src/ml_model.py b/src/ml_model.py
index e0c664b..f220ffc 100644
--- a/src/ml_model.py
+++ b/src/ml_model.py
@@ -290,25 +290,149 @@ def restore_archived_champion(
     return model_path, metadata_path
 
 
+def bundle_to_model_wrapper(bundle: dict[str, Any]) -> RegimeAwareModelWrapper:
+    return RegimeAwareModelWrapper(
+        bundle["models"],
+        bundle["feature_columns"],
+        bundle["prediction_horizon"],
+        bundle["target_return_threshold"],
+    )
+
+
+def _portfolio_oos_rank_key(snapshot: dict[str, Any]) -> tuple[float, float, float]:
+    return (
+        float(snapshot["sharpe_ratio"]),
+        float(snapshot["total_return"]),
+        -abs(float(snapshot["max_drawdown"])),
+    )
+
+
+def portfolio_oos_beats_champion(
+    challenger: dict[str, Any],
+    champion: dict[str, Any],
+) -> bool:
+    """True when challenger ranks higher on Sharpe, then return, then drawdown."""
+    return _portfolio_oos_rank_key(challenger) > _portfolio_oos_rank_key(champion)
+
+
 def build_promotion_report(
     challenger_metadata: dict[str, Any],
     champion_metadata: dict[str, Any] | None,
+    *,
+    challenger_portfolio: dict[str, Any] | None = None,
+    champion_portfolio: dict[str, Any] | None = None,
+    portfolio_thresholds: Any | None = None,
+    require_portfolio_oos: bool = True,
+    fold_stability_report: dict[str, Any] | None = None,
+    calibration_report: dict[str, Any] | None = None,
+    require_ml_quality: bool = True,
+    ml_quality_criteria: Any | None = None,
 ) -> dict[str, Any]:
+    from src.ml_quality_report import evaluate_ml_quality_promotion_gates
+    from src.portfolio_backtest_validation import (
+        PortfolioBacktestThresholds,
+        check_portfolio_summary_thresholds,
+    )
+
+    thresholds = portfolio_thresholds or PortfolioBacktestThresholds()
     challenger_auc = float(challenger_metadata.get("oos_metrics", {}).get("avg_roc_auc", 0.0))
-    champion_auc = float(champion_metadata.get("oos_metrics", {}).get("avg_roc_auc", 0.0)) if champion_metadata else None
-    promote = champion_metadata is None or challenger_auc > champion_auc
-    return {
+    champion_auc = (
+        float(champion_metadata.get("oos_metrics", {}).get("avg_roc_auc", 0.0))
+        if champion_metadata
+        else None
+    )
+    auc_ok = champion_metadata is None or challenger_auc > champion_auc
+
+    ml_quality_eval = evaluate_ml_quality_promotion_gates(
+        challenger_metadata,
+        fold_stability_report,
+        calibration_report,
+        criteria=ml_quality_criteria,
+    )
+    ml_quality_ok = ml_quality_eval["passed"] if require_ml_quality else True
+
+    portfolio_gate = None
+    portfolio_gate_ok = True
+    portfolio_vs_ok = True
+
+    if require_portfolio_oos:
+        if challenger_portfolio is None:
+            portfolio_gate_ok = False
+            portfolio_vs_ok = False
+        else:
+            portfolio_gate = check_portfolio_summary_thresholds(
+                challenger_portfolio, thresholds
+            )
+            portfolio_gate_ok = portfolio_gate.passed
+
+            if champion_portfolio is None and champion_metadata is not None:
+                stored = champion_metadata.get("portfolio_oos")
+                if isinstance(stored, dict):
+                    champion_portfolio = stored
+
+            if champion_portfolio is not None:
+                portfolio_vs_ok = portfolio_oos_beats_champion(
+                    challenger_portfolio, champion_portfolio
+                )
+
+    promote = auc_ok and ml_quality_ok and portfolio_gate_ok and portfolio_vs_ok
+
+    reasons: list[str] = []
+    if champion_metadata is None:
+        reasons.append("no existing champion metadata")
+    elif not auc_ok:
+        reasons.append(
+            f"challenger_avg_roc_auc={challenger_auc:.4f} vs champion_avg_roc_auc={champion_auc:.4f}"
+        )
+    if require_ml_quality and not ml_quality_ok:
+        reasons.append("training metrics gates failed: " + "; ".join(ml_quality_eval["failures"]))
+    if require_portfolio_oos and challenger_portfolio is None:
+        reasons.append("missing challenger portfolio OOS evaluation")
+    elif require_portfolio_oos and portfolio_gate is not None and not portfolio_gate_ok:
+        reasons.append("portfolio gates failed: " + "; ".join(portfolio_gate.failures))
+    elif (
+        require_portfolio_oos
+        and champion_portfolio is not None
+        and challenger_portfolio is not None
+        and not portfolio_vs_ok
+    ):
+        c, h = challenger_portfolio, champion_portfolio
+        reasons.append(
+            "portfolio OOS did not beat champion "
+            f"(sharpe {float(c['sharpe_ratio']):.4f} vs {float(h['sharpe_ratio']):.4f}, "
+            f"return {float(c['total_return']):.4f} vs {float(h['total_return']):.4f})"
+        )
+
+    if promote:
+        reason = (
+            "no existing champion; challenger passes training metrics and portfolio OOS gates"
+            if champion_metadata is None
+            else "challenger passes AUC, training metrics, and portfolio OOS criteria"
+        )
+    else:
+        reason = "; ".join(reasons) if reasons else "challenger retained"
+
+    report: dict[str, Any] = {
         "generated_at": _utc_now_iso(),
         "champion_exists": champion_metadata is not None,
         "champion_avg_roc_auc": champion_auc,
         "challenger_avg_roc_auc": challenger_auc,
+        "auc_gate_passed": auc_ok,
+        "ml_quality_gate_passed": ml_quality_ok,
+        "ml_quality_gate_failures": ml_quality_eval.get("failures", []),
+        "portfolio_gate_passed": portfolio_gate_ok,
+        "portfolio_vs_champion_passed": portfolio_vs_ok,
         "decision": "PROMOTE" if promote else "RETAIN_CHAMPION",
-        "reason": (
-            "no existing champion metadata"
-            if champion_metadata is None
-            else f"challenger_avg_roc_auc={'{:.4f}'.format(challenger_auc)} vs champion_avg_roc_auc={'{:.4f}'.format(champion_auc)}"
-        ),
+        "reason": reason,
     }
+    if challenger_portfolio is not None:
+        report["challenger_portfolio_oos"] = challenger_portfolio
+    if champion_portfolio is not None:
+        report["champion_portfolio_oos"] = champion_portfolio
+    if portfolio_gate is not None:
+        report["portfolio_gate_failures"] = portfolio_gate.failures
+        report["portfolio_gate_warnings"] = portfolio_gate.warnings
+    return report
 
 
 def train_ai_score_model(
diff --git a/src/ml_quality_report.py b/src/ml_quality_report.py
new file mode 100644
index 0000000..3520c0d
--- /dev/null
+++ b/src/ml_quality_report.py
@@ -0,0 +1,497 @@
+"""Fold-level ROC-AUC stability and calibration report generation."""
+
+from __future__ import annotations
+
+import argparse
+import json
+from dataclasses import dataclass
+from datetime import datetime, timezone
+from pathlib import Path
+from typing import Any
+
+import pandas as pd
+from sklearn.metrics import brier_score_loss, roc_auc_score
+
+from src.features import FEATURE_COLUMNS, build_features
+from src.market_regime import compute_daily_regime
+
+FOLD_METRICS_COLUMNS: tuple[str, ...] = (
+    "regime",
+    "fold",
+    "roc_auc",
+    "brier_score",
+    "test_size",
+    "walk_forward_fold",
+    "walk_forward_period",
+)
+
+DEFAULT_ML_OUTPUT_DIR = Path("logs/ml")
+DEFAULT_VALIDATION_OUTPUT_DIR = Path("logs/validation")
+
+FOLD_METRICS_FILENAME = "fold_metrics.csv"
+FOLD_STABILITY_REPORT_FILENAME = "fold_stability_report.json"
+CALIBRATION_REPORT_FILENAME = "model_calibration_report.json"
+CALIBRATION_BINS_FILENAME = "model_calibration_bins.csv"
+
+# Flag when cross-fold / cross-regime ROC-AUC spread is large (see logs/ml/ai_model_metrics.csv history).
+ROC_AUC_STD_WARN_THRESHOLD = 0.05
+
+PROMOTION_MIN_AVG_ROC_AUC = 0.51
+PROMOTION_MAX_OVERALL_BRIER = 0.25
+
+CALIBRATION_REPORT_KEYS: tuple[str, ...] = (
+    "generated_at",
+    "overall_avg_brier_score",
+    "regimes",
+    "bin_count",
+)
+
+CALIBRATION_BINS_COLUMNS: tuple[str, ...] = (
+    "regime",
+    "prob_bin",
+    "count",
+    "avg_pred",
+    "actual_rate",
+)
+
+FOLD_STABILITY_REPORT_KEYS: tuple[str, ...] = (
+    "generated_at",
+    "fold_count",
+    "roc_auc",
+    "by_regime",
+    "high_variance_warning",
+    "roc_auc_std_warn_threshold",
+)
+
+
+@dataclass
+class MlQualityPromotionCriteria:
+    min_avg_roc_auc: float = PROMOTION_MIN_AVG_ROC_AUC
+    max_overall_brier: float = PROMOTION_MAX_OVERALL_BRIER
+    reject_high_fold_variance: bool = True
+
+
+def evaluate_ml_quality_promotion_gates(
+    challenger_metadata: dict[str, Any],
+    fold_stability_report: dict[str, Any] | None,
+    calibration_report: dict[str, Any] | None,
+    criteria: MlQualityPromotionCriteria | None = None,
+) -> dict[str, Any]:
+    """Training-time CV metrics + calibration must pass before champion promotion."""
+    criteria = criteria or MlQualityPromotionCriteria()
+    failures: list[str] = []
+
+    avg_auc = float(challenger_metadata.get("oos_metrics", {}).get("avg_roc_auc", 0.0))
+    if avg_auc < criteria.min_avg_roc_auc:
+        failures.append(
+            f"avg_roc_auc={avg_auc:.4f} < min {criteria.min_avg_roc_auc:.4f}"
+        )
+
+    if calibration_report is None:
+        failures.append("missing calibration report")
+    else:
+        brier = float(calibration_report.get("overall_avg_brier_score", 0.0))
+        if brier > criteria.max_overall_brier:
+            failures.append(
+                f"overall_avg_brier_score={brier:.4f} > max {criteria.max_overall_brier:.4f}"
+            )
+
+    if fold_stability_report is None:
+        failures.append("missing fold stability report")
+    elif criteria.reject_high_fold_variance and fold_stability_report.get(
+        "high_variance_warning"
+    ):
+        roc = fold_stability_report.get("roc_auc", {})
+        failures.append(
+            f"high fold ROC-AUC variance (std={roc.get('std')}, "
+            f"threshold={fold_stability_report.get('roc_auc_std_warn_threshold')})"
+        )
+
+    return {
+        "passed": not failures,
+        "failures": failures,
+        "avg_roc_auc": avg_auc,
+        "criteria": {
+            "min_avg_roc_auc": criteria.min_avg_roc_auc,
+            "max_overall_brier": criteria.max_overall_brier,
+            "reject_high_fold_variance": criteria.reject_high_fold_variance,
+        },
+    }
+
+
+def validate_fold_metrics_csv(path: str | Path) -> pd.DataFrame:
+    """Load fold_metrics.csv and enforce column schema ([AGY] regression helper)."""
+    frame = normalize_fold_metrics_df(pd.read_csv(path))
+    missing = [c for c in FOLD_METRICS_COLUMNS if c not in frame.columns]
+    if missing:
+        raise ValueError(f"fold_metrics missing columns: {missing}")
+    return frame
+
+
+def validate_calibration_artifacts(
+    report_path: str | Path,
+    bins_path: str | Path,
+) -> tuple[dict[str, Any], pd.DataFrame]:
+    """Validate calibration JSON keys and bins CSV schema."""
+    report_path = Path(report_path)
+    bins_path = Path(bins_path)
+    report = json.loads(report_path.read_text(encoding="utf-8"))
+    missing_keys = [k for k in CALIBRATION_REPORT_KEYS if k not in report]
+    if missing_keys:
+        raise ValueError(f"calibration report missing keys: {missing_keys}")
+
+    if not bins_path.is_file():
+        return report, pd.DataFrame(columns=list(CALIBRATION_BINS_COLUMNS))
+
+    bins_df = pd.read_csv(bins_path)
+    missing_cols = [c for c in CALIBRATION_BINS_COLUMNS if c not in bins_df.columns]
+    if missing_cols:
+        raise ValueError(f"calibration bins missing columns: {missing_cols}")
+    return report, bins_df
+
+
+def _utc_now_iso() -> str:
+    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
+
+
+def _filter_ticker_df_by_date(
+    df: pd.DataFrame,
+    start: pd.Timestamp,
+    end: pd.Timestamp | None = None,
+) -> pd.DataFrame:
+    if df is None or df.empty:
+        return df
+    frame = df.copy()
+    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
+    frame = frame[frame["date"] >= pd.Timestamp(start)]
+    if end is not None:
+        frame = frame[frame["date"] < pd.Timestamp(end)]
+    return frame.reset_index(drop=True)
+
+
+def evaluate_walk_forward_oos_metrics(
+    model,
+    ticker_data: dict[str, pd.DataFrame],
+    *,
+    test_start: pd.Timestamp,
+    test_end: pd.Timestamp,
+    vix_df: pd.DataFrame | None = None,
+    spy_df: pd.DataFrame | None = None,
+    macro_df: pd.DataFrame | None = None,
+    lookback_days: int = 400,
+) -> pd.DataFrame:
+    """ROC-AUC / Brier on the outer walk-forward test window (not inner training CV)."""
+    lookback_start = test_start - pd.DateOffset(days=lookback_days)
+    frames: list[pd.DataFrame] = []
+
+    for ticker, df in ticker_data.items():
+        window = _filter_ticker_df_by_date(df, lookback_start, test_end)
+        if len(window) < 50:
+            continue
+        try:
+            feature_df = build_features(
+                window,
+                prediction_horizon=model.prediction_horizon,
+                target_return_threshold=model.target_return_threshold,
+                vix_df=vix_df,
+                spy_df=spy_df,
+                macro_df=macro_df,
+            )
+        except ValueError:
+            continue
+        feature_df["ticker"] = ticker
+        frames.append(feature_df)
+
+    if not frames:
+        return pd.DataFrame(columns=list(FOLD_METRICS_COLUMNS))
+
+    dataset = pd.concat(frames, ignore_index=True).sort_values("date").reset_index(drop=True)
+    if spy_df is not None and vix_df is not None:
+        regime_series = compute_daily_regime(spy_df, vix_df)
+        dataset = dataset.merge(
+            regime_series.rename("regime"), left_on="date", right_index=True, how="left"
+        )
+        dataset["regime"] = dataset["regime"].fillna("NEUTRAL")
+    else:
+        dataset["regime"] = "NEUTRAL"
+
+    dataset["date"] = pd.to_datetime(dataset["date"], errors="coerce")
+    oos = dataset[
+        (dataset["date"] >= pd.Timestamp(test_start))
+        & (dataset["date"] < pd.Timestamp(test_end))
+    ]
+    if oos.empty:
+        return pd.DataFrame(columns=list(FOLD_METRICS_COLUMNS))
+
+    metrics: list[dict[str, Any]] = []
+    calibration_rows: list[dict[str, Any]] = []
+    for regime in ("BULL", "BEAR", "NEUTRAL"):
+        regime_model = model.models.get(regime)
+        if regime_model is None:
+            continue
+        regime_oos = oos[oos["regime"] == regime]
+        if len(regime_oos) < 30:
+            continue
+        available_cols = [c for c in model.feature_columns if c in regime_oos.columns]
+        x_test = regime_oos[available_cols]
+        y_test = regime_oos["target"]
+        proba = regime_model.predict_proba(x_test)[:, 1]
+        try:
+            auc = float(roc_auc_score(y_test, proba))
+        except ValueError:
+            auc = 0.5
+        brier = float(brier_score_loss(y_test, proba))
+        metrics.append(
+            {
+                "regime": regime,
+                "fold": 1,
+                "roc_auc": auc,
+                "brier_score": brier,
+                "test_size": int(len(regime_oos)),
+            }
+        )
+        calibration_rows.extend(
+            {
+                "regime": regime,
+                "fold": 1,
+                "y_true": int(y_true),
+                "y_prob": float(y_prob),
+            }
+            for y_true, y_prob in zip(y_test.tolist(), proba.tolist())
+        )
+
+    metrics_df = pd.DataFrame(metrics)
+    metrics_df.attrs["calibration_rows"] = calibration_rows
+    return metrics_df
+
+
+def normalize_fold_metrics_df(metrics_df: pd.DataFrame) -> pd.DataFrame:
+    """Ensure fold metrics CSV schema (missing optional columns filled with NA)."""
+    if metrics_df is None or metrics_df.empty:
+        return pd.DataFrame(columns=list(FOLD_METRICS_COLUMNS))
+
+    frame = metrics_df.copy()
+    for column in FOLD_METRICS_COLUMNS:
+        if column not in frame.columns:
+            frame[column] = pd.NA
+
+    ordered = [c for c in FOLD_METRICS_COLUMNS if c in frame.columns]
+    extra = [c for c in frame.columns if c not in FOLD_METRICS_COLUMNS]
+    return frame[ordered + extra]
+
+
+def _roc_auc_summary(series: pd.Series) -> dict[str, Any]:
+    values = pd.to_numeric(series, errors="coerce").dropna()
+    if values.empty:
+        return {
+            "count": 0,
+            "mean": None,
+            "std": None,
+            "min": None,
+            "max": None,
+            "range": None,
+        }
+    mean = float(values.mean())
+    std = float(values.std(ddof=0)) if len(values) > 1 else 0.0
+    min_v = float(values.min())
+    max_v = float(values.max())
+    return {
+        "count": int(len(values)),
+        "mean": mean,
+        "std": std,
+        "min": min_v,
+        "max": max_v,
+        "range": max_v - min_v,
+        "coefficient_of_variation": (std / mean) if mean else None,
+    }
+
+
+def build_fold_stability_report(metrics_df: pd.DataFrame) -> dict[str, Any]:
+    """Summarize ROC-AUC dispersion across CV / walk-forward folds."""
+    frame = normalize_fold_metrics_df(metrics_df)
+    if frame.empty or "roc_auc" not in frame.columns:
+        return {
+            "generated_at": _utc_now_iso(),
+            "fold_count": 0,
+            "roc_auc": _roc_auc_summary(pd.Series(dtype=float)),
+            "by_regime": {},
+            "high_variance_warning": False,
+            "message": "no fold metrics available",
+        }
+
+    overall = _roc_auc_summary(frame["roc_auc"])
+    by_regime: dict[str, Any] = {}
+    if "regime" in frame.columns:
+        for regime, regime_df in frame.groupby("regime", dropna=False):
+            by_regime[str(regime)] = _roc_auc_summary(regime_df["roc_auc"])
+
+    std = overall.get("std")
+    high_var = std is not None and std >= ROC_AUC_STD_WARN_THRESHOLD
+
+    walk_forward_summary = None
+    if "walk_forward_fold" in frame.columns and frame["walk_forward_fold"].notna().any():
+        wf = frame.dropna(subset=["walk_forward_fold"])
+        walk_forward_summary = _roc_auc_summary(wf["roc_auc"])
+
+    return {
+        "generated_at": _utc_now_iso(),
+        "fold_count": int(len(frame)),
+        "roc_auc": overall,
+        "by_regime": by_regime,
+        "walk_forward_roc_auc": walk_forward_summary,
+        "high_variance_warning": high_var,
+        "roc_auc_std_warn_threshold": ROC_AUC_STD_WARN_THRESHOLD,
+    }
+
+
+def build_calibration_report(metrics_df: pd.DataFrame) -> tuple[dict[str, Any], pd.DataFrame]:
+    calibration_rows = metrics_df.attrs.get("calibration_rows", []) if metrics_df is not None else []
+    calibration_df = pd.DataFrame(calibration_rows)
+    if calibration_df.empty:
+        return {
+            "generated_at": _utc_now_iso(),
+            "overall_avg_brier_score": 0.0,
+            "regimes": {},
+            "bin_count": 0,
+        }, pd.DataFrame()
+
+    regime_brier: dict[str, Any] = {}
+    if "brier_score" in metrics_df.columns and "regime" in metrics_df.columns:
+        for regime, regime_df in metrics_df.groupby("regime"):
+            regime_brier[str(regime)] = {
+                "avg_brier_score": float(regime_df["brier_score"].mean()),
+                "folds": int(len(regime_df)),
+            }
+
+    calibration_df["prob_bin"] = pd.cut(
+        calibration_df["y_prob"],
+        bins=[i / 10 for i in range(11)],
+        include_lowest=True,
+        duplicates="drop",
+    )
+    bin_rows = (
+        calibration_df.groupby(["regime", "prob_bin"], observed=False)
+        .agg(
+            count=("y_true", "size"),
+            avg_pred=("y_prob", "mean"),
+            actual_rate=("y_true", "mean"),
+        )
+        .reset_index()
+    )
+    bin_rows["prob_bin"] = bin_rows["prob_bin"].astype(str)
+
+    report = {
+        "generated_at": _utc_now_iso(),
+        "overall_avg_brier_score": (
+            float(metrics_df["brier_score"].mean()) if "brier_score" in metrics_df.columns else 0.0
+        ),
+        "regimes": regime_brier,
+        "bin_count": int(len(bin_rows)),
+    }
+    return report, bin_rows
+
+
+def write_ml_quality_reports(
+    output_dir: str | Path,
+    metrics_df: pd.DataFrame,
+    *,
+    file_prefix: str = "",
+) -> dict[str, Path]:
+    """Write fold metrics, stability JSON, and calibration artifacts."""
+    output_dir = Path(output_dir)
+    output_dir.mkdir(parents=True, exist_ok=True)
+
+    prefix = f"{file_prefix}_" if file_prefix else ""
+    fold_metrics_path = output_dir / f"{prefix}{FOLD_METRICS_FILENAME}"
+    stability_path = output_dir / f"{prefix}{FOLD_STABILITY_REPORT_FILENAME}"
+    calibration_path = output_dir / f"{prefix}{CALIBRATION_REPORT_FILENAME}"
+    bins_path = output_dir / f"{prefix}{CALIBRATION_BINS_FILENAME}"
+
+    fold_df = normalize_fold_metrics_df(metrics_df)
+    fold_df.to_csv(fold_metrics_path, index=False)
+
+    stability = build_fold_stability_report(metrics_df)
+    stability_path.write_text(
+        json.dumps(stability, indent=2, sort_keys=True),
+        encoding="utf-8",
+    )
+
+    calibration_report, bins_df = build_calibration_report(metrics_df)
+    calibration_path.write_text(
+        json.dumps(calibration_report, indent=2, sort_keys=True),
+        encoding="utf-8",
+    )
+    if not bins_df.empty:
+        bins_df.to_csv(bins_path, index=False)
+    elif bins_path.exists():
+        bins_path.unlink()
+
+    return {
+        "fold_metrics": fold_metrics_path,
+        "fold_stability": stability_path,
+        "calibration_report": calibration_path,
+        "calibration_bins": bins_path,
+    }
+
+
+def load_fold_metrics_csv(path: str | Path) -> pd.DataFrame:
+    return normalize_fold_metrics_df(pd.read_csv(path))
+
+
+def regenerate_reports_from_fold_metrics_csv(
+    metrics_path: str | Path,
+    output_dir: str | Path | None = None,
+    *,
+    file_prefix: str = "",
+) -> dict[str, Path]:
+    """Rebuild stability (and empty calibration) from saved fold_metrics.csv only."""
+    metrics_path = Path(metrics_path)
+    output_dir = Path(output_dir or metrics_path.parent)
+    metrics_df = load_fold_metrics_csv(metrics_path)
+    return write_ml_quality_reports(output_dir, metrics_df, file_prefix=file_prefix)
+
+
+def main() -> None:
+    parser = argparse.ArgumentParser(
+        description="Generate fold stability and calibration reports from fold metrics"
+    )
+    parser.add_argument(
+        "--metrics",
+        type=Path,
+        default=DEFAULT_ML_OUTPUT_DIR / "ai_model_metrics.csv",
+        help="Source metrics CSV (retrain legacy path) or fold_metrics.csv",
+    )
+    parser.add_argument(
+        "--output-dir",
+        type=Path,
+        default=None,
+        help="Output directory (default: parent of --metrics)",
+    )
+    parser.add_argument(
+        "--file-prefix",
+        default="",
+        help="Optional filename prefix (e.g. walk_forward)",
+    )
+    args = parser.parse_args()
+
+    output_dir = args.output_dir or args.metrics.parent
+    paths = regenerate_reports_from_fold_metrics_csv(
+        args.metrics,
+        output_dir,
+        file_prefix=args.file_prefix,
+    )
+    stability = json.loads(paths["fold_stability"].read_text(encoding="utf-8"))
+    print(f"Wrote fold metrics: {paths['fold_metrics']}")
+    print(f"Wrote fold stability: {paths['fold_stability']}")
+    print(f"Wrote calibration report: {paths['calibration_report']}")
+    if paths["calibration_bins"].is_file():
+        print(f"Wrote calibration bins: {paths['calibration_bins']}")
+    if stability.get("high_variance_warning"):
+        print(
+            f"WARNING: ROC-AUC std {stability['roc_auc']['std']:.4f} "
+            f">= threshold {ROC_AUC_STD_WARN_THRESHOLD}"
+        )
+
+
+if __name__ == "__main__":
+    main()
diff --git a/src/model_governance.py b/src/model_governance.py
new file mode 100644
index 0000000..68d4f8b
--- /dev/null
+++ b/src/model_governance.py
@@ -0,0 +1,121 @@
+"""Model promotion rollback helpers (no ML training deps)."""
+
+from __future__ import annotations
+
+from datetime import datetime, timezone
+from pathlib import Path
+
+import pandas as pd
+
+OOS_VALIDATION_PATH = Path("logs/validation/oos_validation.csv")
+BASELINE_SUMMARY_PATH = Path("logs/baselines/current_strategy/portfolio_summary.csv")
+
+ROLLBACK_MIN_TOTAL_RETURN = -0.05
+ROLLBACK_MIN_WIN_RATE = 0.35
+ROLLBACK_MAX_DRAWDOWN = -0.20
+
+
+def _restore_archived_champion(
+    archived_model_path: Path,
+    archived_metadata_path: Path,
+) -> tuple[Path, Path]:
+    from src.ml_model import restore_archived_champion
+
+    return restore_archived_champion(archived_model_path, archived_metadata_path)
+
+
+def load_recent_performance_snapshot() -> dict | None:
+    if OOS_VALIDATION_PATH.exists():
+        df = pd.read_csv(OOS_VALIDATION_PATH)
+        if not df.empty:
+            row = df.iloc[-1]
+            return {
+                "source": str(OOS_VALIDATION_PATH),
+                "total_return": float(row.get("total_return", 0.0)),
+                "max_drawdown": float(row.get("max_drawdown", 0.0)),
+                "win_rate": float(row.get("win_rate", 0.0)),
+            }
+
+    if BASELINE_SUMMARY_PATH.exists():
+        df = pd.read_csv(BASELINE_SUMMARY_PATH)
+        if not df.empty:
+            row = df.iloc[-1]
+            return {
+                "source": str(BASELINE_SUMMARY_PATH),
+                "total_return": float(row.get("total_return", 0.0)),
+                "max_drawdown": float(row.get("max_drawdown", 0.0)),
+                "win_rate": float(row.get("win_rate", 0.0)),
+            }
+
+    return None
+
+
+def evaluate_rollback_need(performance: dict | None) -> dict:
+    if performance is None:
+        return {
+            "should_rollback": False,
+            "reason": "no recent performance snapshot available",
+        }
+
+    breaches = []
+    if performance["total_return"] <= ROLLBACK_MIN_TOTAL_RETURN:
+        breaches.append(
+            f"total_return={performance['total_return']:.4f} <= {ROLLBACK_MIN_TOTAL_RETURN:.4f}"
+        )
+    if performance["win_rate"] <= ROLLBACK_MIN_WIN_RATE:
+        breaches.append(
+            f"win_rate={performance['win_rate']:.4f} <= {ROLLBACK_MIN_WIN_RATE:.4f}"
+        )
+    if performance["max_drawdown"] <= ROLLBACK_MAX_DRAWDOWN:
+        breaches.append(
+            f"max_drawdown={performance['max_drawdown']:.4f} <= {ROLLBACK_MAX_DRAWDOWN:.4f}"
+        )
+
+    return {
+        "should_rollback": bool(breaches),
+        "reason": "; ".join(breaches) if breaches else "performance within thresholds",
+        "performance": performance,
+        "thresholds": {
+            "min_total_return": ROLLBACK_MIN_TOTAL_RETURN,
+            "min_win_rate": ROLLBACK_MIN_WIN_RATE,
+            "max_drawdown": ROLLBACK_MAX_DRAWDOWN,
+        },
+    }
+
+
+def resolve_rollback_decision(
+    promotion_decision: str,
+    performance: dict | None,
+    archived_champion: tuple[Path, Path] | None,
+    *,
+    restore: bool = True,
+) -> dict:
+    """Build rollback report payload from promotion outcome and live performance snapshot."""
+    rollback_report: dict = {
+        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
+        "promotion_decision": promotion_decision,
+    }
+    if promotion_decision == "PROMOTE":
+        rollback_report["decision"] = "SKIP_ROLLBACK_AFTER_PROMOTION"
+        rollback_report["reason"] = (
+            "new challenger promoted; wait for fresh performance before rollback evaluation"
+        )
+        return rollback_report
+
+    rollback_eval = evaluate_rollback_need(performance)
+    rollback_report.update(rollback_eval)
+    if not rollback_eval["should_rollback"]:
+        rollback_report["decision"] = "NO_ROLLBACK_NEEDED"
+        return rollback_report
+
+    if archived_champion is None:
+        rollback_report["decision"] = "NO_ROLLBACK_AVAILABLE"
+        rollback_report["reason"] = f"{rollback_eval['reason']}; no archived champion available"
+        return rollback_report
+
+    if restore:
+        _restore_archived_champion(*archived_champion)
+    rollback_report["decision"] = "ROLLBACK_TO_ARCHIVED_CHAMPION"
+    rollback_report["restored_model_path"] = str(archived_champion[0])
+    rollback_report["restored_metadata_path"] = str(archived_champion[1])
+    return rollback_report
diff --git a/src/portfolio_backtest_validation.py b/src/portfolio_backtest_validation.py
new file mode 100644
index 0000000..7d6d539
--- /dev/null
+++ b/src/portfolio_backtest_validation.py
@@ -0,0 +1,236 @@
+"""Validate portfolio backtest CSV outputs (schema + optional golden metrics)."""
+
+from __future__ import annotations
+
+from dataclasses import dataclass
+from pathlib import Path
+from typing import Any
+
+import pandas as pd
+
+SUMMARY_COLUMNS = (
+    "initial_cash",
+    "final_equity",
+    "total_return",
+    "benchmark_return",
+    "max_drawdown",
+    "sharpe_ratio",
+    "trades",
+    "win_rate",
+)
+
+EQUITY_COLUMNS = (
+    "date",
+    "cash",
+    "positions_value",
+    "equity",
+    "positions_count",
+    "open_symbols",
+    "daily_return",
+    "running_max",
+    "drawdown",
+    "benchmark_equity",
+)
+
+TRADES_COLUMNS = (
+    "ticker",
+    "entry_date",
+    "exit_date",
+    "entry_price",
+    "exit_price",
+    "qty",
+    "cost_basis",
+    "exit_value",
+    "return_pct",
+    "exit_reason",
+)
+
+SUMMARY_METRIC_KEYS = (
+    "initial_cash",
+    "final_equity",
+    "total_return",
+    "benchmark_return",
+    "max_drawdown",
+    "sharpe_ratio",
+    "trades",
+    "win_rate",
+)
+
+
+def _require_columns(df: pd.DataFrame, required: tuple[str, ...], label: str) -> None:
+    missing = [c for c in required if c not in df.columns]
+    if missing:
+        raise ValueError(f"{label}: missing columns {missing}")
+
+
+def load_summary_row(path: Path) -> dict[str, Any]:
+    df = pd.read_csv(path)
+    if df.empty:
+        raise ValueError(f"{path}: summary is empty")
+    _require_columns(df, SUMMARY_COLUMNS, "portfolio_summary")
+    row = df.iloc[0]
+    out: dict[str, Any] = {}
+    for key in SUMMARY_METRIC_KEYS:
+        val = row[key]
+        if key == "trades":
+            out[key] = int(val)
+        elif key in ("initial_cash", "final_equity"):
+            out[key] = float(val)
+        else:
+            out[key] = float(val)
+    return out
+
+
+def validate_portfolio_backtest_dir(
+    output_dir: str | Path,
+    *,
+    golden_summary: dict[str, Any] | None = None,
+    summary_rtol: float = 1e-4,
+    summary_atol: float = 1e-6,
+    min_equity_rows: int = 2,
+    min_trades_rows: int = 0,
+) -> dict[str, Any]:
+    """Validate the three portfolio backtest CSVs under ``output_dir``."""
+    output_dir = Path(output_dir)
+    summary_path = output_dir / "portfolio_summary.csv"
+    equity_path = output_dir / "portfolio_equity.csv"
+    trades_path = output_dir / "portfolio_trades.csv"
+
+    for path in (summary_path, equity_path, trades_path):
+        if not path.is_file():
+            raise FileNotFoundError(f"Missing portfolio backtest artifact: {path}")
+
+    summary = load_summary_row(summary_path)
+
+    equity_df = pd.read_csv(equity_path)
+    _require_columns(equity_df, EQUITY_COLUMNS, "portfolio_equity")
+    if len(equity_df) < min_equity_rows:
+        raise ValueError(
+            f"portfolio_equity: expected at least {min_equity_rows} rows, got {len(equity_df)}"
+        )
+    if equity_df["equity"].isna().any():
+        raise ValueError("portfolio_equity: NaN in equity column")
+
+    trades_df = pd.read_csv(trades_path)
+    _require_columns(trades_df, TRADES_COLUMNS, "portfolio_trades")
+    if len(trades_df) < min_trades_rows:
+        raise ValueError(
+            f"portfolio_trades: expected at least {min_trades_rows} rows, got {len(trades_df)}"
+        )
+
+    if int(summary["trades"]) != len(trades_df):
+        raise ValueError(
+            f"summary trades={summary['trades']} != trades rows={len(trades_df)}"
+        )
+
+    if golden_summary is not None:
+        import numpy as np
+
+        for key in SUMMARY_METRIC_KEYS:
+            if key not in golden_summary:
+                raise KeyError(f"golden_summary missing key: {key}")
+            expected = golden_summary[key]
+            actual = summary[key]
+            if key == "trades":
+                if int(actual) != int(expected):
+                    raise AssertionError(
+                        f"{key}: expected {expected}, got {actual}"
+                    )
+            elif not np.isclose(actual, float(expected), rtol=summary_rtol, atol=summary_atol):
+                raise AssertionError(
+                    f"{key}: expected {expected}, got {actual}"
+                )
+
+    return {
+        "summary": summary,
+        "equity_rows": len(equity_df),
+        "trades_rows": len(trades_df),
+    }
+
+
+@dataclass
+class PortfolioBacktestThresholds:
+    """OOS / CI gates on portfolio_summary.csv (not golden fixture regression)."""
+
+    max_drawdown_floor: float = -0.20
+    min_return_vs_benchmark: float = -0.15
+    min_sharpe: float | None = None
+
+
+@dataclass
+class PortfolioBacktestThresholdResult:
+    summary: dict[str, Any]
+    passed: bool
+    failures: list[str]
+    warnings: list[str]
+
+
+def _apply_portfolio_thresholds_to_summary(
+    summary: dict[str, Any],
+    thresholds: PortfolioBacktestThresholds,
+) -> tuple[list[str], list[str]]:
+    failures: list[str] = []
+    warnings: list[str] = []
+
+    max_dd = float(summary["max_drawdown"])
+    if max_dd < thresholds.max_drawdown_floor:
+        failures.append(
+            f"max_drawdown {max_dd:.4f} worse than floor {thresholds.max_drawdown_floor:.4f}"
+        )
+
+    excess_vs_bench = float(summary["total_return"]) - float(summary["benchmark_return"])
+    if excess_vs_bench < thresholds.min_return_vs_benchmark:
+        failures.append(
+            f"total_return - benchmark_return = {excess_vs_bench:.4f} "
+            f"< min {thresholds.min_return_vs_benchmark:.4f}"
+        )
+    elif excess_vs_bench < 0:
+        warnings.append(
+            f"underperforms benchmark by {-excess_vs_bench:.4f} (within allowed gap)"
+        )
+
+    if thresholds.min_sharpe is not None:
+        sharpe = float(summary["sharpe_ratio"])
+        if sharpe < thresholds.min_sharpe:
+            failures.append(f"sharpe_ratio {sharpe:.4f} < min {thresholds.min_sharpe:.4f}")
+
+    return failures, warnings
+
+
+def check_portfolio_summary_thresholds(
+    summary: dict[str, Any],
+    thresholds: PortfolioBacktestThresholds | None = None,
+) -> PortfolioBacktestThresholdResult:
+    """Apply portfolio-level gates to an in-memory summary row (retrain promotion)."""
+    thresholds = thresholds or PortfolioBacktestThresholds()
+    failures, warnings = _apply_portfolio_thresholds_to_summary(summary, thresholds)
+    return PortfolioBacktestThresholdResult(
+        summary=summary,
+        passed=not failures,
+        failures=failures,
+        warnings=warnings,
+    )
+
+
+def check_portfolio_backtest_thresholds(
+    output_dir: str | Path,
+    thresholds: PortfolioBacktestThresholds | None = None,
+    *,
+    validate_schema: bool = True,
+) -> PortfolioBacktestThresholdResult:
+    """Apply portfolio-level gates after schema validation."""
+    thresholds = thresholds or PortfolioBacktestThresholds()
+
+    if validate_schema:
+        result = validate_portfolio_backtest_dir(output_dir, min_equity_rows=2)
+        summary = result["summary"]
+    else:
+        summary = load_summary_row(Path(output_dir) / "portfolio_summary.csv")
+
+    failures, warnings = _apply_portfolio_thresholds_to_summary(summary, thresholds)
+    return PortfolioBacktestThresholdResult(
+        summary=summary,
+        passed=not failures,
+        failures=failures,
+        warnings=warnings,
+    )
diff --git a/src/portfolio_backtester.py b/src/portfolio_backtester.py
index db63ceb..e155522 100644
--- a/src/portfolio_backtester.py
+++ b/src/portfolio_backtester.py
@@ -9,6 +9,7 @@ from src.strategy import add_indicators, build_market_regime_frame
 from src.features import FEATURE_COLUMNS, build_features
 from src.ml_model import load_ai_score_model
 from src.portfolio_optimizer import compute_candidate_weights
+from src.risk_manager import apply_factor_crowding_limits
 
 
 @dataclass
@@ -260,6 +261,7 @@ def run_portfolio_backtest(
     macro_df: pd.DataFrame | None = None,
     evaluation_start_date: str | pd.Timestamp | None = None,
     evaluation_end_date: str | pd.Timestamp | None = None,
+    crowding_guard_enabled: bool = False,
 ) -> tuple[PortfolioBacktestResult, pd.DataFrame, pd.DataFrame]:
     if relative_strength_lookback_days <= 0:
         raise ValueError("relative_strength_lookback_days must be positive")
@@ -532,6 +534,15 @@ def run_portfolio_backtest(
                 if close <= 0:
                     continue
 
+                if crowding_guard_enabled:
+                    crowding = apply_factor_crowding_limits(
+                        ticker=ticker,
+                        open_symbols=set(positions.keys()),
+                        ticker_data=ticker_data,
+                    )
+                    if not crowding.allowed:
+                        continue
+
                 if total_to_deploy is not None:
                     target_value = total_to_deploy * alloc_weights.get(
                         ticker, 1.0 / len(candidate_tickers)
diff --git a/src/report_performance.py b/src/report_performance.py
index 2ebc588..e67e555 100644
--- a/src/report_performance.py
+++ b/src/report_performance.py
@@ -1,113 +1,325 @@
-"""실제 거래 내역과 백테스트 결과를 비교 분석하는 스크립트."""
+"""실제 거래 내역과 시그널 가격을 비교해 paper 슬리피지를 분석·리포트한다."""
+
+from __future__ import annotations
+
+import argparse
+import json
+from dataclasses import asdict, dataclass
+from datetime import datetime, timedelta, timezone
+from pathlib import Path
 
-import pandas as pd
 import numpy as np
-from datetime import datetime, timedelta
+import pandas as pd
+
 from src.alpaca_client import get_account_summary, get_positions_summary
-from src.config import SIGNAL_LOG_PATH, ORDER_LOG_PATH
-
-
-def analyze_slippage(signals_path=None, orders_path=None):
-    """signals log와 orders log를 결합하여 슬리피지를 분석한다."""
-    
-    # 인자가 제공되지 않으면 기본 경로 사용
-    if signals_path is None:
-        signals_path = SIGNAL_LOG_PATH
-    if orders_path is None:
-        orders_path = ORDER_LOG_PATH
-        
-    try:
-        signals_df = pd.read_csv(signals_path)
-        orders_df = pd.read_csv(orders_path)
-    except FileNotFoundError:
-        print("Log files not found.")
-        return
+from src.config import ORDER_LOG_PATH, SIGNAL_LOG_PATH
 
-    # 주문 체결 내역만 필터링 (기존 로그의 컬럼 밀림 현상 대응)
-    # 1. 'event' 컬럼에서 확인
+
+@dataclass
+class SlippageReport:
+    generated_at: str
+    lookback_days: int
+    signals_path: str
+    orders_path: str
+    matched_trades: int
+    overall_avg_slippage_pct: float
+    total_slippage_usd: float
+    by_ticker: list[dict]
+    status: str = "ok"
+    message: str | None = None
+
+    def to_dict(self) -> dict:
+        return asdict(self)
+
+
+def _utc_now_iso() -> str:
+    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
+
+
+def _filter_since(df: pd.DataFrame, since: datetime | None, column: str = "timestamp") -> pd.DataFrame:
+    if since is None or df.empty or column not in df.columns:
+        return df
+    frame = df.copy()
+    frame["_ts"] = pd.to_datetime(frame[column], utc=True, errors="coerce")
+    cutoff = pd.Timestamp(since).tz_convert("UTC") if pd.Timestamp(since).tzinfo else pd.Timestamp(since, tz="UTC")
+    return frame[frame["_ts"] >= cutoff].drop(columns=["_ts"])
+
+
+def _extract_filled_orders(orders_df: pd.DataFrame) -> pd.DataFrame:
     filled_orders = orders_df[orders_df.get("event") == "STATUS_CHECK"].copy()
-    
-    # 2. 만약 비어있다면, 다른 컬럼에 밀려있는지 확인 (예: filled_avg_price 컬럼에 STATUS_CHECK이 있는 경우)
+
     if filled_orders.empty:
-        # 마지막 컬럼들 중 'STATUS_CHECK'이 포함된 행 찾기
         mask = orders_df.apply(lambda row: "STATUS_CHECK" in row.values, axis=1)
         filled_orders = orders_df[mask].copy()
-        
-        # 컬럼 재매핑 (데이터 위치에 맞게)
-        # 필터링된 행들에 대해 'STATUS_CHECK'이 위치한 인덱스를 기준으로 재배치
-        def remap_row(row):
+
+        def remap_row(row: pd.Series) -> pd.Series:
             vals = list(row)
             if "STATUS_CHECK" in vals:
                 idx = vals.index("STATUS_CHECK")
-                # STATUS_CHECK이 마지막(10번 인덱스)에 있다고 가정하고 밀린 경우 대응
-                # timestamp, ticker, notional, order_id, status, side, order_type, filled_qty, filled_avg_price, reason, event
                 if idx == 10:
-                    return pd.Series([vals[0], vals[1], vals[2], vals[3], vals[4], vals[5], vals[6], vals[7], vals[8], vals[9], vals[10]],
-                                   index=["timestamp", "ticker", "notional", "order_id", "status", "side", "order_type", "filled_qty", "filled_avg_price", "reason", "event"])
+                    return pd.Series(
+                        [
+                            vals[0],
+                            vals[1],
+                            vals[2],
+                            vals[3],
+                            vals[4],
+                            vals[5],
+                            vals[6],
+                            vals[7],
+                            vals[8],
+                            vals[9],
+                            vals[10],
+                        ],
+                        index=[
+                            "timestamp",
+                            "ticker",
+                            "notional",
+                            "order_id",
+                            "status",
+                            "side",
+                            "order_type",
+                            "filled_qty",
+                            "filled_avg_price",
+                            "reason",
+                            "event",
+                        ],
+                    )
             return row
 
         if not filled_orders.empty:
             filled_orders = filled_orders.apply(remap_row, axis=1)
 
     if filled_orders.empty:
-        print("No filled orders found in log.")
-        return
+        return filled_orders
+
+    filled_orders["filled_avg_price"] = pd.to_numeric(
+        filled_orders["filled_avg_price"], errors="coerce"
+    )
+    return filled_orders.dropna(subset=["filled_avg_price"])
+
+
+def compute_slippage_report(
+    signals_path: str | Path | None = None,
+    orders_path: str | Path | None = None,
+    *,
+    lookback_days: int | None = None,
+    since: datetime | None = None,
+) -> SlippageReport | None:
+    """Match paper fills to signal close prices and compute slippage metrics."""
+    signals_path = Path(signals_path or SIGNAL_LOG_PATH)
+    orders_path = Path(orders_path or ORDER_LOG_PATH)
+
+    if since is None and lookback_days is not None:
+        since = datetime.now(timezone.utc) - timedelta(days=lookback_days)
+
+    try:
+        signals_df = pd.read_csv(signals_path)
+        orders_df = pd.read_csv(orders_path)
+    except FileNotFoundError:
+        return None
 
-    # 숫자형 변환
-    filled_orders["filled_avg_price"] = pd.to_numeric(filled_orders["filled_avg_price"], errors="coerce")
-    filled_orders = filled_orders.dropna(subset=["filled_avg_price"])
+    signals_df = _filter_since(signals_df, since)
+    orders_df = _filter_since(orders_df, since)
 
+    filled_orders = _extract_filled_orders(orders_df)
+    if filled_orders.empty:
+        return None
 
-    # Timestamp 변환 (초 단위 절삭하여 매칭 확률 높임)
-    signals_df["ts_short"] = pd.to_datetime(signals_df["timestamp"]).dt.floor("min")
-    filled_orders["ts_short"] = pd.to_datetime(filled_orders["timestamp"]).dt.floor("min")
+    signals_df["ts_short"] = pd.to_datetime(signals_df["timestamp"], utc=True).dt.floor("min")
+    filled_orders["ts_short"] = pd.to_datetime(filled_orders["timestamp"], utc=True).dt.floor("min")
 
-    # Ticker와 유사 시간대로 Join
     merged = pd.merge(
         filled_orders,
         signals_df,
         on=["ticker", "ts_short"],
         how="inner",
-        suffixes=("_order", "_signal")
+        suffixes=("_order", "_signal"),
     )
-
     if merged.empty:
-        print("Could not match orders with signals for slippage analysis.")
-        # 시간을 좀 더 넓게 잡아보자 (5분 내외)
-        return
+        return None
 
     merged["side_lower"] = merged["side"].astype(str).str.lower()
-    # Handle both plain "sell" and Enum string representation "orderside.sell"
     sign = np.where(merged["side_lower"].str.contains("sell", na=False), -1, 1)
-
-    merged["slippage_pct"] = sign * (merged["filled_avg_price"] - merged["close"]) / merged["close"] * 100
-
-    # 슬리피지 USD 비용 계산
+    merged["slippage_pct"] = (
+        sign * (merged["filled_avg_price"] - merged["close"]) / merged["close"] * 100
+    )
     merged["filled_qty"] = pd.to_numeric(merged["filled_qty"], errors="coerce")
-    merged["slippage_usd"] = sign * (merged["filled_avg_price"] - merged["close"]) * merged["filled_qty"]
-    
-    # BUY는 높은 가격에 체결되면 슬리피지 발생 (+), SELL은 낮은 가격에 체결되면 발생 (+)
-    # 편의상 절대값이나 방향성을 고려해 출력
-    print("\n=== Slippage Analysis (Actual vs Signal Price) ===")
-    summary = merged.groupby("ticker").agg(
+    merged["slippage_usd"] = (
+        sign * (merged["filled_avg_price"] - merged["close"]) * merged["filled_qty"]
+    )
+
+    by_ticker_df = merged.groupby("ticker").agg(
         avg_slippage_pct=("slippage_pct", "mean"),
         total_slippage_usd=("slippage_usd", "sum"),
-        trades=("ticker", "count")
+        trades=("ticker", "count"),
     )
-    print(summary.to_string())
-    print(f"\nOverall Average Slippage: {merged['slippage_pct'].mean():.4f}%")
-    print(f"Total Slippage Cost: ${merged['slippage_usd'].sum():.2f}")
+    by_ticker = [
+        {
+            "ticker": str(ticker),
+            "avg_slippage_pct": float(row["avg_slippage_pct"]),
+            "total_slippage_usd": float(row["total_slippage_usd"]),
+            "trades": int(row["trades"]),
+        }
+        for ticker, row in by_ticker_df.iterrows()
+    ]
 
+    return SlippageReport(
+        generated_at=_utc_now_iso(),
+        lookback_days=int(lookback_days or 0),
+        signals_path=str(signals_path),
+        orders_path=str(orders_path),
+        matched_trades=int(len(merged)),
+        overall_avg_slippage_pct=float(merged["slippage_pct"].mean()),
+        total_slippage_usd=float(merged["slippage_usd"].sum()),
+        by_ticker=by_ticker,
+    )
 
-def report_account_performance():
-    """Alpaca 계좌의 현재 실적 요약."""
+
+def format_slippage_report(report: SlippageReport) -> str:
+    lines = [
+        "",
+        "=== Slippage Analysis (Paper Fill vs Signal Price) ===",
+        f"Window: last {report.lookback_days} day(s)" if report.lookback_days else "Window: all logs",
+        f"Status: {report.status}",
+        f"Matched trades: {report.matched_trades}",
+    ]
+    if report.message:
+        lines.append(f"Note: {report.message}")
+    if report.by_ticker:
+        summary = pd.DataFrame(report.by_ticker).set_index("ticker")
+        lines.append(summary.to_string())
+    lines.append(f"\nOverall Average Slippage: {report.overall_avg_slippage_pct:.4f}%")
+    lines.append(f"Total Slippage Cost: ${report.total_slippage_usd:.2f}")
+    return "\n".join(lines)
+
+
+def write_slippage_artifacts(
+    report: SlippageReport,
+    output_dir: str | Path,
+    *,
+    run_id: str | None = None,
+) -> Path:
+    output_dir = Path(output_dir)
+    output_dir.mkdir(parents=True, exist_ok=True)
+    stamp = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
+    run_dir = output_dir / f"slippage_{stamp}"
+    run_dir.mkdir(parents=True, exist_ok=True)
+
+    (run_dir / "summary.json").write_text(
+        json.dumps(report.to_dict(), indent=2, sort_keys=True),
+        encoding="utf-8",
+    )
+    if report.by_ticker:
+        pd.DataFrame(report.by_ticker).to_csv(run_dir / "by_ticker.csv", index=False)
+
+    latest = output_dir / "latest_summary.json"
+    latest.write_text(
+        json.dumps(report.to_dict(), indent=2, sort_keys=True),
+        encoding="utf-8",
+    )
+    return run_dir
+
+
+def analyze_slippage(
+    signals_path: str | Path | None = None,
+    orders_path: str | Path | None = None,
+    *,
+    lookback_days: int | None = None,
+) -> SlippageReport | None:
+    report = compute_slippage_report(
+        signals_path=signals_path,
+        orders_path=orders_path,
+        lookback_days=lookback_days,
+    )
+    if report is None:
+        print("No slippage data available (missing logs, fills, or signal matches).")
+        return None
+    print(format_slippage_report(report))
+    return report
+
+
+def _maybe_notify_slippage(report: SlippageReport) -> None:
+    try:
+        from src.notifier import notify_info
+    except ImportError:
+        return
+    notify_info(
+        "Weekly paper vs signal slippage",
+        (
+            f"Matched trades: {report.matched_trades}\n"
+            f"Avg slippage: {report.overall_avg_slippage_pct:.4f}%\n"
+            f"Total cost: ${report.total_slippage_usd:.2f}"
+        ),
+    )
+
+
+def _empty_slippage_report(
+    *,
+    lookback_days: int,
+    signals_path: Path,
+    orders_path: Path,
+    message: str,
+) -> SlippageReport:
+    return SlippageReport(
+        generated_at=_utc_now_iso(),
+        lookback_days=lookback_days,
+        signals_path=str(signals_path),
+        orders_path=str(orders_path),
+        matched_trades=0,
+        overall_avg_slippage_pct=0.0,
+        total_slippage_usd=0.0,
+        by_ticker=[],
+        status="no_data",
+        message=message,
+    )
+
+
+def run_weekly_slippage_report(
+    *,
+    lookback_days: int = 7,
+    output_dir: str | Path = "logs/slippage_reports",
+    signals_path: str | Path | None = None,
+    orders_path: str | Path | None = None,
+    notify_telegram: bool = False,
+    include_account: bool = False,
+) -> SlippageReport:
+    signals_path = Path(signals_path or SIGNAL_LOG_PATH)
+    orders_path = Path(orders_path or ORDER_LOG_PATH)
+
+    report = compute_slippage_report(
+        signals_path=signals_path,
+        orders_path=orders_path,
+        lookback_days=lookback_days,
+    )
+    if report is None:
+        report = _empty_slippage_report(
+            lookback_days=lookback_days,
+            signals_path=signals_path,
+            orders_path=orders_path,
+            message="no matched paper fills in lookback window",
+        )
+        print(f"Weekly slippage report: {report.message}.")
+
+    run_dir = write_slippage_artifacts(report, output_dir)
+    print(format_slippage_report(report))
+    print(f"\nSaved weekly slippage report to {run_dir}")
+    if notify_telegram:
+        _maybe_notify_slippage(report)
+    if include_account:
+        report_account_performance()
+    return report
+
+
+def report_account_performance() -> None:
+    """Alpaca paper 계좌의 현재 실적 요약."""
     account = get_account_summary()
     positions = get_positions_summary()
-    
+
     print("\n=== Account Performance Summary ===")
     print(f"Portfolio Value: ${account['portfolio_value']:.2f}")
     print(f"Cash: ${account['cash']:.2f}")
-    
+
     if positions:
         print("\n--- Open Positions ---")
         pos_df = pd.DataFrame(positions)
@@ -116,10 +328,67 @@ def report_account_performance():
         print("\nNo open positions.")
 
 
-def main():
+def _load_slippage_config() -> dict:
+    path = Path("config/slippage_report_config.json")
+    if not path.is_file():
+        return {}
+    return json.loads(path.read_text(encoding="utf-8"))
+
+
+def main() -> None:
+    config = _load_slippage_config()
+    parser = argparse.ArgumentParser(description="Paper vs signal slippage reporting")
+    parser.add_argument(
+        "--weekly",
+        action="store_true",
+        help="Run weekly lookback, write artifacts under output_dir",
+    )
+    parser.add_argument(
+        "--days",
+        type=int,
+        default=int(config.get("lookback_days", 7)),
+        help="Lookback window in days (default from config or 7)",
+    )
+    parser.add_argument(
+        "--output-dir",
+        default=str(config.get("output_dir", "logs/slippage_reports")),
+        help="Directory for JSON/CSV weekly artifacts",
+    )
+    parser.add_argument(
+        "--telegram",
+        action="store_true",
+        default=bool(config.get("notify_telegram", False)),
+        help="Send Telegram summary when configured",
+    )
+    parser.add_argument(
+        "--account",
+        action="store_true",
+        help="Include Alpaca account summary",
+    )
+    parser.add_argument("--signals", default=None, help="Override signals CSV path")
+    parser.add_argument("--orders", default=None, help="Override orders CSV path")
+    args = parser.parse_args()
+
     print(f"Performance Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
-    report_account_performance()
-    analyze_slippage()
+
+    if args.weekly:
+        run_weekly_slippage_report(
+            lookback_days=args.days,
+            output_dir=args.output_dir,
+            signals_path=args.signals,
+            orders_path=args.orders,
+            notify_telegram=args.telegram,
+            include_account=args.account,
+        )
+        return
+
+    if args.account:
+        report_account_performance()
+    analyze_slippage(
+        signals_path=args.signals,
+        orders_path=args.orders,
+        lookback_days=args.days if args.days > 0 else None,
+    )
 
 
 if __name__ == "__main__":
diff --git a/src/retrain_holdout.py b/src/retrain_holdout.py
new file mode 100644
index 0000000..0b4683d
--- /dev/null
+++ b/src/retrain_holdout.py
@@ -0,0 +1,60 @@
+"""Holdout window helpers for retrain portfolio promotion (no ML deps)."""
+
+from __future__ import annotations
+
+import pandas as pd
+
+PORTFOLIO_HOLDOUT_MONTHS = 6
+
+
+def portfolio_holdout_window(
+    ticker_data: dict[str, pd.DataFrame],
+    *,
+    months: int = PORTFOLIO_HOLDOUT_MONTHS,
+) -> tuple[pd.Timestamp, pd.Timestamp]:
+    latest_dates = []
+    for df in ticker_data.values():
+        if df is None or df.empty or "date" not in df.columns:
+            continue
+        series = pd.to_datetime(df["date"], errors="coerce").dropna()
+        if not series.empty:
+            latest_dates.append(series.max())
+    if not latest_dates:
+        raise ValueError("No valid dates found in ticker_data")
+    eval_end = max(latest_dates)
+    eval_start = eval_end - pd.DateOffset(months=months)
+    return eval_start, eval_end
+
+
+def exclude_holdout_from_ticker_data(
+    ticker_data: dict[str, pd.DataFrame],
+    holdout_start: pd.Timestamp,
+) -> dict[str, pd.DataFrame]:
+    """Rows with date >= holdout_start are removed (challenger training set)."""
+    out: dict[str, pd.DataFrame] = {}
+    for ticker, df in ticker_data.items():
+        if df is None or df.empty or "date" not in df.columns:
+            continue
+        frame = df.copy()
+        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
+        out[ticker] = frame[frame["date"] < holdout_start].reset_index(drop=True)
+    return out
+
+
+def slice_ticker_data_to_holdout(
+    ticker_data: dict[str, pd.DataFrame],
+    holdout_start: pd.Timestamp,
+    holdout_end: pd.Timestamp,
+) -> dict[str, pd.DataFrame]:
+    """Rows within [holdout_start, holdout_end] for portfolio OOS scoring."""
+    out: dict[str, pd.DataFrame] = {}
+    for ticker, df in ticker_data.items():
+        if df is None or df.empty or "date" not in df.columns:
+            continue
+        frame = df.copy()
+        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
+        mask = (frame["date"] >= holdout_start) & (frame["date"] <= holdout_end)
+        sliced = frame.loc[mask].reset_index(drop=True)
+        if not sliced.empty:
+            out[ticker] = sliced
+    return out
diff --git a/src/retrain_notifications.py b/src/retrain_notifications.py
new file mode 100644
index 0000000..e6192fe
--- /dev/null
+++ b/src/retrain_notifications.py
@@ -0,0 +1,41 @@
+"""Telegram and log hooks for retrain success, partial success, and failure."""
+
+from __future__ import annotations
+
+from pathlib import Path
+from typing import Callable
+
+from src.notifier import notify_error, notify_info
+
+AppendRetrainLogFn = Callable[[str, object, float], None]
+
+
+def notify_champion_retained_if_needed(promotion_report: dict, report_path: Path) -> None:
+    if promotion_report.get("decision") == "PROMOTE":
+        return
+    notify_info(
+        "ℹ️ Retrain finished; champion retained",
+        f"Decision: {promotion_report.get('decision')}\n"
+        f"Promotion report: {report_path}",
+    )
+
+
+def notify_retrain_failure(
+    exc: Exception,
+    elapsed_sec: float,
+    *,
+    append_retrain_log: AppendRetrainLogFn,
+) -> None:
+    append_retrain_log("failure", None, elapsed_sec)
+    notify_error("AI Retrain Failed", exc)
+
+
+def run_retrain_cli(main_fn: Callable[[], None], append_retrain_log: AppendRetrainLogFn) -> None:
+    import time
+
+    started = time.time()
+    try:
+        main_fn()
+    except Exception as exc:
+        notify_retrain_failure(exc, time.time() - started, append_retrain_log=append_retrain_log)
+        raise SystemExit(1) from exc
diff --git a/src/train_ai_model.py b/src/train_ai_model.py
index 0091776..0471583 100644
--- a/src/train_ai_model.py
+++ b/src/train_ai_model.py
@@ -16,7 +16,9 @@ from src.ml_model import (
     archive_current_champion,
     build_model_bundle,
     build_promotion_report,
+    bundle_to_model_wrapper,
     find_latest_archived_champion,
+    load_ai_score_model,
     load_model_metadata,
     restore_archived_champion,
     save_challenger_bundle,
@@ -24,23 +26,40 @@ from src.ml_model import (
     train_ai_score_model,
 )
 from src.macro_loader import load_macro_data
+from src.ml_quality_report import (
+    CALIBRATION_BINS_FILENAME,
+    CALIBRATION_REPORT_FILENAME,
+    DEFAULT_ML_OUTPUT_DIR,
+    write_ml_quality_reports,
+)
+from src.retrain_holdout import (
+    exclude_holdout_from_ticker_data,
+    portfolio_holdout_window,
+    slice_ticker_data_to_holdout,
+)
 from src.notifier import notify_info
-from src.portfolio_backtester import run_portfolio_backtest
+from src.retrain_notifications import notify_champion_retained_if_needed, run_retrain_cli
+from src.portfolio_backtester import (
+    PortfolioBacktestResult,
+    build_ai_score_frames,
+    run_portfolio_backtest,
+)
 
 VIX_TICKER = "^VIX"
 RETRAIN_LOG_PATH = Path("logs/retrain_history.csv")
 ROLLBACK_REPORT_PATH = Path("logs/ml/model_rollback_report.json")
-OOS_VALIDATION_PATH = Path("logs/validation/oos_validation.csv")
-BASELINE_SUMMARY_PATH = Path("logs/baselines/current_strategy/portfolio_summary.csv")
+from src.model_governance import (
+    evaluate_rollback_need as _evaluate_rollback_need,
+    load_recent_performance_snapshot as _load_recent_performance_snapshot,
+    resolve_rollback_decision,
+)
+
 FEATURE_STATS_PATH = Path("models/ai_feature_stats.json")
 DRIFT_REPORT_PATH = Path("logs/ml/feature_drift_report.json")
-CALIBRATION_REPORT_PATH = Path("logs/ml/model_calibration_report.json")
-CALIBRATION_BINS_PATH = Path("logs/ml/model_calibration_bins.csv")
+CALIBRATION_REPORT_PATH = DEFAULT_ML_OUTPUT_DIR / CALIBRATION_REPORT_FILENAME
+CALIBRATION_BINS_PATH = DEFAULT_ML_OUTPUT_DIR / CALIBRATION_BINS_FILENAME
 THRESHOLD_RETUNE_REPORT_PATH = Path("logs/ml/threshold_retune_report.json")
 THRESHOLD_RETUNE_RESULTS_PATH = Path("logs/ml/threshold_retune_results.csv")
-ROLLBACK_MIN_TOTAL_RETURN = -0.05
-ROLLBACK_MIN_WIN_RATE = 0.35
-ROLLBACK_MAX_DRAWDOWN = -0.20
 DRIFT_ZSCORE_ALERT_THRESHOLD = 1.5
 BUY_THRESHOLD_GRID = [0.40, 0.45, 0.50, 0.55, 0.60]
 EXIT_THRESHOLD_GRID = [0.20, 0.25, 0.30, 0.35, 0.40, 0.45]
@@ -82,65 +101,6 @@ def _append_retrain_log(status: str, metrics_df, elapsed_sec: float) -> None:
         writer.writerow(row)
 
 
-def _load_recent_performance_snapshot() -> dict | None:
-    if OOS_VALIDATION_PATH.exists():
-        df = pd.read_csv(OOS_VALIDATION_PATH)
-        if not df.empty:
-            row = df.iloc[-1]
-            return {
-                "source": str(OOS_VALIDATION_PATH),
-                "total_return": float(row.get("total_return", 0.0)),
-                "max_drawdown": float(row.get("max_drawdown", 0.0)),
-                "win_rate": float(row.get("win_rate", 0.0)),
-            }
-
-    if BASELINE_SUMMARY_PATH.exists():
-        df = pd.read_csv(BASELINE_SUMMARY_PATH)
-        if not df.empty:
-            row = df.iloc[-1]
-            return {
-                "source": str(BASELINE_SUMMARY_PATH),
-                "total_return": float(row.get("total_return", 0.0)),
-                "max_drawdown": float(row.get("max_drawdown", 0.0)),
-                "win_rate": float(row.get("win_rate", 0.0)),
-            }
-
-    return None
-
-
-def _evaluate_rollback_need(performance: dict | None) -> dict:
-    if performance is None:
-        return {
-            "should_rollback": False,
-            "reason": "no recent performance snapshot available",
-        }
-
-    breaches = []
-    if performance["total_return"] <= ROLLBACK_MIN_TOTAL_RETURN:
-        breaches.append(
-            f"total_return={performance['total_return']:.4f} <= {ROLLBACK_MIN_TOTAL_RETURN:.4f}"
-        )
-    if performance["win_rate"] <= ROLLBACK_MIN_WIN_RATE:
-        breaches.append(
-            f"win_rate={performance['win_rate']:.4f} <= {ROLLBACK_MIN_WIN_RATE:.4f}"
-        )
-    if performance["max_drawdown"] <= ROLLBACK_MAX_DRAWDOWN:
-        breaches.append(
-            f"max_drawdown={performance['max_drawdown']:.4f} <= {ROLLBACK_MAX_DRAWDOWN:.4f}"
-        )
-
-    return {
-        "should_rollback": bool(breaches),
-        "reason": "; ".join(breaches) if breaches else "performance within thresholds",
-        "performance": performance,
-        "thresholds": {
-            "min_total_return": ROLLBACK_MIN_TOTAL_RETURN,
-            "min_win_rate": ROLLBACK_MIN_WIN_RATE,
-            "max_drawdown": ROLLBACK_MAX_DRAWDOWN,
-        },
-    }
-
-
 def _write_rollback_report(payload: dict) -> None:
     ROLLBACK_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
     ROLLBACK_REPORT_PATH.write_text(
@@ -256,60 +216,6 @@ def _write_drift_report(report: dict, path: Path = DRIFT_REPORT_PATH) -> None:
     path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
 
 
-def _build_calibration_report(metrics_df: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
-    calibration_rows = metrics_df.attrs.get("calibration_rows", [])
-    calibration_df = pd.DataFrame(calibration_rows)
-    if calibration_df.empty:
-        return {
-            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
-            "overall_avg_brier_score": 0.0,
-            "regimes": {},
-            "bin_count": 0,
-        }, pd.DataFrame()
-
-    regime_brier = {}
-    if "brier_score" in metrics_df.columns and "regime" in metrics_df.columns:
-        for regime, regime_df in metrics_df.groupby("regime"):
-            regime_brier[str(regime)] = {
-                "avg_brier_score": float(regime_df["brier_score"].mean()),
-                "folds": int(len(regime_df)),
-            }
-
-    calibration_df["prob_bin"] = pd.cut(
-        calibration_df["y_prob"],
-        bins=[i / 10 for i in range(11)],
-        include_lowest=True,
-        duplicates="drop",
-    )
-    bin_rows = (
-        calibration_df.groupby(["regime", "prob_bin"], observed=False)
-        .agg(
-            count=("y_true", "size"),
-            avg_pred=("y_prob", "mean"),
-            actual_rate=("y_true", "mean"),
-        )
-        .reset_index()
-    )
-    bin_rows["prob_bin"] = bin_rows["prob_bin"].astype(str)
-
-    report = {
-        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
-        "overall_avg_brier_score": float(metrics_df["brier_score"].mean()) if "brier_score" in metrics_df.columns else 0.0,
-        "regimes": regime_brier,
-        "bin_count": int(len(bin_rows)),
-    }
-    return report, bin_rows
-
-
-def _write_calibration_report(report: dict, bins_df: pd.DataFrame) -> None:
-    CALIBRATION_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
-    CALIBRATION_REPORT_PATH.write_text(
-        json.dumps(report, indent=2, sort_keys=True),
-        encoding="utf-8",
-    )
-    bins_df.to_csv(CALIBRATION_BINS_PATH, index=False)
-
-
 def _pick_latest_date(ticker_data: dict[str, pd.DataFrame]) -> pd.Timestamp:
     latest_dates = []
     for df in ticker_data.values():
@@ -332,6 +238,118 @@ def _score_threshold_row(row: dict) -> tuple[float, float, float, float]:
     )
 
 
+def _portfolio_oos_snapshot(
+    result: PortfolioBacktestResult,
+    eval_start: pd.Timestamp,
+    eval_end: pd.Timestamp,
+) -> dict:
+    return {
+        "evaluation_start": eval_start.strftime("%Y-%m-%d"),
+        "evaluation_end": eval_end.strftime("%Y-%m-%d"),
+        "total_return": float(result.total_return),
+        "benchmark_return": float(result.benchmark_return),
+        "max_drawdown": float(result.max_drawdown),
+        "sharpe_ratio": float(result.sharpe_ratio),
+        "trades": int(result.trades),
+        "win_rate": float(result.win_rate),
+    }
+
+
+def _run_retrain_oos_portfolio(
+    *,
+    settings,
+    ticker_data: dict[str, pd.DataFrame],
+    vix_df: pd.DataFrame | None,
+    macro_df: pd.DataFrame | None,
+    model_wrapper,
+    eval_start: pd.Timestamp,
+    eval_end: pd.Timestamp,
+) -> dict:
+    """Portfolio backtest on holdout-only price data for model promotion."""
+    benchmark_df = (
+        ticker_data.get(settings.market_regime_ticker)
+        if settings.market_regime_filter_enabled
+        else None
+    )
+    relative_strength_benchmark_df = (
+        ticker_data.get(settings.relative_strength_benchmark_ticker)
+        if settings.relative_strength_filter_enabled
+        else None
+    )
+    spy_df = ticker_data.get("SPY")
+
+    ai_score_frames = None
+    if settings.use_ai_score:
+        ai_score_frames = build_ai_score_frames(
+            ticker_data,
+            ai_model_bundle=model_wrapper,
+            vix_df=vix_df,
+            spy_df=spy_df,
+            macro_df=macro_df,
+        )
+
+    result, _, _ = run_portfolio_backtest(
+        ticker_data=ticker_data,
+        benchmark_df=benchmark_df,
+        relative_strength_benchmark_df=relative_strength_benchmark_df,
+        initial_cash=10000.0,
+        max_positions=settings.max_total_positions,
+        target_position_pct=settings.max_position_pct,
+        transaction_cost_pct=0.001,
+        ma_fast=settings.ma_fast,
+        ma_slow=settings.ma_slow,
+        rsi_buy_limit=settings.rsi_buy_limit,
+        use_ai_score=settings.use_ai_score,
+        ai_score_buy_threshold=settings.ai_score_buy_threshold,
+        market_regime_filter_enabled=settings.market_regime_filter_enabled,
+        market_regime_ma_fast=settings.market_regime_ma_fast,
+        market_regime_ma_slow=settings.market_regime_ma_slow,
+        relative_strength_filter_enabled=settings.relative_strength_filter_enabled,
+        relative_strength_lookback_days=settings.relative_strength_lookback_days,
+        relative_strength_min_excess_return=settings.relative_strength_min_excess_return,
+        volume_filter_enabled=settings.volume_filter_enabled,
+        volume_lookback_days=settings.volume_lookback_days,
+        min_volume_ratio=settings.min_volume_ratio,
+        volatility_filter_enabled=settings.volatility_filter_enabled,
+        volatility_lookback_days=settings.volatility_lookback_days,
+        max_volatility=settings.max_volatility,
+        rank_trend_weight=settings.rank_trend_weight,
+        rank_ai_weight=settings.rank_ai_weight,
+        rank_momentum_weight=settings.rank_momentum_weight,
+        rank_volatility_weight=settings.rank_volatility_weight,
+        stop_loss_pct=settings.stop_loss_pct,
+        take_profit_pct=settings.take_profit_pct,
+        trailing_stop_pct=settings.trailing_stop_pct,
+        allocation_method=settings.allocation_method,
+        ai_exit_enabled=getattr(settings, "ai_exit_enabled", False),
+        ai_exit_threshold=(
+            settings.ai_exit_threshold_bear
+            if getattr(settings, "ai_exit_dynamic_enabled", False)
+            else settings.ai_exit_threshold
+        ),
+        ai_exit_dynamic_enabled=getattr(settings, "ai_exit_dynamic_enabled", False),
+        ai_exit_vix_low=getattr(settings, "ai_exit_vix_low", 15.0),
+        ai_exit_vix_high=getattr(settings, "ai_exit_vix_high", 25.0),
+        ai_exit_threshold_bull=getattr(settings, "ai_exit_threshold_bull", 0.22),
+        ai_exit_threshold_bear=getattr(settings, "ai_exit_threshold_bear", 0.50),
+        vix_df=vix_df,
+        macro_df=macro_df,
+        ai_score_frames=ai_score_frames,
+        evaluation_start_date=eval_start,
+        evaluation_end_date=eval_end,
+    )
+    return _portfolio_oos_snapshot(result, eval_start, eval_end)
+
+
+def _load_champion_model_wrapper():
+    if not MODEL_PATH.exists():
+        return None
+    try:
+        return load_ai_score_model()
+    except (FileNotFoundError, ValueError):
+        return None
+
+
 def _run_threshold_retune(
     settings,
     ticker_data: dict[str, pd.DataFrame],
@@ -383,19 +401,23 @@ def _run_threshold_retune(
                 rank_trend_weight=settings.rank_trend_weight,
                 rank_ai_weight=settings.rank_ai_weight,
                 rank_momentum_weight=settings.rank_momentum_weight,
-                rank_volatility_weight=settings.rank_volatility_weight,
-                ai_exit_enabled=getattr(settings, "ai_exit_enabled", False),
-                ai_exit_threshold=exit_threshold,
-                ai_exit_dynamic_enabled=getattr(settings, "ai_exit_dynamic_enabled", False),
-                ai_exit_vix_low=getattr(settings, "ai_exit_vix_low", 15.0),
-                ai_exit_vix_high=getattr(settings, "ai_exit_vix_high", 25.0),
-                ai_exit_threshold_bull=getattr(settings, "ai_exit_threshold_bull", 0.22),
-                ai_exit_threshold_bear=exit_threshold if getattr(settings, "ai_exit_dynamic_enabled", False) else getattr(settings, "ai_exit_threshold_bear", 0.50),
-                vix_df=vix_df,
-                macro_df=macro_df,
-                evaluation_start_date=eval_start,
-                evaluation_end_date=eval_end,
-            )
+        rank_volatility_weight=settings.rank_volatility_weight,
+        stop_loss_pct=settings.stop_loss_pct,
+        take_profit_pct=settings.take_profit_pct,
+        trailing_stop_pct=settings.trailing_stop_pct,
+        allocation_method=settings.allocation_method,
+        ai_exit_enabled=getattr(settings, "ai_exit_enabled", False),
+        ai_exit_threshold=exit_threshold,
+        ai_exit_dynamic_enabled=getattr(settings, "ai_exit_dynamic_enabled", False),
+        ai_exit_vix_low=getattr(settings, "ai_exit_vix_low", 15.0),
+        ai_exit_vix_high=getattr(settings, "ai_exit_vix_high", 25.0),
+        ai_exit_threshold_bull=getattr(settings, "ai_exit_threshold_bull", 0.22),
+        ai_exit_threshold_bear=exit_threshold if getattr(settings, "ai_exit_dynamic_enabled", False) else getattr(settings, "ai_exit_threshold_bear", 0.50),
+        vix_df=vix_df,
+        macro_df=macro_df,
+        evaluation_start_date=eval_start,
+        evaluation_end_date=eval_end,
+    )
             rows.append(
                 {
                     "buy_threshold": buy_threshold,
@@ -464,9 +486,19 @@ def main() -> None:
     else:
         print(f"  Macro data: {len(macro_df)} rows, columns: {list(macro_df.columns)}")
 
+    holdout_start, holdout_end = portfolio_holdout_window(training_data)
+    training_data_fit = exclude_holdout_from_ticker_data(training_data, holdout_start)
+    holdout_ticker_data = slice_ticker_data_to_holdout(
+        training_data, holdout_start, holdout_end
+    )
+    print(
+        f"Portfolio promotion holdout: {holdout_start.strftime('%Y-%m-%d')} "
+        f"to {holdout_end.strftime('%Y-%m-%d')} (excluded from challenger training)"
+    )
+
     print("Training model with LightGBM + enhanced features (21 features)...")
     model, metrics_df = train_ai_score_model(
-        training_data=training_data,
+        training_data=training_data_fit,
         prediction_horizon=20,
         target_return_threshold=0.0,
         vix_df=vix_df,
@@ -483,11 +515,19 @@ def main() -> None:
         spy_df=spy_df,
         macro_df=macro_df,
     )
+    output_dir = DEFAULT_ML_OUTPUT_DIR
+    output_dir.mkdir(parents=True, exist_ok=True)
+
     drift_report = _compare_feature_stats(baseline_feature_stats, current_feature_stats)
     _write_drift_report(drift_report)
     _write_feature_stats(current_feature_stats)
-    calibration_report, calibration_bins_df = _build_calibration_report(metrics_df)
-    _write_calibration_report(calibration_report, calibration_bins_df)
+    quality_paths = write_ml_quality_reports(output_dir, metrics_df)
+    calibration_report = json.loads(
+        quality_paths["calibration_report"].read_text(encoding="utf-8")
+    )
+    stability_report = json.loads(
+        quality_paths["fold_stability"].read_text(encoding="utf-8")
+    )
 
     if drift_report["drifted_feature_count"] > 0:
         top_features = ", ".join(
@@ -506,10 +546,17 @@ def main() -> None:
             f"Average Brier score: {calibration_report['overall_avg_brier_score']:.4f}\n"
             f"Report: {CALIBRATION_REPORT_PATH}"
         )
+    if stability_report.get("high_variance_warning"):
+        roc = stability_report.get("roc_auc", {})
+        notify_info(
+            "⚠️ Fold ROC-AUC Variance Warning",
+            f"ROC-AUC std={roc.get('std')} (threshold={stability_report.get('roc_auc_std_warn_threshold')})\n"
+            f"Report: {quality_paths['fold_stability']}",
+        )
 
     threshold_retune_report, threshold_retune_results_df = _run_threshold_retune(
         settings=settings,
-        ticker_data=training_data,
+        ticker_data=training_data_fit,
         vix_df=vix_df,
         macro_df=macro_df,
     )
@@ -521,26 +568,64 @@ def main() -> None:
         settings.ai_exit_threshold = float(threshold_retune_report["best_exit_threshold"])
     save_settings(settings)
 
-    output_dir = Path("logs/ml")
-    output_dir.mkdir(parents=True, exist_ok=True)
-
     metrics_path = output_dir / "ai_model_metrics.csv"
     metrics_df.to_csv(metrics_path, index=False)
 
     bundle = build_model_bundle(
         trained_models=model.models,
         metrics_df=metrics_df,
-        training_data=training_data,
+        training_data=training_data_fit,
         feature_columns=FEATURE_COLUMNS,
         prediction_horizon=model.prediction_horizon,
         target_return_threshold=model.target_return_threshold,
     )
 
+    challenger_portfolio = None
+    champion_portfolio = None
+    if settings.use_ai_score:
+        if holdout_start > holdout_end:
+            raise ValueError(
+                "Invalid portfolio holdout window; cannot score promotion gates"
+            )
+        print(
+            "Running holdout-window portfolio evaluation for promotion gates "
+            "(full history for indicator warmup)..."
+        )
+        challenger_portfolio = _run_retrain_oos_portfolio(
+            settings=settings,
+            ticker_data=training_data,
+            vix_df=vix_df,
+            macro_df=macro_df,
+            model_wrapper=bundle_to_model_wrapper(bundle),
+            eval_start=holdout_start,
+            eval_end=holdout_end,
+        )
+        challenger_portfolio["holdout_excluded_from_training"] = True
+        bundle["metadata"]["portfolio_oos"] = challenger_portfolio
+        champion_wrapper = _load_champion_model_wrapper()
+        if champion_wrapper is not None:
+            champion_portfolio = _run_retrain_oos_portfolio(
+                settings=settings,
+                ticker_data=training_data,
+                vix_df=vix_df,
+                macro_df=macro_df,
+                model_wrapper=champion_wrapper,
+                eval_start=holdout_start,
+                eval_end=holdout_end,
+            )
+            champion_portfolio["holdout_excluded_from_training"] = True
+
     challenger_model_path, challenger_metadata_path = save_challenger_bundle(bundle)
     champion_metadata = load_model_metadata()
     promotion_report = build_promotion_report(
         challenger_metadata=bundle["metadata"],
         champion_metadata=champion_metadata,
+        challenger_portfolio=challenger_portfolio,
+        champion_portfolio=champion_portfolio,
+        require_portfolio_oos=settings.use_ai_score,
+        fold_stability_report=stability_report,
+        calibration_report=calibration_report,
+        require_ml_quality=True,
     )
     promotion_report.update(
         {
@@ -562,29 +647,15 @@ def main() -> None:
         if archived is not None:
             promotion_report["archived_previous_champion_model_path"] = str(archived[0])
             promotion_report["archived_previous_champion_metadata_path"] = str(archived[1])
-
-    rollback_report = {
-        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
-        "promotion_decision": promotion_report["decision"],
-    }
-    if promotion_report["decision"] == "PROMOTE":
-        rollback_report["decision"] = "SKIP_ROLLBACK_AFTER_PROMOTION"
-        rollback_report["reason"] = "new challenger promoted; wait for fresh performance before rollback evaluation"
     else:
-        rollback_eval = _evaluate_rollback_need(_load_recent_performance_snapshot())
-        rollback_report.update(rollback_eval)
-        if rollback_eval["should_rollback"]:
-            archived = find_latest_archived_champion(CHAMPION_ARCHIVE_DIR)
-            if archived is None:
-                rollback_report["decision"] = "NO_ROLLBACK_AVAILABLE"
-                rollback_report["reason"] = f"{rollback_eval['reason']}; no archived champion available"
-            else:
-                restore_archived_champion(*archived)
-                rollback_report["decision"] = "ROLLBACK_TO_ARCHIVED_CHAMPION"
-                rollback_report["restored_model_path"] = str(archived[0])
-                rollback_report["restored_metadata_path"] = str(archived[1])
-        else:
-            rollback_report["decision"] = "NO_ROLLBACK_NEEDED"
+        notify_champion_retained_if_needed(promotion_report, promotion_report_path)
+
+    archived = find_latest_archived_champion(CHAMPION_ARCHIVE_DIR)
+    rollback_report = resolve_rollback_decision(
+        promotion_report["decision"],
+        _load_recent_performance_snapshot(),
+        archived,
+    )
     _write_rollback_report(rollback_report)
 
     elapsed = time.time() - started_at
@@ -604,6 +675,8 @@ def main() -> None:
     print(f"Saved promotion report to {promotion_report_path}")
     print(f"Saved rollback report to {ROLLBACK_REPORT_PATH}")
     print(f"Saved feature drift report to {DRIFT_REPORT_PATH}")
+    print(f"Saved fold metrics to {quality_paths['fold_metrics']}")
+    print(f"Saved fold stability report to {quality_paths['fold_stability']}")
     print(f"Saved calibration report to {CALIBRATION_REPORT_PATH}")
     print(f"Saved calibration bins to {CALIBRATION_BINS_PATH}")
     print(f"Saved threshold retune report to {THRESHOLD_RETUNE_REPORT_PATH}")
@@ -617,4 +690,4 @@ def main() -> None:
 
 
 if __name__ == "__main__":
-    main()
+    run_retrain_cli(main, _append_retrain_log)
diff --git a/src/walk_forward_validation.py b/src/walk_forward_validation.py
index 492f05f..71c295a 100644
--- a/src/walk_forward_validation.py
+++ b/src/walk_forward_validation.py
@@ -11,6 +11,7 @@ import numpy as np
 from src.settings import load_settings
 from src.data_loader import load_price_data_batch
 from src.ml_model import train_ai_score_model
+from src.ml_quality_report import evaluate_walk_forward_oos_metrics, write_ml_quality_reports
 from src.portfolio_backtester import run_portfolio_backtest, build_ai_score_frames
 from src.macro_loader import load_macro_data
 
@@ -73,7 +74,8 @@ def main():
     print(f"Generated {len(folds)} validation folds.\n")
 
     results = []
-    
+    fold_metrics_frames: list[pd.DataFrame] = []
+
     # 3. 각 Fold별 학습 및 검증
     for i, fold in enumerate(folds, 1):
         t_start, t_end = fold["test_start"], fold["test_end"]
@@ -96,6 +98,11 @@ def main():
         macro_train = _filter_by_date(macro_all, fold["train_start"], fold["train_end"])
         macro_test = _filter_by_date(macro_all, fold["test_start"], fold["test_end"])
 
+        lookback_start = fold["test_start"] - pd.DateOffset(days=400)
+        vix_with_lookback = _filter_by_date(vix_all, lookback_start, fold["test_end"])
+        spy_with_lookback = _filter_by_date(spy_all, lookback_start, fold["test_end"])
+        macro_with_lookback = _filter_by_date(macro_all, lookback_start, fold["test_end"])
+
         # 모델 학습
         print(f"  Training model...")
         model, _ = train_ai_score_model(
@@ -105,16 +112,31 @@ def main():
             spy_df=spy_train,
             macro_df=macro_train,
         )
+        period_label = f"{fold['test_start'].date()} ~ {fold['test_end'].date()}"
+        print(f"  Evaluating OOS classification metrics on test window...")
+        fold_metrics_df = evaluate_walk_forward_oos_metrics(
+            model,
+            all_ticker_data,
+            test_start=fold["test_start"],
+            test_end=fold["test_end"],
+            vix_df=vix_with_lookback,
+            spy_df=spy_with_lookback,
+            macro_df=macro_with_lookback,
+        )
+        if not fold_metrics_df.empty:
+            fold_metrics_df = fold_metrics_df.copy()
+            fold_metrics_df["walk_forward_fold"] = i
+            fold_metrics_df["walk_forward_period"] = period_label
+            fold_metrics_frames.append(fold_metrics_df)
 
         # AI 스코어 계산을 위한 데이터 준비 (피처 생성용 룩백 데이터 포함)
-        lookback_start = fold["test_start"] - pd.DateOffset(days=400) # 넉넉하게 400일
-        test_data_with_lookback = {t: _filter_by_date(df, lookback_start, fold["test_end"]) 
-                                   for t, df in all_ticker_data.items()}
-        test_data_with_lookback = {t: df for t, df in test_data_with_lookback.items() if len(df) > 272}
-
-        vix_with_lookback = _filter_by_date(vix_all, lookback_start, fold["test_end"])
-        spy_with_lookback = _filter_by_date(spy_all, lookback_start, fold["test_end"])
-        macro_with_lookback = _filter_by_date(macro_all, lookback_start, fold["test_end"])
+        test_data_with_lookback = {
+            t: _filter_by_date(df, lookback_start, fold["test_end"])
+            for t, df in all_ticker_data.items()
+        }
+        test_data_with_lookback = {
+            t: df for t, df in test_data_with_lookback.items() if len(df) > 272
+        }
 
         # AI 스코어 계산
         print(f"  Calculating AI scores...")
@@ -173,6 +195,19 @@ def main():
     # 4. 종합 결과 출력 및 저장
     res_df = pd.DataFrame(results)
     res_df.to_csv(output_dir / "walk_forward_results.csv", index=False)
+
+    if fold_metrics_frames:
+        combined_metrics = pd.concat(fold_metrics_frames, ignore_index=True)
+        calibration_rows: list[dict] = []
+        for frame in fold_metrics_frames:
+            calibration_rows.extend(frame.attrs.get("calibration_rows", []))
+        combined_metrics.attrs["calibration_rows"] = calibration_rows
+        quality_paths = write_ml_quality_reports(
+            output_dir, combined_metrics, file_prefix="walk_forward"
+        )
+        print(f"Saved walk-forward fold metrics to {quality_paths['fold_metrics']}")
+        print(f"Saved walk-forward fold stability to {quality_paths['fold_stability']}")
+        print(f"Saved walk-forward calibration to {quality_paths['calibration_report']}")
     
     print("=" * 72)
     print("Walk-Forward Validation Summary")
diff --git a/tests/fixtures/audit_daily/golden_execution_audit.csv b/tests/fixtures/audit_daily/golden_execution_audit.csv
new file mode 100644
index 0000000..6e0d801
--- /dev/null
+++ b/tests/fixtures/audit_daily/golden_execution_audit.csv
@@ -0,0 +1,6 @@
+timestamp,event_type,ticker,action,status,reason
+2026-05-30T09:00:00+00:00,SKIP_BUY,AAPL,BUY,SKIPPED,earnings filter: within 3d window
+2026-05-30T09:05:00+00:00,SKIP_BUY,MSFT,BUY,SKIPPED,macro event risk: FOMC day
+2026-05-30T09:10:00+00:00,SKIP_BUY,GOOG,BUY,SKIPPED,stale price data for GOOG
+2026-05-30T09:15:00+00:00,SKIP_BUY,NVDA,BUY,SKIPPED,LLM reject: low conviction
+2026-05-30T09:20:00+00:00,BUY_ERROR,TSLA,BUY,ERROR,API rate limit exceeded
diff --git a/tests/fixtures/audit_daily/golden_latest_summary.json b/tests/fixtures/audit_daily/golden_latest_summary.json
new file mode 100644
index 0000000..806c162
--- /dev/null
+++ b/tests/fixtures/audit_daily/golden_latest_summary.json
@@ -0,0 +1,41 @@
+{
+  "api_error_count": 1,
+  "api_error_samples": [
+    {
+      "event_type": "BUY_ERROR",
+      "reason": "API rate limit exceeded",
+      "ticker": "TSLA",
+      "timestamp": "2026-05-30T09:20:00+00:00"
+    }
+  ],
+  "context_skip_counts": {
+    "earnings": 1,
+    "macro_event": 1,
+    "other": 1,
+    "stale": 1
+  },
+  "context_skip_rate_of_skips": {
+    "earnings": 0.25,
+    "macro_event": 0.25,
+    "other": 0.25,
+    "stale": 0.25
+  },
+  "event_type_counts": {
+    "BUY_ERROR": 1,
+    "SKIP_BUY": 4
+  },
+  "generated_at": "2026-05-30T12:00:00Z",
+  "orders_submitted_count": 0,
+  "row_count": 5,
+  "skip_by_event": {
+    "SKIP_BUY": 4
+  },
+  "skip_reason_counts": {
+    "earnings filter: within 3d window": 1,
+    "llm_or_policy": 1,
+    "macro event risk: FOMC day": 1,
+    "stale_price_data": 1
+  },
+  "stale_bar_count": 1,
+  "unique_tickers": 5
+}
\ No newline at end of file
diff --git a/tests/fixtures/audit_daily/golden_output/skip_reasons_20260530.csv b/tests/fixtures/audit_daily/golden_output/skip_reasons_20260530.csv
new file mode 100644
index 0000000..74a54ce
--- /dev/null
+++ b/tests/fixtures/audit_daily/golden_output/skip_reasons_20260530.csv
@@ -0,0 +1,5 @@
+reason,count
+earnings filter: within 3d window,1
+macro event risk: FOMC day,1
+stale_price_data,1
+llm_or_policy,1
diff --git a/tests/fixtures/llm_monitoring/golden_llm_cache.json b/tests/fixtures/llm_monitoring/golden_llm_cache.json
new file mode 100644
index 0000000..89ad43f
--- /dev/null
+++ b/tests/fixtures/llm_monitoring/golden_llm_cache.json
@@ -0,0 +1,23 @@
+{
+  "AAPL_2026-05-28": {
+    "is_approved": true,
+    "category": "None",
+    "reason": "No material risk",
+    "category_reason": "No material risk",
+    "timestamp": "2026-05-28T10:00:00"
+  },
+  "MSFT_2026-05-28": {
+    "is_approved": false,
+    "category": "Guidance",
+    "reason": "Weak guidance",
+    "category_reason": "[Guidance] Weak guidance",
+    "timestamp": "2026-05-28T11:00:00"
+  },
+  "AAPL_2026-05-29": {
+    "is_approved": true,
+    "category": "None",
+    "reason": "Reused",
+    "category_reason": "Reused",
+    "timestamp": "2026-05-29T09:00:00"
+  }
+}
diff --git a/tests/fixtures/ml_quality/golden_fold_metrics.csv b/tests/fixtures/ml_quality/golden_fold_metrics.csv
new file mode 100644
index 0000000..2b3fa72
--- /dev/null
+++ b/tests/fixtures/ml_quality/golden_fold_metrics.csv
@@ -0,0 +1,5 @@
+regime,fold,roc_auc,brier_score,test_size,walk_forward_fold,walk_forward_period
+BULL,1,0.52,0.22,100,,
+BULL,2,0.53,0.24,100,,
+BEAR,1,0.51,0.28,80,,
+BEAR,2,0.52,0.26,80,,
diff --git a/tests/fixtures/ml_quality/golden_fold_stability_report.json b/tests/fixtures/ml_quality/golden_fold_stability_report.json
new file mode 100644
index 0000000..01f7eb0
--- /dev/null
+++ b/tests/fixtures/ml_quality/golden_fold_stability_report.json
@@ -0,0 +1,36 @@
+{
+  "by_regime": {
+    "BEAR": {
+      "coefficient_of_variation": 0.009708737864077678,
+      "count": 2,
+      "max": 0.52,
+      "mean": 0.515,
+      "min": 0.51,
+      "range": 0.010000000000000009,
+      "std": 0.0050000000000000044
+    },
+    "BULL": {
+      "coefficient_of_variation": 0.009523809523809532,
+      "count": 2,
+      "max": 0.53,
+      "mean": 0.525,
+      "min": 0.52,
+      "range": 0.010000000000000009,
+      "std": 0.0050000000000000044
+    }
+  },
+  "fold_count": 4,
+  "generated_at": "2026-05-30T10:53:08Z",
+  "high_variance_warning": false,
+  "roc_auc": {
+    "coefficient_of_variation": 0.01359820733051054,
+    "count": 4,
+    "max": 0.53,
+    "mean": 0.52,
+    "min": 0.51,
+    "range": 0.020000000000000018,
+    "std": 0.007071067811865481
+  },
+  "roc_auc_std_warn_threshold": 0.05,
+  "walk_forward_roc_auc": null
+}
\ No newline at end of file
diff --git a/tests/fixtures/ml_quality/golden_model_calibration_bins.csv b/tests/fixtures/ml_quality/golden_model_calibration_bins.csv
new file mode 100644
index 0000000..4303c62
--- /dev/null
+++ b/tests/fixtures/ml_quality/golden_model_calibration_bins.csv
@@ -0,0 +1,21 @@
+regime,prob_bin,count,avg_pred,actual_rate
+BEAR,"(-0.001, 0.1]",0,,
+BEAR,"(0.1, 0.2]",0,,
+BEAR,"(0.2, 0.3]",0,,
+BEAR,"(0.3, 0.4]",1,0.4,0.0
+BEAR,"(0.4, 0.5]",0,,
+BEAR,"(0.5, 0.6]",1,0.6,1.0
+BEAR,"(0.6, 0.7]",0,,
+BEAR,"(0.7, 0.8]",0,,
+BEAR,"(0.8, 0.9]",0,,
+BEAR,"(0.9, 1.0]",0,,
+BULL,"(-0.001, 0.1]",0,,
+BULL,"(0.1, 0.2]",0,,
+BULL,"(0.2, 0.3]",1,0.3,0.0
+BULL,"(0.3, 0.4]",0,,
+BULL,"(0.4, 0.5]",0,,
+BULL,"(0.5, 0.6]",0,,
+BULL,"(0.6, 0.7]",1,0.7,1.0
+BULL,"(0.7, 0.8]",0,,
+BULL,"(0.8, 0.9]",0,,
+BULL,"(0.9, 1.0]",0,,
diff --git a/tests/fixtures/ml_quality/golden_model_calibration_report.json b/tests/fixtures/ml_quality/golden_model_calibration_report.json
new file mode 100644
index 0000000..0f8fb63
--- /dev/null
+++ b/tests/fixtures/ml_quality/golden_model_calibration_report.json
@@ -0,0 +1,15 @@
+{
+  "bin_count": 20,
+  "generated_at": "2026-05-30T10:53:08Z",
+  "overall_avg_brier_score": 0.25,
+  "regimes": {
+    "BEAR": {
+      "avg_brier_score": 0.27,
+      "folds": 2
+    },
+    "BULL": {
+      "avg_brier_score": 0.22999999999999998,
+      "folds": 2
+    }
+  }
+}
\ No newline at end of file
diff --git a/tests/fixtures/portfolio_backtest/portfolio_equity.csv b/tests/fixtures/portfolio_backtest/portfolio_equity.csv
new file mode 100644
index 0000000..5bb4942
--- /dev/null
+++ b/tests/fixtures/portfolio_backtest/portfolio_equity.csv
@@ -0,0 +1,501 @@
+date,cash,positions_value,equity,positions_count,open_symbols,daily_return,running_max,drawdown,benchmark_equity
+2024-05-28,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,9999.999999999989
+2024-05-29,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,9905.593725051025
+2024-05-30,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,9857.842624272827
+2024-05-31,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,9931.719619083231
+2024-06-03,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,9922.880751386698
+2024-06-04,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,9927.632591311254
+2024-06-05,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10057.33326006609
+2024-06-06,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10079.433550382206
+2024-06-07,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10065.276362756653
+2024-06-10,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10113.999408679732
+2024-06-11,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10091.695667494838
+2024-06-12,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10178.225412866488
+2024-06-13,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10160.0223759572
+2024-06-14,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10160.635591668391
+2024-06-17,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10254.868844440382
+2024-06-18,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10290.03501563959
+2024-06-20,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10272.326919538404
+2024-06-21,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10258.794670914835
+2024-06-24,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10238.888562969705
+2024-06-25,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10241.779560208537
+2024-06-26,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10242.155621348651
+2024-06-27,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10278.762281663856
+2024-06-28,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10280.325472357525
+2024-07-01,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10290.68585559318
+2024-07-02,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10347.113527289292
+2024-07-03,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10398.922111992972
+2024-07-05,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10462.071328412045
+2024-07-08,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10461.829032376629
+2024-07-09,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10437.600892063216
+2024-07-10,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10523.056701226333
+2024-07-11,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10481.551083650173
+2024-07-12,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10547.212464711338
+2024-07-15,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10578.585498571363
+2024-07-16,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10687.464930160408
+2024-07-17,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10515.983399517649
+2024-07-18,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10385.470051907427
+2024-07-19,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10329.016150684583
+2024-07-22,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10411.621597003146
+2024-07-23,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10385.03477329268
+2024-07-24,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10153.687825491485
+2024-07-25,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10100.893163055087
+2024-07-26,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10211.451545545378
+2024-07-29,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10189.783849856838
+2024-07-30,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10144.237050980882
+2024-07-31,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10323.216698517455
+2024-08-01,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10124.644039264354
+2024-08-02,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,9861.10978781002
+2024-08-05,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,9607.36338258764
+2024-08-06,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,9727.334712949734
+2024-08-07,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,9648.356363641502
+2024-08-08,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,9921.021631511127
+2024-08-09,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,9955.62199525586
+2024-08-12,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,9936.90855771289
+2024-08-13,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10119.439869824846
+2024-08-14,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10169.510924902272
+2024-08-15,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10356.785484941529
+2024-08-16,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10383.984604169807
+2024-08-19,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10479.21951683484
+2024-08-20,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10443.832044774463
+2024-08-21,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10506.818106480963
+2024-08-22,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10393.317750484997
+2024-08-23,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10523.726233079504
+2024-08-26,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10482.682559361423
+2024-08-27,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10486.843016376017
+2024-08-28,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10399.125799835447
+2024-08-29,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10446.935001648299
+2024-08-30,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10562.937418983734
+2024-09-03,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10322.025034755285
+2024-09-04,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10313.963833236978
+2024-09-05,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10267.30981287168
+2024-09-06,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10089.079130157723
+2024-09-09,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10234.25720636828
+2024-09-10,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10266.126876530527
+2024-09-11,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10363.059232689222
+2024-09-12,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10423.110991036856
+2024-09-13,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10493.143783285404
+2024-09-16,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10537.698502347854
+2024-09-17,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10543.429974913226
+2024-09-18,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10512.041441014935
+2024-09-19,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10703.298047390315
+2024-09-20,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10687.474641097691
+2024-09-23,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10736.487147895223
+2024-09-24,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10777.233669874146
+2024-09-25,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10735.41142234179
+2024-09-26,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10799.066634078927
+2024-09-27,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10792.935371273992
+2024-09-30,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10801.05670241828
+2024-10-01,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10708.675399360345
+2024-10-02,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10728.775961615316
+2024-10-03,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10698.688938099234
+2024-10-04,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10829.47635370419
+2024-10-07,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10749.60958943924
+2024-10-08,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10828.581266577427
+2024-10-09,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10945.935938590934
+2024-10-10,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10941.430600068872
+2024-10-11,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11043.521395910362
+2024-10-14,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11114.679866852208
+2024-10-15,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10976.832995581004
+2024-10-16,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11034.658217058643
+2024-10-17,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11024.617039551149
+2024-10-18,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11071.405111398295
+2024-10-21,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11006.432015543705
+2024-10-22,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10984.211749478085
+2024-10-23,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10902.948777824553
+2024-10-24,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10916.637956878885
+2024-10-25,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10902.2204244777
+2024-10-28,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10935.888918664927
+2024-10-29,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10942.858275071781
+2024-10-30,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10888.465068183457
+2024-10-31,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10745.791022304407
+2024-11-01,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10786.59378531718
+2024-11-04,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10749.697529743007
+2024-11-05,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10916.869947122153
+2024-11-06,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11233.050108527648
+2024-11-07,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11297.222940715625
+2024-11-08,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11324.93035889798
+2024-11-11,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11398.193771428605
+2024-11-12,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11350.372248687449
+2024-11-13,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11360.834814694232
+2024-11-14,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11284.245570021143
+2024-11-15,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11205.130694412848
+2024-11-18,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11248.069752340725
+2024-11-19,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11271.355137375274
+2024-11-20,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11253.476416974267
+2024-11-21,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11394.009985795865
+2024-11-22,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11511.368334104956
+2024-11-25,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11572.81141115215
+2024-11-26,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11553.981007669116
+2024-11-27,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11523.960567845337
+2024-11-29,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11588.95197389831
+2024-12-02,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11605.776081018541
+2024-12-03,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11626.60702532736
+2024-12-04,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11708.95485671084
+2024-12-05,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11654.419851270826
+2024-12-06,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11745.623395769668
+2024-12-09,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11640.867033074323
+2024-12-10,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11540.789805683982
+2024-12-11,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11631.621387741252
+2024-12-12,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11548.77069997956
+2024-12-13,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11569.187931893828
+2024-12-16,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11594.242594030158
+2024-12-17,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11548.355020251352
+2024-12-18,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11155.874005422706
+2024-12-19,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11117.16748239047
+2024-12-20,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11270.104845004536
+2024-12-23,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11324.015011090383
+2024-12-24,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11451.983839462933
+2024-12-26,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11452.67997791054
+2024-12-27,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11336.12540746822
+2024-12-30,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11191.638497724627
+2024-12-31,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11158.541468553141
+2025-01-02,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11162.494499649833
+2025-01-03,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11330.643255982595
+2025-01-06,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11399.56007514246
+2025-01-07,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11259.617838499556
+2025-01-08,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11262.699467616121
+2025-01-10,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11107.332457778872
+2025-01-13,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11122.173413009748
+2025-01-14,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11175.402703942093
+2025-01-15,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11390.307758382545
+2025-01-16,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11452.713479069416
+2025-01-17,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11575.980037527797
+2025-01-21,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11738.78464230174
+2025-01-22,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11801.02765908675
+2025-01-23,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11887.943167909692
+2025-01-24,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11865.144571380504
+2025-01-27,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11739.966083233046
+2025-01-28,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11831.52253345049
+2025-01-29,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11800.382245152
+2025-01-30,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11898.630779123932
+2025-01-31,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11848.384150668448
+2025-02-03,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11782.010515665828
+2025-02-04,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11942.744625418234
+2025-02-05,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,12009.237003968334
+2025-02-06,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,12017.495403208182
+2025-02-07,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11958.807402426384
+2025-02-10,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,12079.110614117672
+2025-02-11,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,12063.03435727829
+2025-02-12,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,12059.43331772443
+2025-02-13,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,12179.621624029758
+2025-02-14,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,12149.731792869892
+2025-02-18,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,12242.037848713817
+2025-02-19,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,12146.623327295532
+2025-02-20,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,12032.791137150929
+2025-02-21,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11768.612175447815
+2025-02-24,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11648.270211130466
+2025-02-25,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11568.304156989063
+2025-02-26,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11602.964801661286
+2025-02-27,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11440.350635869665
+2025-02-28,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11620.877491003253
+2025-03-03,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11419.018309724332
+2025-03-04,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11255.094122238163
+2025-03-05,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11423.10829020214
+2025-03-06,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11124.885840839177
+2025-03-07,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11196.860203682638
+2025-03-10,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10824.874830040335
+2025-03-11,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10768.697429352394
+2025-03-12,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10853.81698241935
+2025-03-13,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10693.633583839031
+2025-03-14,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10942.186103023245
+2025-03-17,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11065.126735780243
+2025-03-18,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10966.977345082265
+2025-03-19,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11097.302378337848
+2025-03-20,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11090.501696825955
+2025-03-21,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11098.794681212761
+2025-03-24,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11310.561661549278
+2025-03-25,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11324.225661830173
+2025-03-26,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11173.731352885894
+2025-03-27,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11096.207052578322
+2025-03-28,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10851.926552617619
+2025-03-31,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10884.93176015446
+2025-04-01,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10917.548952430143
+2025-04-02,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11023.629918296418
+2025-04-03,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10428.204001888005
+2025-04-04,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,9749.410079377605
+2025-04-07,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,9751.013108099078
+2025-04-08,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,9609.939499387907
+2025-04-09,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10567.40630035206
+2025-04-10,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10180.472640269725
+2025-04-11,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10336.23807125484
+2025-04-14,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10433.515059401232
+2025-04-15,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10464.81290974077
+2025-04-16,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10272.45513479374
+2025-04-17,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10307.982459552257
+2025-04-21,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10086.721957930371
+2025-04-22,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10333.063238049448
+2025-04-23,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10524.857999720341
+2025-04-24,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10820.888839099109
+2025-04-25,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10899.092146676305
+2025-04-28,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,10923.923858892444
+2025-04-29,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11002.664037245575
+2025-04-30,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11009.177414529135
+2025-05-01,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11034.678816912543
+2025-05-02,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11269.182625889858
+2025-05-05,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11205.934593445678
+2025-05-06,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11064.220293292057
+2025-05-07,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11118.198464685454
+2025-05-08,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11221.128282857624
+2025-05-09,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11221.004920848287
+2025-05-12,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11571.927876632804
+2025-05-13,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11718.526096442005
+2025-05-14,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11733.693146936175
+2025-05-15,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11786.321854439784
+2025-05-16,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11882.265371255507
+2025-05-19,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11866.894083573807
+2025-05-20,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11838.81196366691
+2025-05-21,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11607.97363925691
+2025-05-22,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11625.097753408352
+2025-05-23,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11569.3061394186
+2025-05-27,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11794.310243528735
+2025-05-28,10000.0,0.0,10000.0,0,,0.0,10000.0,0.0,11714.331264122096
+2025-05-29,2000.0,7992.0,9992.0,8,"ANET,ARM,LULU,QQQ,SCHW,SMH,UBER,XLK",-0.0008000000000000229,10000.0,-0.0008000000000000229,11713.193257684276
+2025-05-30,2000.0,7948.5768005523,9948.576800552299,8,"ANET,ARM,LULU,QQQ,SCHW,SMH,UBER,XLK",-0.00434579658203571,10000.0,-0.005142319944770102,11779.218003580982
+2025-06-02,2000.0,8038.921462584061,10038.921462584061,8,"ANET,ARM,LULU,QQQ,SCHW,SMH,UBER,XLK",0.009081164456281599,10038.921462584061,0.0,11844.44570076475
+2025-06-03,2000.0,8183.464477681387,10183.464477681388,8,"ANET,ARM,LULU,QQQ,SCHW,SMH,UBER,XLK",0.01439826137061151,10183.464477681388,0.0,11940.812338552063
+2025-06-04,2000.0,8223.189804985317,10223.189804985317,8,"ANET,ARM,LULU,QQQ,SCHW,SMH,UBER,XLK",0.0039009638999569773,10223.189804985317,0.0,11918.78707345893
+2025-06-05,2000.0,8205.101851332476,10205.101851332476,8,"ANET,ARM,LULU,QQQ,SCHW,SMH,UBER,XLK",-0.001769306253515901,10223.189804985317,-0.001769306253515901,11867.349951577793
+2025-06-06,2000.0,8098.262435681685,10098.262435681685,8,"ANET,ARM,LULU,QQQ,SCHW,SMH,UBER,XLK",-0.010469216006584126,10223.189804985317,-0.012219999010750215,11999.151183860335
+2025-06-09,2000.0,8157.73751789798,10157.73751789798,8,"ANET,ARM,LULU,QQQ,SCHW,SMH,UBER,XLK",0.005889635231318913,10223.189804985317,-0.006402335116131641,12034.704318498645
+2025-06-10,2000.0,8161.403419606771,10161.403419606771,8,"ANET,ARM,LULU,QQQ,SCHW,SMH,UBER,XLK",0.00036089746386269717,10223.189804985317,-0.006043748238775293,12114.150926687615
+2025-06-11,2000.0,8142.965705799468,10142.965705799468,8,"ANET,ARM,LULU,QQQ,SCHW,SMH,UBER,XLK",-0.0018144849727870227,10223.189804985317,-0.007847266921203744,12138.880810658951
+2025-06-12,2000.0,8137.723344830869,10137.723344830869,8,"ANET,ARM,LULU,QQQ,SCHW,SMH,UBER,XLK",-0.0005168469578480384,10223.189804985317,-0.008360058043016205,12141.283749134855
+2025-06-13,2000.0,7963.517918938012,9963.517918938012,8,"ANET,ARM,LULU,QQQ,SCHW,SMH,UBER,XLK",-0.017183880440146626,10223.189804985317,-0.02540028024527885,12038.343363821874
+2025-06-16,1745.3011226452736,8394.973480106019,10140.274602751291,8,"ANET,ARM,COIN,QQQ,SCHW,SMH,UBER,XLK",0.01774038901232977,10223.189804985317,-0.008110502085522553,12172.639596168954
+2025-06-17,1745.3011226452736,8294.26291106907,10039.564033714345,8,"ANET,ARM,COIN,QQQ,SCHW,SMH,UBER,XLK",-0.009931739817935603,10223.189804985317,-0.017961690506951844,12070.840515405493
+2025-06-18,1745.3011226452736,8471.960178046458,10217.26130069173,8,"ANET,ARM,COIN,QQQ,SCHW,SMH,UBER,XLK",0.017699699546778414,10223.189804985317,-0.000579907485498854,12083.608754063625
+2025-06-20,1745.3011226452736,8446.433248049116,10191.73437069439,8,"ANET,ARM,COIN,QQQ,SCHW,SMH,UBER,XLK",-0.0024984121719204833,10223.189804985317,-0.0030768708094989217,12052.46497086485
+2025-06-23,1745.3011226452736,8579.602580532055,10324.90370317733,8,"ANET,ARM,COIN,QQQ,SCHW,SMH,UBER,XLK",0.013066405347637255,10324.90370317733,0.0,12187.170490601407
+2025-06-24,1745.3011226452736,8974.457182578491,10719.758305223764,8,"ANET,ARM,COIN,QQQ,SCHW,SMH,UBER,XLK",0.0382429331447347,10719.758305223764,0.0,12376.171044808172
+2025-06-25,1745.3011226452736,9061.163188611958,10806.46431125723,8,"ANET,ARM,COIN,QQQ,SCHW,SMH,UBER,XLK",0.008088429194454294,10806.46431125723,0.0,12346.873229463885
+2025-06-26,1745.3011226452736,9252.647385754515,10997.94850839979,8,"ANET,ARM,COIN,QQQ,SCHW,SMH,UBER,XLK",0.01771941234683827,10997.94850839979,0.0,12455.40399495441
+2025-06-27,1745.3011226452736,9194.991808390621,10940.292931035896,8,"ANET,ARM,COIN,QQQ,SCHW,SMH,UBER,XLK",-0.005242393826435765,10997.94850839979,-0.005242393826435765,12451.996846249778
+2025-06-30,1745.3011226452736,9243.024918124063,10988.326040769338,8,"ANET,ARM,COIN,QQQ,SCHW,SMH,UBER,XLK",0.0043904774795544554,10997.94850839979,-0.0008749329589152754,12541.684701044549
+2025-07-01,1745.3011226452736,9056.978158926537,10802.27928157181,8,"ANET,ARM,COIN,QQQ,SCHW,SMH,UBER,XLK",-0.016931310420463475,10997.94850839979,-0.017791429617854293,12508.518212169865
+2025-07-02,1745.3011226452736,9185.360650690576,10930.66177333585,8,"ANET,ARM,COIN,QQQ,SCHW,SMH,UBER,XLK",0.011884759541725298,10997.94850839979,-0.006118116939040741,12594.491660588597
+2025-07-03,1745.3011226452736,9265.12677412775,11010.427896773024,8,"ANET,ARM,COIN,QQQ,SCHW,SMH,UBER,XLK",0.007297465157302119,11010.427896773024,0.0,12719.962284742773
+2025-07-07,1745.3011226452736,9210.213207156487,10955.514329801761,8,"ANET,ARM,COIN,QQQ,SCHW,SMH,UBER,XLK",-0.004987414429856729,11010.427896773024,-0.004987414429856729,12648.466555637795
+2025-07-08,1745.3011226452736,9254.508307645308,10999.809430290581,8,"ANET,ARM,COIN,QQQ,SCHW,SMH,UBER,XLK",0.004043178545102721,11010.427896773024,-0.0009644008917724101,12637.639628440302
+2025-07-09,1745.3011226452736,9379.807972781626,11125.109095426898,8,"ANET,ARM,COIN,QQQ,SCHW,SMH,UBER,XLK",0.011391075993669064,11125.109095426898,0.0,12706.951752075078
+2025-07-10,1745.3011226452736,9451.31706328434,11196.618185929612,8,"ANET,ARM,COIN,QQQ,SCHW,SMH,UBER,XLK",0.006427720383623825,11196.618185929612,0.0,12713.437859610727
+2025-07-11,1745.3011226452736,9418.41714386907,11163.718266514345,8,"ANET,ARM,COIN,QQQ,SCHW,SMH,UBER,XLK",-0.0029383800419855444,11196.618185929612,-0.0029383800419855444,12639.112733135174
+2025-07-14,1745.3011226452736,9416.716331514886,11162.01745416016,8,"ANET,ARM,COIN,QQQ,SCHW,SMH,UBER,XLK",-0.00015235178043560005,11196.618185929612,-0.0030902841549901305,12715.78306911664
+2025-07-15,1745.3011226452736,9402.891564032256,11148.192686677528,8,"ANET,ARM,COIN,QQQ,SCHW,SMH,UBER,XLK",-0.0012385545479932647,11196.618185929612,-0.004325011217488739,12642.431952230065
+2025-07-16,1745.3011226452736,9483.075257892731,11228.376380538004,8,"ANET,ARM,COIN,QQQ,SCHW,SMH,UBER,XLK",0.007192528521353658,11228.376380538004,0.0,12716.306895553804
+2025-07-17,1745.3011226452736,9646.58413488509,11391.885257530364,8,"ANET,ARM,COIN,QQQ,SCHW,SMH,UBER,XLK",0.014562112228066137,11391.885257530364,0.0,12807.341154791586
+2025-07-18,1745.3011226452736,9700.113034546535,11445.414157191808,8,"ANET,ARM,COIN,QQQ,SCHW,SMH,UBER,XLK",0.0046988622560133475,11445.414157191808,0.0,12807.11746796037
+2025-07-21,1745.3011226452736,9734.485520904038,11479.786643549312,8,"ANET,ARM,COIN,QQQ,SCHW,SMH,UBER,XLK",0.0030031666731697992,11479.786643549312,0.0,12825.502218870693
+2025-07-22,1745.3011226452736,9596.022783303139,11341.323905948411,8,"ANET,ARM,COIN,QQQ,SCHW,SMH,UBER,XLK",-0.01206143823924688,11479.786643549312,-0.01206143823924688,12784.641346566983
+2025-07-23,1745.3011226452736,9621.468229683587,11366.769352328862,8,"ANET,ARM,COIN,QQQ,SCHW,SMH,UBER,XLK",0.0022436045907396895,11479.786643549312,-0.009844894746711796,12902.889067776352
+2025-07-24,1745.3011226452736,9672.591856394283,11417.892979039556,8,"ANET,ARM,COIN,QQQ,SCHW,SMH,UBER,XLK",0.004497639137915677,11479.786643549312,-0.005391534392717667,12890.877549993556
+2025-07-25,1745.3011226452736,9695.937247570577,11441.238370215851,8,"ANET,ARM,COIN,QQQ,SCHW,SMH,UBER,XLK",0.002044632159291737,11479.786643549312,-0.0033579259380331905,12981.809091636322
+2025-07-28,1745.3011226452736,9725.95812511117,11471.259247756443,8,"ANET,ARM,COIN,QQQ,SCHW,SMH,UBER,XLK",0.002623918545281212,11479.786643549312,-0.0007428183168944891,12985.687851734116
+2025-07-29,1745.3011226452736,9663.227088881682,11408.528211526955,8,"ANET,ARM,COIN,QQQ,SCHW,SMH,UBER,XLK",-0.005468539667234595,11479.786643549312,-0.006207295852697636,12919.729055134372
+2025-07-30,1745.3011226452736,9757.18277341152,11502.483896056794,8,"ANET,ARM,COIN,QQQ,SCHW,SMH,UBER,XLK",0.008235565779195708,11502.483896056794,0.0,12913.996321366723
+2025-07-31,1745.3011226452736,9547.114053721343,11292.415176366616,8,"ANET,ARM,COIN,QQQ,SCHW,SMH,UBER,XLK",-0.018262900568997265,11502.483896056794,-0.018262900568997265,12826.21782286323
+2025-08-01,1745.3011226452736,9107.213949773497,10852.51507241877,8,"ANET,ARM,COIN,QQQ,SCHW,SMH,UBER,XLK",-0.03895536048554904,11502.483896056794,-0.05650682317936928,12574.81398778401
+2025-08-04,1745.3011226452736,9275.743925614259,11021.045048259533,8,"ANET,ARM,COIN,QQQ,SCHW,SMH,UBER,XLK",0.015529116957328615,11502.483896056794,-0.04185520728808012,12787.937092105083
+2025-08-05,1716.7095975329187,9150.71732550094,10867.42692303386,8,"ANET,ARM,C,COIN,QQQ,SCHW,SMH,XLK",-0.013938616941769344,11502.483896056794,-0.055210420528442605,12791.309902501354
+2025-08-06,1716.7095975329187,9438.427008457069,11155.136605989988,8,"ANET,ARM,C,COIN,QQQ,SCHW,SMH,XLK",0.02647449897696741,11502.483896056794,-0.03019758977327336,12956.754703813505
+2025-08-07,1716.7095975329187,9470.935534425238,11187.645131958157,8,"ANET,ARM,C,COIN,QQQ,SCHW,SMH,XLK",0.0029142203378049736,11502.483896056794,-0.027371371865738237,12923.03399358983
+2025-08-08,1668.5297672353092,9602.393626867648,11270.923394102958,8,"ANET,C,COIN,MDB,QQQ,SCHW,SMH,XLK",0.007443770441637465,11502.483896056794,-0.020131347632941998,12983.0585276015
+2025-08-11,1781.9622680792452,9449.753442918944,11231.715710998189,8,"AMD,ANET,C,MDB,QQQ,SCHW,SMH,XLK",-0.0034786575805565434,11502.483896056794,-0.02353997514844841,12944.19988890061
+2025-08-12,1781.9622680792452,9657.232560942552,11439.194829021797,8,"AMD,ANET,C,MDB,QQQ,SCHW,SMH,XLK",0.018472611252120963,11502.483896056794,-0.005502208706129386,13108.288157736068
+2025-08-13,1781.9622680792452,9636.841652558427,11418.803920637672,8,"AMD,ANET,C,MDB,QQQ,SCHW,SMH,XLK",-0.0017825475209488628,11502.483896056794,-0.007274948278589433,13136.366942936278
+2025-08-14,1781.9622680792452,9613.927464446737,11395.889732525982,8,"AMD,ANET,C,MDB,QQQ,SCHW,SMH,XLK",-0.002006706505422784,11502.483896056794,-0.009267056097974957,13095.424377526844
+2025-08-15,1781.9622680792452,9596.379366216295,11378.34163429554,8,"AMD,ANET,C,MDB,QQQ,SCHW,SMH,XLK",-0.001539862059243724,11502.483896056794,-0.010792648169132502,13037.580575270455
+2025-08-18,1781.9622680792452,9657.332781990557,11439.295050069803,8,"AMD,ANET,C,MDB,QQQ,SCHW,SMH,XLK",0.005356968329246037,11502.483896056794,-0.005493495714317231,13061.33087332474
+2025-08-19,1837.6994914136783,9360.463728309196,11198.163219722874,8,"AMD,ANET,C,PLTR,QQQ,SCHW,SMH,XLK",-0.021079256133485047,11502.483896056794,-0.026456953044571963,12907.871020399689
+2025-08-20,1837.6994914136783,9292.595864120884,11130.295355534561,8,"AMD,ANET,C,PLTR,QQQ,SCHW,SMH,XLK",-0.006060624662871494,11502.483896056794,-0.03235723204531715,12882.515635558795
+2025-08-21,1837.6994914136783,9271.991567935265,11109.691059348943,8,"AMD,ANET,C,PLTR,QQQ,SCHW,SMH,XLK",-0.001851190424643434,11502.483896056794,-0.03414852307183025,12833.43611073042
+2025-08-22,1837.6994914136783,9419.602757976489,11257.302249390166,8,"AMD,ANET,C,PLTR,QQQ,SCHW,SMH,XLK",0.013286705206532856,11502.483896056794,-0.021315539224591284,13058.765268649859
+2025-08-25,1837.6994914136783,9373.827240548631,11211.526731962309,8,"AMD,ANET,C,PLTR,QQQ,SCHW,SMH,XLK",-0.00406629549547155,11502.483896056794,-0.025295159438930348,13006.012131357604
+2025-08-26,1837.6994914136783,9477.229686544004,11314.929177957682,8,"AMD,ANET,C,PLTR,QQQ,SCHW,SMH,XLK",0.009222869326136252,11502.483896056794,-0.01630558406288307,13075.569719932673
+2025-08-27,1837.6994914136783,9460.523766727569,11298.223258141246,8,"AMD,ANET,C,PLTR,QQQ,SCHW,SMH,XLK",-0.0014764493487930963,11502.483896056794,-0.01775795904270472,13123.632560468775
+2025-08-28,1837.6994914136783,9536.980371624773,11374.679863038451,8,"AMD,ANET,C,PLTR,QQQ,SCHW,SMH,XLK",0.0067671352521831984,11502.483896056794,-0.011110994301166244,13232.915682640252
+2025-08-29,1837.6994914136783,9409.014024755941,11246.713516169619,8,"AMD,ANET,C,PLTR,QQQ,SCHW,SMH,XLK",-0.01125010535765969,11502.483896056794,-0.02223609980230934,13143.395465423293
+2025-09-02,1837.6994914136783,9347.547959982649,11185.247451396326,8,"AMD,ANET,C,PLTR,QQQ,SCHW,SMH,XLK",-0.005465246774973065,11502.483896056794,-0.027579820804549904,13077.93196224573
+2025-09-03,1837.6994914136783,9367.402593007988,11205.102084421665,8,"AMD,ANET,C,PLTR,QQQ,SCHW,SMH,XLK",0.0017750732034864658,11502.483896056794,-0.025853703801930528,13060.275457895868
+2025-09-04,1837.6994914136783,9487.77306124313,11325.472552656807,8,"AMD,ANET,C,PLTR,QQQ,SCHW,SMH,XLK",0.010742469575756086,11502.483896056794,-0.015388966852687203,13167.660280948869
+2025-09-05,1837.6994914136783,9349.261237718554,11186.960729132232,8,"AMD,ANET,C,PLTR,QQQ,SCHW,SMH,XLK",-0.01223011427387044,11502.483896056794,-0.027430872303392473,13160.498242461254
+2025-09-08,1821.2281888767698,9402.352855119147,11223.581043995917,8,"AMD,ANET,C,CVS,QQQ,SCHW,SMH,XLK",0.003273482025222485,11502.483896056794,-0.024247184745591288,13197.738597291791
+2025-09-09,1702.396635282986,9624.107097220982,11326.503732503968,8,"ANET,BAC,C,CVS,QQQ,SCHW,SMH,XLK",0.009170218320213364,11502.483896056794,-0.015299318403145468,13271.668502249902
+2025-09-10,1702.396635282986,9773.003451323955,11475.400086606942,8,"ANET,BAC,C,CVS,QQQ,SCHW,SMH,XLK",0.013145835433372222,11502.483896056794,-0.0023546052917436944,13357.183513968857
+2025-09-11,1614.8508604933368,9972.378024159898,11587.228884653236,8,"ANET,BAC,C,CVS,QQQ,SLB,SMH,XLK",0.009745089251991246,11587.228884653236,0.0,13486.654078262409
+2025-09-12,1614.8508604933368,9813.974153611676,11428.825014105012,8,"ANET,BAC,C,CVS,QQQ,SLB,SMH,XLK",-0.013670556793611177,11587.228884653236,-0.013670556793611177,13449.537122178534
+2025-09-15,1614.8508604933368,9870.111319299298,11484.962179792634,8,"ANET,BAC,C,CVS,QQQ,SLB,SMH,XLK",0.004911893008978652,11587.228884653236,-0.008825812096975971,13539.915503724154
+2025-09-16,1614.8508604933368,9854.466842894162,11469.3177033875,8,"ANET,BAC,C,CVS,QQQ,SLB,SMH,XLK",-0.0013621704765087728,11587.228884653236,-0.010175960312815091,13521.39932831301
+2025-09-17,1614.8508604933368,9871.758225068465,11486.609085561802,8,"ANET,BAC,C,CVS,QQQ,SLB,SMH,XLK",0.0015076208211752817,11587.228884653236,-0.008683680981282693,13529.016887544409
+2025-09-18,1614.8508604933368,10023.640880134653,11638.49174062799,8,"ANET,BAC,C,CVS,QQQ,SLB,SMH,XLK",0.013222584135565096,11638.49174062799,0.0,13699.200611229611
+2025-09-19,1614.8508604933368,10076.375523323173,11691.226383816509,8,"ANET,BAC,C,CVS,QQQ,SLB,SMH,XLK",0.004531054741778284,11691.226383816509,0.0,13769.857276245899
+2025-09-22,1614.8508604933368,10067.820679965898,11682.671540459236,8,"ANET,BAC,C,CVS,QQQ,SLB,SMH,XLK",-0.0007317319053127269,11691.226383816509,-0.0007317319053127269,13814.160289642643
+2025-09-23,1614.8508604933368,10061.903686245712,11676.754546739048,8,"ANET,BAC,C,CVS,QQQ,SLB,SMH,XLK",-0.0005064760829486259,11691.226383816509,-0.0012378373835523204,13755.648777999639
+2025-09-24,1614.8508604933368,10017.114061929738,11631.964922423074,8,"ANET,BAC,C,CVS,QQQ,SLB,SMH,XLK",-0.00383579393886313,11691.226383816509,-0.005068883233282251,13687.318141941181
+2025-09-25,1614.8508604933368,9994.63962071381,11609.490481207147,8,"ANET,BAC,C,CVS,QQQ,SLB,SMH,XLK",-0.0019321276642265683,11691.226383816509,-0.006991217167987118,13603.549395480337
+2025-09-26,1614.8508604933368,10071.642966773017,11686.493827266353,8,"ANET,BAC,C,CVS,QQQ,SLB,SMH,XLK",0.006632792901967166,11691.226383816509,-0.00040479556162786867,13677.543769964373
+2025-09-29,1614.8508604933368,10082.179260639583,11697.03012113292,8,"ANET,BAC,C,CVS,QQQ,SLB,SMH,XLK",0.000901578696082872,11697.03012113292,0.0,13746.701398284227
+2025-09-30,1614.8508604933368,10069.14510629178,11683.995966785118,8,"ANET,BAC,C,CVS,QQQ,SLB,SMH,XLK",-0.0011143131387046923,11697.03012113292,-0.0011143131387046923,13774.69301773403
+2025-10-01,1614.8508604933368,10150.986626920354,11765.83748741369,8,"ANET,BAC,C,CVS,QQQ,SLB,SMH,XLK",0.007004583094792904,11765.83748741369,0.0,13877.799618195924
+2025-10-02,1614.8508604933368,10082.426512760536,11697.277373253874,8,"ANET,BAC,C,CVS,QQQ,SLB,SMH,XLK",-0.005827049220521463,11765.83748741369,-0.005827049220521463,13908.998945579915
+2025-10-03,1614.8508604933368,10090.734887811504,11705.585748304842,8,"ANET,BAC,C,CVS,QQQ,SLB,SMH,XLK",0.0007102828107645731,11765.83748741369,-0.005120905262655628,13846.829109309376
+2025-10-06,1614.8508604933368,10183.886746712225,11798.737607205563,8,"ANET,BAC,C,CVS,QQQ,SLB,SMH,XLK",0.007957898126901508,11798.737607205563,0.0,13982.535104601708
+2025-10-07,1614.8508604933368,10088.284872166823,11703.135732660161,8,"ANET,BAC,C,CVS,QQQ,SLB,SMH,XLK",-0.00810272062385875,11798.737607205563,-0.00810272062385875,13889.763987168259
+2025-10-08,1614.8508604933368,10259.482012376378,11874.332872869716,8,"ANET,BAC,C,CVS,QQQ,SLB,SMH,XLK",0.014628313652023328,11874.332872869716,0.0,14022.043754885748
+2025-10-09,1614.8508604933368,10222.078885297993,11836.92974579133,8,"ANET,BAC,C,CVS,QQQ,SLB,SMH,XLK",-0.003149913976543739,11874.332872869716,-0.003149913976543739,13969.470118058598
+2025-10-10,1479.1419460200511,10058.554446827948,11537.696392847998,8,"AMAT,ANET,BAC,C,CVS,QQQ,SMH,XLK",-0.025279642556780946,11874.332872869716,-0.028349927833913102,13560.022847509894
+2025-10-13,1479.1419460200511,10185.447919002294,11664.589865022344,8,"AMAT,ANET,BAC,C,CVS,QQQ,SMH,XLK",0.010998163572149888,11874.332872869716,-0.0176635614053392,13807.366093889264
+2025-10-14,1479.1419460200511,10120.58313519339,11599.72508121344,8,"AMAT,ANET,BAC,C,CVS,QQQ,SMH,XLK",-0.005560828504001525,11874.332872869716,-0.023126165873595728,13825.819082566257
+2025-10-15,1479.5207914286636,10341.25643931785,11820.777230746515,8,"AMAT,ANET,ASML,BAC,CVS,QQQ,SMH,XLK",0.019056671428453464,11874.332872869716,-0.004510202189595414,13941.876542665592
+2025-10-16,1479.5207914286636,10356.486010676208,11836.006802104872,8,"AMAT,ANET,ASML,BAC,CVS,QQQ,SMH,XLK",0.0012883730960384643,11874.332872869716,-0.0032276399167157077,13852.524799374592
+2025-10-17,1479.5207914286636,10364.242200477927,11843.762991906591,8,"AMAT,ANET,ASML,BAC,CVS,QQQ,SMH,XLK",0.0006553046083364045,11874.332872869716,-0.0025744503956909304,13872.901313547742
+2025-10-20,1479.5207914286636,10498.482801867527,11978.003593296191,8,"AMAT,ANET,ASML,BAC,CVS,QQQ,SMH,XLK",0.01133428636501188,11978.003593296191,0.0,14060.592393711553
+2025-10-21,1479.5207914286636,10450.226986754918,11929.747778183582,8,"AMAT,ANET,ASML,BAC,CVS,QQQ,SMH,XLK",-0.004028702674593987,11978.003593296191,-0.004028702674593987,14052.437743908999
+2025-10-22,1479.5207914286636,10335.163064362667,11814.68385579133,8,"AMAT,ANET,ASML,BAC,CVS,QQQ,SMH,XLK",-0.009645126161231476,11978.003593296191,-0.013634971490262937,13919.929132558846
+2025-10-23,1479.5207914286636,10540.186856476435,12019.7076479051,8,"AMAT,ANET,ASML,BAC,CVS,QQQ,SMH,XLK",0.017353303280584154,12019.7076479051,0.0,14071.00484072197
+2025-10-24,1479.5207914286636,10640.105755072846,12119.62654650151,8,"AMAT,ANET,ASML,BAC,CVS,QQQ,SMH,XLK",0.008312922537165424,12119.62654650151,0.0,14195.40862103275
+2025-10-27,1479.5207914286636,10819.412288127185,12298.933079555849,8,"AMAT,ANET,ASML,BAC,CVS,QQQ,SMH,XLK",0.0147947242735873,12298.933079555849,0.0,14352.925349439942
+2025-10-28,1479.5207914286636,10817.59999901118,12297.120790439843,8,"AMAT,ANET,ASML,BAC,CVS,QQQ,SMH,XLK",-0.00014735336018845135,12298.933079555849,-0.00014735336018845135,14347.46807198036
+2025-10-29,1479.5207914286636,10951.778546857955,12431.299338286619,8,"AMAT,ANET,ASML,BAC,CVS,QQQ,SMH,XLK",0.010911379186507641,12431.299338286619,0.0,14370.144164445852
+2025-10-30,1479.5207914286636,10790.428631187362,12269.949422616026,8,"AMAT,ANET,ASML,BAC,CVS,QQQ,SMH,XLK",-0.012979328329232542,12431.299338286619,-0.012979328329232542,14177.624834777473
+2025-10-31,1479.5207914286636,10802.877130165665,12282.39792159433,8,"AMAT,ANET,ASML,BAC,CVS,QQQ,SMH,XLK",0.0010145517760129508,12431.299338286619,-0.011977944753827519,14278.417927474935
+2025-11-03,1479.5207914286636,10866.788995665005,12346.309787093669,8,"AMAT,ANET,ASML,BAC,CVS,QQQ,SMH,XLK",0.005203533211293632,12431.299338286619,-0.006836739175863471,14269.34897721236
+2025-11-04,1479.5207914286636,10615.771806896162,12095.292598324826,8,"AMAT,ANET,ASML,BAC,CVS,QQQ,SMH,XLK",-0.020331353505421257,12431.299338286619,-0.027029092520275855,13962.031580575367
+2025-11-05,1479.5207914286636,10561.954582847242,12041.475374275906,8,"AMAT,ANET,ASML,BAC,CVS,QQQ,SMH,XLK",-0.004449435481732267,12431.299338286619,-0.03135826379870943,14019.261000407812
+2025-11-06,1479.5207914286636,10368.712380782206,11848.23317221087,8,"AMAT,ANET,ASML,BAC,CVS,QQQ,SMH,XLK",-0.016048050264493074,12431.299338286619,-0.0469030750695536,13862.936020613228
+2025-11-07,1479.5207914286636,10325.747632884595,11805.268424313259,8,"AMAT,ANET,ASML,BAC,CVS,QQQ,SMH,XLK",-0.0036262577949919272,12431.299338286619,-0.05035925022296539,13914.112429789251
+2025-11-10,1479.5207914286636,10492.169900105237,11971.6906915339,8,"AMAT,ANET,ASML,BAC,CVS,QQQ,SMH,XLK",0.014097287858181318,12431.299338286619,-0.036971891211499464,14159.484175594851
+2025-11-11,1479.5207914286636,10407.28592471106,11886.806716139723,8,"AMAT,ANET,ASML,BAC,CVS,QQQ,SMH,XLK",-0.0070903916231485065,12431.299338286619,-0.04380013764691004,14167.620797557356
+2025-11-12,1843.906972627765,10107.905942610028,11951.812915237793,8,"AMAT,AMD,ASML,BAC,CVS,QQQ,SMH,XLK",0.005468768917543443,12431.299338286619,-0.0385709015607143,14164.109050741718
+2025-11-13,1843.906972627765,9851.569431915408,11695.476404543173,8,"AMAT,AMD,ASML,BAC,CVS,QQQ,SMH,XLK",-0.021447500267328334,12431.299338286619,-0.059191152406508074,13834.842143856413
+2025-11-14,1843.906972627765,9825.867092599141,11669.774065226906,8,"AMAT,AMD,ASML,BAC,CVS,QQQ,SMH,XLK",-0.0021976308127373834,12431.299338286619,-0.061258702918875474,13802.641782102071
+2025-11-17,1843.906972627765,9762.483495097145,11606.39046772491,8,"AMAT,AMD,ASML,BAC,CVS,QQQ,SMH,XLK",-0.005431433132100039,12431.299338286619,-0.0663574135023125,13632.316327063534
+2025-11-18,1843.906972627765,9610.162751338452,11454.069723966217,8,"AMAT,AMD,ASML,BAC,CVS,QQQ,SMH,XLK",-0.013123868629292379,12431.299338286619,-0.07861041615422093,13524.950597619101
+2025-11-19,1843.906972627765,9701.962032939822,11545.869005567587,8,"AMAT,AMD,ASML,BAC,CVS,QQQ,SMH,XLK",0.0080145558577569,12431.299338286619,-0.07122588786773343,13542.2827441897
+2025-11-20,1843.906972627765,9318.02573830364,11161.932710931405,8,"AMAT,AMD,ASML,BAC,CVS,QQQ,SMH,XLK",-0.03325313100737948,12431.299338286619,-0.10211053509473034,13211.992183434644
+2025-11-21,1916.708127396886,9296.025556693978,11212.733684090865,8,"AMAT,AMD,ASML,BAC,CVS,ISRG,SMH,UPS",0.004551270328812196,12431.299338286619,-0.09802399741455403,13292.377068342083
+2025-11-24,1916.708127396886,9470.949740316166,11387.657867713053,8,"AMAT,AMD,ASML,BAC,CVS,ISRG,SMH,UPS",0.015600493916160474,12431.299338286619,-0.08395272627369688,13514.282313568781
+2025-11-25,2158.52810607155,9324.54651375291,11483.07461982446,8,"AMAT,AMD,ASML,BAC,CAT,CVS,ISRG,UPS",0.008378961962137721,12431.299338286619,-0.07627720101162416,13648.282393524187
+2025-11-26,3495.033755729516,8159.696709068591,11654.730464798107,7,"AMAT,AMD,BAC,CAT,CRWD,ISRG,UPS",0.014948596143170567,12431.299338286619,-0.06246884194130786,13769.179649989
+2025-11-28,3495.033755729516,8223.99178264201,11719.025538371527,7,"AMAT,AMD,BAC,CAT,CRWD,ISRG,UPS",0.005516650407970891,12431.299338286619,-0.05729681029571798,13898.153214207625
+2025-12-01,2171.274041055628,9510.669958501809,11681.943999557436,8,"AMAT,BAC,CAT,GS,ISRG,MCD,UPS,XLV",-0.003164216913144835,12431.299338286619,-0.06027972767265577,13785.826576923084
+2025-12-02,2171.274041055628,9596.014779355053,11767.288820410682,8,"AMAT,BAC,CAT,GS,ISRG,MCD,UPS,XLV",0.007305703644571393,12431.299338286619,-0.05341440985423618,13879.339788690051
+2025-12-03,2171.274041055628,9750.979419009846,11922.253460065473,8,"AMAT,BAC,CAT,GS,ISRG,MCD,UPS,XLV",0.01316910309756314,12431.299338286619,-0.040948726626938936,14028.130628439918
+2025-12-04,2171.274041055628,9725.676623858697,11896.950664914326,8,"AMAT,BAC,CAT,GS,ISRG,MCD,UPS,XLV",-0.0021223164929264904,12431.299338286619,-0.04298413696198078,14022.099643392188
+2025-12-05,2171.274041055628,9771.904280283074,11943.178321338703,8,"AMAT,BAC,CAT,GS,ISRG,MCD,UPS,XLV",0.003885672701048337,12431.299338286619,-0.0392654865485037,14071.021584026841
+2025-12-08,2171.274041055628,9747.594681155815,11918.868722211442,8,"AMAT,BAC,CAT,GS,ISRG,MCD,UPS,XLV",-0.0020354380109879333,12431.299338286619,-0.04122100209565094,14037.519823795958
+2025-12-09,2171.274041055628,9735.942726155154,11907.216767210783,8,"AMAT,BAC,CAT,GS,ISRG,MCD,UPS,XLV",-0.0009776057839235852,12431.299338286619,-0.04215830998950665,14046.135457067061
+2025-12-10,2171.274041055628,9895.619711722013,12066.89375277764,8,"AMAT,BAC,CAT,GS,ISRG,MCD,UPS,XLV",0.01341010151142652,12431.299338286619,-0.0293135556945896,14197.531000952942
+2025-12-11,2171.274041055628,9931.5883657749,12102.862406830529,8,"AMAT,BAC,CAT,GS,ISRG,MCD,UPS,XLV",0.0029807715879333063,12431.299338286619,-0.026420161120611962,14242.304688961
+2025-12-12,2171.274041055628,9820.956702905814,11992.230743961441,8,"AMAT,BAC,CAT,GS,ISRG,MCD,UPS,XLV",-0.00914095022733219,12431.299338286619,-0.03531960597014261,14073.928863433872
+2025-12-15,2171.274041055628,9869.801308258564,12041.075349314193,8,"AMAT,BAC,CAT,GS,ISRG,MCD,UPS,XLV",0.004073020807854766,12431.299338286619,-0.031390442652329376,14025.251087375504
+2025-12-16,2171.274041055628,9786.977595919738,11958.251636975365,8,"AMAT,BAC,CAT,GS,ISRG,MCD,UPS,XLV",-0.006878431530083051,12431.299338286619,-0.03805295717192936,13995.985135227344
+2025-12-17,2171.274041055628,9686.946861103326,11858.220902158955,8,"AMAT,BAC,CAT,GS,ISRG,MCD,UPS,XLV",-0.008364996644418365,12431.299338286619,-0.04609964095729435,13800.41705558069
+2025-12-18,2171.274041055628,9750.764786752417,11922.038827808046,8,"AMAT,BAC,CAT,GS,ISRG,MCD,UPS,XLV",0.005381745387916581,12431.299338286619,-0.04096599209948415,13928.04281574932
+2025-12-19,2171.274041055628,9847.81708685674,12019.091127912368,8,"AMAT,BAC,CAT,GS,ISRG,MCD,UPS,XLV",0.008140579099436218,12431.299338286619,-0.033158899899120575,14072.30173871987
+2025-12-22,2171.274041055628,9906.17509236245,12077.449133418078,8,"AMAT,BAC,CAT,GS,ISRG,MCD,UPS,XLV",0.004855442469371418,12431.299338286619,-0.028464458560557127,14195.38246773281
+2025-12-23,2171.274041055628,9884.475806654082,12055.74984770971,8,"AMAT,BAC,CAT,GS,ISRG,MCD,UPS,XLV",-0.0017966778802923633,12431.299338286619,-0.03020999497777921,14199.535884856488
+2025-12-24,2171.274041055628,9930.544709173184,12101.818750228813,8,"AMAT,BAC,CAT,GS,ISRG,MCD,UPS,XLV",0.003821322033142005,12431.299338286619,-0.026504115064066802,14255.580011788083
+2025-12-26,2171.274041055628,9919.539549275672,12090.813590331301,8,"AMAT,BAC,CAT,GS,ISRG,MCD,UPS,XLV",-0.0009093806579529851,12431.299338286619,-0.02738939339242441,14241.582830661548
+2025-12-29,2171.274041055628,9851.86372399878,12023.13776505441,8,"AMAT,BAC,CAT,GS,ISRG,MCD,UPS,XLV",-0.005597292917575936,12431.299338286619,-0.03283337985234824,14162.780212586682
+2025-12-30,2171.274041055628,9810.73516481565,11982.009205871276,8,"AMAT,BAC,CAT,GS,ISRG,MCD,UPS,XLV",-0.003420784156917378,12431.299338286619,-0.03614184810364862,14127.731859926069
+2025-12-31,2171.274041055628,9737.307385413054,11908.581426468681,8,"AMAT,BAC,CAT,GS,ISRG,MCD,UPS,XLV",-0.00612816916937553,12431.299338286619,-0.042048533913751185,14009.80519451299
+2026-01-02,2171.274041055628,9936.162363606527,12107.436404662156,8,"AMAT,BAC,CAT,GS,ISRG,MCD,UPS,XLV",0.016698460637090573,12431.299338286619,-0.02605221906506683,14097.1884333024
+2026-01-05,2171.274041055628,10131.327767612438,12302.601808668067,8,"AMAT,BAC,CAT,GS,ISRG,MCD,UPS,XLV",0.01611946554852528,12431.299338286619,-0.010352701364223615,14310.889899893156
+2026-01-06,2171.274041055628,10353.238347281336,12524.512388336963,8,"AMAT,BAC,CAT,GS,ISRG,MCD,UPS,XLV",0.01803769504370556,12524.512388336963,0.0,14470.57783603757
+2026-01-07,2171.274041055628,10239.446137668805,12410.720178724434,8,"AMAT,BAC,CAT,GS,ISRG,MCD,UPS,XLV",-0.009085560066872889,12524.512388336963,-0.009085560066872889,14394.733374663421
+2026-01-08,2118.9972635227796,10268.614156443839,12387.611419966619,8,"AMAT,BAC,CAT,GS,ISRG,LLY,UPS,XLV",-0.0018619998215276823,12524.512388336963,-0.010930642577177574,14333.474098472152
+2026-01-09,2118.9972635227796,10378.295462094407,12497.292725617186,8,"AMAT,BAC,CAT,GS,ISRG,LLY,UPS,XLV",0.008854112542937997,12524.512388336963,-0.00217331117378472,14432.89837651086
+2026-01-12,2118.9972635227796,10429.750668130828,12548.747931653608,8,"AMAT,BAC,CAT,GS,ISRG,LLY,UPS,XLV",0.004117308217558957,12548.747931653608,0.0,14500.128383310082
+2026-01-13,2118.9972635227796,10351.061029401637,12470.058292924416,8,"AMAT,BAC,CAT,GS,ISRG,LLY,UPS,XLV",-0.0062707163422018874,12548.747931653608,-0.0062707163422018874,14503.014771198516
+2026-01-14,2118.9972635227796,10268.307526877848,12387.304790400627,8,"AMAT,BAC,CAT,GS,ISRG,LLY,UPS,XLV",-0.006636176077119305,12548.747931653608,-0.012865278841544758,14411.575573719823
+2026-01-15,2118.9972635227796,10395.76719979781,12514.76446332059,8,"AMAT,BAC,CAT,GS,ISRG,LLY,UPS,XLV",0.010289540386439366,12548.747931653608,-0.002708116261328164,14496.344062082784
+2026-01-16,2118.9972635227796,10391.443349473668,12510.440612996448,8,"AMAT,BAC,CAT,GS,ISRG,LLY,UPS,XLV",-0.0003454999362404454,12548.747931653608,-0.003052680543572883,14490.893636920797
+2026-01-20,1933.9064049697206,10427.336135720085,12361.242540689806,8,"AMAT,BAC,CAT,GS,KLAC,LLY,UPS,XLV",-0.01192588470078737,12548.747931653608,-0.014942159328169224,14209.32310049075
+2026-01-21,1933.9064049697206,10627.529968706402,12561.436373676122,8,"AMAT,BAC,CAT,GS,KLAC,LLY,UPS,XLV",0.016195283955260376,12561.436373676122,0.0,14360.511810882103
+2026-01-22,1864.5587140775265,10679.487623005276,12544.046337082802,8,"AMAT,CAT,GS,HD,KLAC,LLY,UPS,XLV",-0.00138439873243823,12561.436373676122,-0.00138439873243823,14428.626303703995
+2026-01-23,1864.5587140775265,10574.821478120959,12439.380192198485,8,"AMAT,CAT,GS,HD,KLAC,LLY,UPS,XLV",-0.008343890166835677,12561.436373676122,-0.009716737628303385,14379.39747564
+2026-01-26,1864.5587140775265,10621.597919362428,12486.156633439954,8,"AMAT,CAT,GS,HD,KLAC,LLY,UPS,XLV",0.003760351441851162,12561.436373676122,-0.005992924534802824,14439.349334176406
+2026-01-27,1864.5587140775265,10694.29096290363,12558.849676981155,8,"AMAT,CAT,GS,HD,KLAC,LLY,UPS,XLV",0.005821891049045291,12561.436373676122,-0.0002059236394643671,14504.876458731886
+2026-01-28,1778.6751574723687,10743.547785796472,12522.222943268842,8,"AMAT,BA,CAT,GS,HD,KLAC,UPS,XLV",-0.002916408321969599,12561.436373676122,-0.0031217314040181687,14471.794014114612
+2026-01-29,1778.6751574723687,10838.774007554082,12617.449165026452,8,"AMAT,BA,CAT,GS,HD,KLAC,UPS,XLV",0.007604578052077926,12617.449165026452,0.0,14444.408944606126
+2026-01-30,1778.6751574723687,10515.11193660656,12293.787094078929,8,"AMAT,BA,CAT,GS,HD,KLAC,UPS,XLV",-0.02565194174466434,12617.449165026452,-0.02565194174466434,14237.242671500853
+2026-02-02,1778.6751574723687,10681.008582040015,12459.683739512384,8,"AMAT,BA,CAT,GS,HD,KLAC,UPS,XLV",0.013494348337409923,12617.449165026452,-0.012503749644687923,14326.924100310342
+2026-02-03,1778.6751574723687,10612.717626902386,12391.392784374755,8,"AMAT,BA,CAT,GS,HD,KLAC,UPS,XLV",-0.005480954136986904,12617.449165026452,-0.017916171303331896,14217.975755263413
+2026-02-04,1778.6751574723687,10504.02784137021,12282.70299884258,8,"AMAT,BA,CAT,GS,HD,KLAC,UPS,XLV",-0.008771393774978264,12617.449165026452,-0.026530415284868658,14007.753437761483
+2026-02-05,1778.6751574723687,10476.48927982102,12255.16443729339,8,"AMAT,BA,CAT,GS,HD,KLAC,UPS,XLV",-0.0022420603634057956,12617.449165026452,-0.028712992855739583,13780.249430980804
+2026-02-06,1778.6751574723687,10895.690573903357,12674.365731375727,8,"AMAT,BA,CAT,GS,HD,KLAC,UPS,XLV",0.03420609296817556,12674.365731375727,0.0,14185.893335865958
+2026-02-09,1681.5732939560687,11077.603439717772,12759.176733673841,8,"AMAT,BA,CAT,GS,HD,KLAC,LIN,UPS",0.006691538187837187,12759.176733673841,0.0,14323.072812634218
+2026-02-10,1681.5732939560687,11108.335404947888,12789.908698903957,8,"AMAT,BA,CAT,GS,HD,KLAC,LIN,UPS",0.0024086166272003773,12789.908698903957,0.0,14326.220760939781
+2026-02-11,1681.5732939560687,11273.548047297814,12955.121341253884,8,"AMAT,BA,CAT,GS,HD,KLAC,LIN,UPS",0.012917421557832043,12955.121341253884,0.0,14355.44488207824
+2026-02-12,1681.5732939560687,11101.277073889949,12782.850367846018,8,"AMAT,BA,CAT,GS,HD,KLAC,LIN,UPS",-0.013297519094575438,12955.121341253884,-0.013297519094575438,14118.86774853715
+2026-02-13,1681.5732939560687,11349.36124255714,13030.934536513209,8,"AMAT,BA,CAT,GS,HD,KLAC,LIN,UPS",0.019407578241799728,13030.934536513209,0.0,14257.673836559223
+2026-02-17,1681.5732939560687,11333.384284058982,13014.957578015052,8,"AMAT,BA,CAT,GS,HD,KLAC,LIN,UPS",-0.0012260792542077015,13030.934536513209,-0.0012260792542077015,14225.501725671875
+2026-02-18,1681.5732939560687,11388.365175860405,13069.938469816474,8,"AMAT,BA,CAT,GS,HD,KLAC,LIN,UPS",0.004224438802189923,13069.938469816474,0.0,14322.27211874286
+2026-02-19,1681.5732939560687,11341.077293090364,13022.650587046433,8,"AMAT,BA,CAT,GS,HD,KLAC,LIN,UPS",-0.0036180646817309814,13069.938469816474,-0.0036180646817309814,14304.042001354977
+2026-02-20,1681.5732939560687,11435.379282672917,13116.952576628986,8,"AMAT,BA,CAT,GS,HD,KLAC,LIN,UPS",0.0072413821558228175,13116.952576628986,0.0,14313.058624501275
+2026-02-23,1681.5732939560687,11327.056651212471,13008.62994516854,8,"AMAT,BA,CAT,GS,HD,KLAC,LIN,UPS",-0.008258216291293752,13116.952576628986,-0.008258216291293752,14080.850778975242
+2026-02-24,2985.684846974249,10160.187473732438,13145.872320706687,7,"AMAT,BA,CAT,HD,KLAC,LIN,UPS",0.010550102210349799,13145.872320706687,0.0,14201.685674598211
+2026-02-25,2985.684846974249,10232.644970546522,13218.329817520771,7,"AMAT,BA,CAT,HD,KLAC,LIN,UPS",0.005511805914922174,13218.329817520771,0.0,14367.406227169897
+2026-02-26,2985.684846974249,10079.945769265423,13065.630616239672,7,"AMAT,BA,CAT,HD,KLAC,LIN,UPS",-0.011552079830743578,13218.329817520771,-0.011552079830743578,14348.002213124319
+2026-02-27,2985.684846974249,10068.284446067513,13053.969293041762,7,"AMAT,BA,CAT,HD,KLAC,LIN,UPS",-0.0008925189713702153,13218.329817520771,-0.012434288351706124,14299.674468466963
+2026-03-02,4174.2240730209005,8869.695763326745,13043.919836347646,6,"AMAT,CAT,HD,KLAC,LIN,UPS",-0.0007698391553190298,13218.329817520771,-0.013194555104983574,14331.367736100128
+2026-03-03,4174.2240730209005,8567.269762816159,12741.49383583706,6,"AMAT,CAT,HD,KLAC,LIN,UPS",-0.023185208457649265,13218.329817520771,-0.03607384505201783,14130.345937897633
+2026-03-04,2894.9163664287507,9896.88139178615,12791.7977582149,7,"AMAT,CAT,HD,KLAC,LIN,SLB,UPS",0.003948039611835208,13218.329817520771,-0.03226822640939908,14316.998653622572
+2026-03-05,1645.0684887173265,10852.160440519201,12497.228929236528,8,"AMAT,CAT,HD,KLAC,LIN,SLB,UPS,XOM",-0.0230279460749917,13218.329817520771,-0.05455310150669945,14205.863534235627
+2026-03-06,1601.4548092714926,10594.316479567653,12195.771288839145,8,"AMAT,CAT,FCX,KLAC,LIN,SLB,UPS,XOM",-0.0241219587241569,13218.329817520771,-0.07735913256803706,14029.661416526778
+2026-03-09,1601.4548092714926,10783.817277169646,12385.272086441139,8,"AMAT,CAT,FCX,KLAC,LIN,SLB,UPS,XOM",0.015538238059237264,13218.329817520771,-0.063022919126698,14142.17776446723
+2026-03-10,1601.4548092714926,10906.471576738111,12507.926386009603,8,"AMAT,CAT,FCX,KLAC,LIN,SLB,UPS,XOM",0.009903238193914365,13218.329817520771,-0.05374381191257116,14104.19512715706
+2026-03-11,1554.673418804296,10996.645264152869,12551.318682957164,8,"AMAT,CAT,FCX,KLAC,LIN,SLB,T,XOM",0.003469183908541007,13218.329817520771,-0.05046107517150089,14138.17515586446
+2026-03-12,1554.673418804296,10767.942667354062,12322.616086158358,8,"AMAT,CAT,FCX,KLAC,LIN,SLB,T,XOM",-0.018221399884408185,13218.329817520771,-0.06776300362661203,13899.808623309867
+2026-03-13,1460.0769911569953,10867.816259727779,12327.893250884774,8,"AMAT,AMT,CAT,FCX,LIN,MU,T,XOM",0.00042825035605420503,13218.329817520771,-0.06736377280098826,13845.24695865315
+2026-03-16,1401.7515420911943,11059.624341339217,12461.375883430412,8,"AMAT,AMT,ARM,CAT,LIN,MU,T,XOM",0.010827692114875997,13218.329817520771,-0.05726547487769784,13977.21579006982
+2026-03-17,1401.7515420911943,11225.221133427362,12626.972675518557,8,"AMAT,AMT,ARM,CAT,LIN,MU,T,XOM",0.013288804834812318,13218.329817520771,-0.044737659762307924,14045.1786817228
+2026-03-18,1401.7515420911943,11127.565967013647,12529.317509104842,8,"AMAT,AMT,ARM,CAT,LIN,MU,T,XOM",-0.007733854259703188,13218.329817520771,-0.052125519481489246,13896.50761864106
+2026-03-19,1401.7515420911943,11161.808435398025,12563.55997748922,8,"AMAT,AMT,ARM,CAT,LIN,MU,T,XOM",0.002732987519830532,13218.329817520771,-0.04953499035586628,13875.605004104074
+2026-03-20,1401.7515420911943,11103.642035507739,12505.393577598934,8,"AMAT,AMT,ARM,CAT,LIN,MU,T,XOM",-0.004629770542306955,13218.329817520771,-0.053935425259010183,13651.76200229013
+2026-03-23,1567.6839723906637,10998.78326251056,12566.467234901223,8,"AMAT,AMT,ARM,LIN,MU,NET,T,XOM",0.004883785298184673,13218.329817520771,-0.04931504899775685,13866.945306857064
+2026-03-24,1449.609745520194,11098.029397227387,12547.639142747581,8,"AMAT,ARM,LIN,MU,NET,PLTR,T,XOM",-0.001498280447614686,13218.329817520771,-0.05073944167168498,13788.619063887925
+2026-03-25,1449.609745520194,11303.518020916243,12753.127766436437,8,"AMAT,ARM,LIN,MU,NET,PLTR,T,XOM",0.01637667622977723,13218.329817520771,-0.03519370885024464,13870.268614219764
+2026-03-26,1449.609745520194,10960.884280383845,12410.49402590404,8,"AMAT,ARM,LIN,MU,NET,PLTR,T,XOM",-0.026866643760453668,13218.329817520771,-0.061114815772409625,13601.199090772567
+2026-03-27,1754.3129451274635,10504.505754547417,12258.818699674881,8,"AMAT,ARM,DDOG,LIN,MU,NET,PLTR,TGT",-0.012221538152516032,13218.329817520771,-0.07258943687227926,13363.16461114298
+2026-03-30,1694.422750766706,10240.785344479213,11935.208095245918,8,"AMAT,ARM,DDOG,EQIX,NET,PFE,PLTR,TGT",-0.026398188304844195,13218.329817520771,-0.09707139555362643,13244.658139706757
+2026-03-31,1694.422750766706,10709.500481776071,12403.923232542777,8,"AMAT,ARM,DDOG,EQIX,NET,PFE,PLTR,TGT",0.03927163511154519,13218.329817520771,-0.06161191286803169,13674.298465268192
+2026-04-01,1708.613244759228,10832.856509583351,12541.46975434258,8,"AMAT,APD,ARM,EQIX,NET,PFE,PLTR,TGT",0.01108895300471846,13218.329817520771,-0.051206171469637574,13785.203907697529
+2026-04-02,1708.613244759228,10807.492116520996,12516.105361280224,8,"AMAT,APD,ARM,EQIX,NET,PFE,PLTR,TGT",-0.0020224418317137394,13218.329817520771,-0.05312505179812921,13799.450865811135
+2026-04-06,1708.613244759228,10841.939891957165,12550.553136716393,8,"AMAT,APD,ARM,EQIX,NET,PFE,PLTR,TGT",0.002752275923046721,13218.329817520771,-0.05051899067605703,13841.088807290449
+2026-04-07,1708.613244759228,10766.80612683579,12475.419371595019,8,"AMAT,APD,ARM,EQIX,NET,PFE,PLTR,TGT",-0.005986490340538997,13218.329817520771,-0.05620304956690003,13882.345543797965
+2026-04-08,1708.613244759228,10971.177947523478,12679.791192282706,8,"AMAT,APD,ARM,EQIX,NET,PFE,PLTR,TGT",0.016381959964649973,13218.329817520771,-0.040741805710146295,14217.55221226642
+2026-04-09,1505.6245422938246,11081.421348490092,12587.045890783917,8,"AMAT,APD,ARM,EQIX,NET,PFE,TGT,VZ",-0.007314418675540724,13218.329817520771,-0.04775822176112554,14193.78438732285
+2026-04-10,1496.579020452167,10880.34713804496,12376.926158497126,8,"AMAT,APD,ARM,COST,EQIX,NET,PFE,TGT",-0.016693331708644732,13218.329817520771,-0.06365430963209684,14091.083558584216
+2026-04-13,1496.579020452167,11032.903322643035,12529.482343095202,8,"AMAT,APD,ARM,COST,EQIX,NET,PFE,TGT",0.012325853983813362,13218.329817520771,-0.0521130493742491,14287.504049990745
+2026-04-14,1496.579020452167,11030.4953063476,12527.074326799768,8,"AMAT,APD,ARM,COST,EQIX,NET,PFE,TGT",-0.0001921880114034158,13218.329817520771,-0.05229522188232516,14433.630428480397
+2026-04-15,1496.579020452167,11107.302129496056,12603.881149948224,8,"AMAT,APD,ARM,COST,EQIX,NET,PFE,TGT",0.0061312658602288295,13218.329817520771,-0.046484591930676555,14540.173032990007
+2026-04-16,1496.579020452167,11201.049377341622,12697.62839779379,8,"AMAT,APD,ARM,COST,EQIX,NET,PFE,TGT",0.007437966665208684,13218.329817520771,-0.03939237611069424,14569.659773857915
+2026-04-17,1496.579020452167,11374.266726728132,12870.8457471803,8,"AMAT,APD,ARM,COST,EQIX,NET,PFE,TGT",0.013641708826240828,13218.329817520771,-0.026288046609329152,14749.194492570083
+2026-04-20,2660.7984527023036,10344.380105414844,13005.178558117148,7,"AMAT,APD,ARM,COST,EQIX,PFE,TGT",0.010436983985009585,13218.329817520771,-0.01612543054577842,14748.386694660172
+2026-04-21,1358.1256126257813,11667.300115299366,13025.425727925147,8,"AMAT,APD,ARM,COST,CVS,EQIX,PFE,TGT",0.001556854426682408,13218.329817520771,-0.014593681067023412,14649.639635255777
+2026-04-22,1182.561445088596,12069.343234613452,13251.90467970205,8,"AMAT,APD,ARM,COST,CVS,EQIX,LRCX,TGT",0.017387451013701316,13251.90467970205,0.0,14835.657932927868
+2026-04-23,1096.8186105852424,12309.533271151213,13406.351881736455,8,"AMAT,APD,ARM,CVS,EQIX,LRCX,TGT,XLF",0.011654717247624902,13406.351881736455,0.0,14677.732687626787
+2026-04-24,1096.8186105852424,12685.777055214283,13782.595665799525,8,"AMAT,APD,ARM,CVS,EQIX,LRCX,TGT,XLF",0.028064591126809812,13782.595665799525,0.0,14851.954150241972
+2026-04-27,1096.8186105852424,12384.803265257982,13481.621875843224,8,"AMAT,APD,ARM,CVS,EQIX,LRCX,TGT,XLF",-0.021837235688713208,13782.595665799525,-0.021837235688713208,14840.067492664022
+2026-04-28,1096.8186105852424,12043.321211031624,13140.139821616865,8,"AMAT,APD,ARM,CVS,EQIX,LRCX,TGT,XLF",-0.025329449035967788,13782.595665799525,-0.04661355957621727,14688.061464298507
+2026-04-29,1096.8186105852424,12141.025128535754,13237.843739120995,8,"AMAT,APD,ARM,CVS,EQIX,LRCX,TGT,XLF",0.007435531039281518,13782.595665799525,-0.039524625106016176,14708.605948357199
+2026-04-30,1096.8186105852424,12336.248320170971,13433.066930756213,8,"AMAT,APD,ARM,CVS,EQIX,LRCX,TGT,XLF",0.014747355799214157,13782.595665799525,-0.025360153016070974,14882.32267752283
+2026-05-01,1096.8186105852424,12282.116358591127,13378.93496917637,8,"AMAT,APD,ARM,CVS,EQIX,LRCX,TGT,XLF",-0.0040297544751976,13782.595665799525,-0.02928771230116034,14927.145612836921
+2026-05-04,1096.8186105852424,12187.247431731286,13284.066042316528,8,"AMAT,APD,ARM,CVS,EQIX,LRCX,TGT,XLF",-0.007090917705961597,13782.595665799525,-0.03617095324939845,14881.629436613703
+2026-05-05,1096.8186105852424,12444.30299374709,13541.121604332331,8,"AMAT,APD,ARM,CVS,EQIX,LRCX,TGT,XLF",0.01935066877844105,13782.595665799525,-0.01752021660668701,14996.20653382526
+2026-05-06,1096.8186105852424,13060.866049284245,14157.684659869486,8,"AMAT,APD,ARM,CVS,EQIX,LRCX,TGT,XLF",0.04553264297839954,14157.684659869486,0.0,15244.628344227724
+2026-05-07,1096.8186105852424,12571.416974887947,13668.235585473189,8,"AMAT,APD,ARM,CVS,EQIX,LRCX,TGT,XLF",-0.03457126544029199,14157.684659869486,-0.03457126544029199,15197.724243081657
+2026-05-08,1096.8186105852424,12793.231119102085,13890.049729687327,8,"AMAT,APD,ARM,CVS,EQIX,LRCX,TGT,XLF",0.01622844022749259,14157.684659869486,-0.018903862927585946,15341.343317052024
+2026-05-11,1096.8186105852424,12855.943427512355,13952.762038097597,8,"AMAT,APD,ARM,CVS,EQIX,LRCX,TGT,XLF",0.004514908847031318,14157.684659869486,-0.0144743032985295,15395.554633848016
+2026-05-12,1096.8186105852424,12788.786574068334,13885.605184653576,8,"AMAT,APD,ARM,CVS,EQIX,LRCX,TGT,XLF",-0.004813158373994431,14157.684659869486,-0.019217794558394896,15325.398733073867
+2026-05-13,1096.8186105852424,13036.004834287334,14132.823444872576,8,"AMAT,APD,ARM,CVS,EQIX,LRCX,TGT,XLF",0.017803924058868326,14157.684659869486,-0.001756022654423206,15383.660097734248
+2026-05-14,1096.8186105852424,13134.377020835447,14231.19563142069,8,"AMAT,APD,ARM,CVS,EQIX,LRCX,TGT,XLF",0.0069605473337885915,14231.19563142069,0.0,15476.548267599112
+2026-05-15,1096.8186105852424,12756.216187561862,13853.034798147104,8,"AMAT,APD,ARM,CVS,EQIX,LRCX,TGT,XLF",-0.026572667755241364,14231.19563142069,-0.026572667755241364,15203.05716602871
+2026-05-18,1096.8186105852424,12688.930404246332,13785.749014831574,8,"AMAT,APD,ARM,CVS,EQIX,LRCX,TGT,XLF",-0.004857115014576419,14231.19563142069,-0.0313007162662865,15227.388741757506
+2026-05-19,1096.8186105852424,12679.69457567659,13776.513186261833,8,"AMAT,APD,ARM,CVS,EQIX,LRCX,TGT,XLF",-0.0006699547888043833,14231.19563142069,-0.03194970099033523,15176.225774954193
+2026-05-20,1096.8186105852424,13190.80888989821,14287.627500483452,8,"AMAT,APD,ARM,CVS,EQIX,LRCX,TGT,XLF",0.03710041193379099,14287.627500483452,0.0,15448.607694005876
+2026-05-21,1096.8186105852424,13734.54468881303,14831.363299398272,8,"AMAT,APD,ARM,CVS,EQIX,LRCX,TGT,XLF",0.038056409218145015,14831.363299398272,0.0,15553.360013356809
+2026-05-22,1096.8186105852424,13858.552101124427,14955.37071170967,8,"AMAT,APD,ARM,CVS,EQIX,LRCX,TGT,XLF",0.008361160724613015,14955.37071170967,0.0,15668.466267967575
+2026-05-26,1096.8186105852424,13975.553942178843,15072.372552764085,8,"AMAT,APD,ARM,CVS,EQIX,LRCX,TGT,XLF",0.007823399587334023,15072.372552764085,0.0,15823.625689672777
diff --git a/tests/fixtures/portfolio_backtest/portfolio_summary.csv b/tests/fixtures/portfolio_backtest/portfolio_summary.csv
new file mode 100644
index 0000000..fcc8c9b
--- /dev/null
+++ b/tests/fixtures/portfolio_backtest/portfolio_summary.csv
@@ -0,0 +1,2 @@
+initial_cash,final_equity,total_return,benchmark_return,max_drawdown,sharpe_ratio,trades,win_rate
+10000.0,15072.372552764085,0.5072372552764086,0.5823625689672778,-0.10211053509473034,1.5211408575289322,42,0.5714285714285714
diff --git a/tests/fixtures/portfolio_backtest/portfolio_trades.csv b/tests/fixtures/portfolio_backtest/portfolio_trades.csv
new file mode 100644
index 0000000..a5c53c1
--- /dev/null
+++ b/tests/fixtures/portfolio_backtest/portfolio_trades.csv
@@ -0,0 +1,43 @@
+ticker,entry_date,exit_date,entry_price,exit_price,qty,cost_basis,exit_value,return_pct,exit_reason
+LULU,2025-05-29,2025-06-16,317.0899963378906,241.2899932861328,3.1505251239003678,1000.0,759.4299958077188,-0.24057000419228125,SELL_SIGNAL
+UBER,2025-05-29,2025-08-05,84.30000305175781,89.38999938964844,11.850533378826123,1000.0,1058.2598523287754,0.0582598523287754,SELL_SIGNAL
+ARM,2025-05-29,2025-08-08,128.10000610351562,138.5,7.798594476199506,1000.0,1079.025229618678,0.07902522961867797,SELL_SIGNAL
+COIN,2025-06-16,2025-08-11,261.57000732421875,319.6199951171875,3.873206850636804,1014.1288731624454,1236.716400333704,0.2194864312236222,SELL_SIGNAL
+MDB,2025-08-08,2025-08-19,209.17999267578125,218.6100006103516,5.383296176904149,1127.2050599162874,1175.6655381382006,0.04299171459140916,SELL_SIGNAL
+PLTR,2025-08-19,2025-09-08,157.75,156.10000610351562,7.0922877114989795,1119.9283148037678,1105.9990488978267,-0.012437640625580282,SELL_SIGNAL
+AMD,2025-08-11,2025-09-09,172.27999877929688,155.82000732421875,6.513586159400008,1123.2838994897681,1013.9320960215745,-0.09735010313765269,SELL_SIGNAL
+SCHW,2025-05-29,2025-09-11,86.66069793701172,93.02495574951172,11.52771699030293,1000.0,1071.2929975529084,0.07129299755290841,SELL_SIGNAL
+SLB,2025-09-11,2025-10-10,35.53801727294922,31.286869049072266,32.57581661572933,1158.8387723425576,1018.1761133142932,-0.12138242384134168,SELL_SIGNAL
+C,2025-08-05,2025-10-15,90.0796890258789,98.2096939086914,12.053377823626374,1086.8513774411301,1182.574788077531,0.0880740574316341,SELL_SIGNAL
+ANET,2025-05-29,2025-11-12,86.37000274658203,134.97999572753906,11.566515783624125,1000.0,1559.6870028050414,0.5596870028050414,SELL_SIGNAL
+XLK,2025-05-29,2025-11-21,115.15689849853516,136.2237548828125,8.67512075286317,1000.0,1180.5757654938157,0.1805757654938156,SELL_SIGNAL
+QQQ,2025-05-29,2025-11-21,517.4254150390625,588.568603515625,1.930713047646841,1000.0,1135.2207251606546,0.13522072516065453,SELL_SIGNAL
+SMH,2025-05-29,2025-11-25,243.3228759765625,338.955322265625,4.105655894418354,1000.0,1390.2422828875317,0.3902422828875316,SELL_SIGNAL
+CVS,2025-09-08,2025-11-26,68.52015686035156,78.51912689208984,16.365226416055627,1122.4703514347352,1283.6983062904726,0.14363671579356785,SELL_SIGNAL
+ASML,2025-10-15,2025-11-26,1004.499755859375,1037.3330078125,1.1757232790125094,1182.1959426689184,1218.3969488078483,0.030621832500289825,SELL_SIGNAL
+AMD,2025-11-12,2025-12-01,258.8900146484375,219.75999450683597,4.612404701687249,1195.30082160594,1012.6084098741883,-0.15284220376113877,SELL_SIGNAL
+CRWD,2025-11-26,2025-12-01,501.5400085449219,504.1300048828125,2.321697164725034,1165.5896054403547,1169.2667657862542,0.0031547641886444655,SELL_SIGNAL
+MCD,2025-12-01,2026-01-08,301.88360595703125,307.16412353515625,3.866975203176457,1168.544963444777,1186.6082529668633,0.015457932802891206,SELL_SIGNAL
+ISRG,2025-11-21,2026-01-20,561.6099853515625,527.4400024414062,1.9949363428312041,1121.497667942675,1051.157020303807,-0.0627202798984896,SELL_SIGNAL
+BAC,2025-09-09,2026-01-22,49.74877166748047,52.15515899658203,22.74691109017797,1132.7636496153584,1185.1823958247578,0.04627509562758192,SELL_SIGNAL
+LLY,2026-01-08,2026-01-28,1081.52001953125,1020.337646484375,1.144358054514451,1238.8850304997118,1166.4639724746344,-0.058456641449502356,SELL_SIGNAL
+XLV,2025-12-01,2026-02-09,153.99842834472656,155.6800079345703,7.580443716400482,1168.544963444777,1178.9434143788737,0.008898631425737324,SELL_SIGNAL
+GS,2025-12-01,2026-02-24,802.6359252929688,897.5464477539062,1.4544283176151507,1168.544963444777,1304.1115530181805,0.11601315637334486,SELL_SIGNAL
+BA,2026-01-28,2026-03-02,241.58999633789065,229.7400054931641,5.178588519869488,1252.3475290797921,1188.5392260466513,-0.050950955347056404,SELL_SIGNAL
+HD,2026-01-22,2026-03-06,378.49951171875,355.5429992675781,3.311168225658112,1254.5300867169522,1176.0854193479602,-0.06252912401190636,SELL_SIGNAL
+UPS,2025-11-21,2026-03-11,91.81044006347656,99.1290054321289,12.203145628101973,1121.497667942675,1208.4760035679235,0.07755552072150573,SELL_SIGNAL
+KLAC,2026-01-20,2026-03-13,1482.3594970703125,1416.8316650390625,0.8331390822663778,1236.2478788568662,1179.237415303452,-0.04611572203960468,SELL_SIGNAL
+SLB,2026-03-04,2026-03-13,47.88999938964844,44.720001220703125,26.68674911617992,1279.3077065921495,1192.238021599112,-0.06806000194040562,SELL_SIGNAL
+FCX,2026-03-06,2026-03-16,59.22957611083984,57.80271911621094,20.572144521426033,1219.6990987937938,1187.9367654986966,-0.026041122213264156,SELL_SIGNAL
+CAT,2025-11-25,2026-03-23,564.2131958007812,700.3666381835938,2.0334049087248696,1148.4223042128674,1422.7048310296645,0.238834203942766,SELL_SIGNAL
+AMT,2026-03-13,2026-03-24,182.58567810058597,168.67466735839844,6.74643766782223,1233.0359322749325,1136.8151763446099,-0.07803564633578586,SELL_SIGNAL
+XOM,2026-03-05,2026-03-27,149.74362182617188,169.8372344970703,8.338238481256539,1249.8478777114242,1414.7272208694285,0.13191952884691238,AI_EXIT
+T,2026-03-11,2026-03-27,26.878684997558597,28.79859161376953,46.65414758032196,1255.25739403512,1342.230169510972,0.06928680594843706,AI_EXIT
+LIN,2026-02-09,2026-03-30,454.8123168945313,499.260009765625,2.802846768358059,1276.0452778951737,1397.949955637053,0.09553319137935312,AI_EXIT
+MU,2026-03-13,2026-03-30,425.9510803222656,321.79998779296875,2.8918881844617026,1233.0359322749325,929.678972875948,-0.24602442756010812,SELL_SIGNAL
+DDOG,2026-03-27,2026-04-01,114.4800033569336,118.66999816894533,10.69969367900959,1226.1270953865655,1268.4628966670475,0.034528069267676154,SELL_SIGNAL
+PLTR,2026-03-24,2026-04-09,154.77999877929688,130.49000549316406,8.099460677729045,1254.8894032150795,1055.8417696602007,-0.15861767024640605,SELL_SIGNAL
+VZ,2026-04-09,2026-04-10,47.071998596191406,46.040000915527344,26.715917725134133,1258.8304721256045,1228.7708756478044,-0.023878986998974394,SELL_SIGNAL
+NET,2026-03-23,2026-04-20,220.6499938964844,204.80999755859372,5.690077784087667,1256.7724007301954,1164.2194322501364,-0.07364338079534927,SELL_SIGNAL
+PFE,2026-03-30,2026-04-22,27.31905174255371,26.364803314208984,43.65326487587539,1193.7595614368793,1149.7588327330466,-0.03685895395122185,SELL_SIGNAL
+COST,2026-04-10,2026-04-23,997.0232543945312,1012.9102172851562,1.2402705510042664,1237.8163974894617,1255.026430596802,0.013903542675832714,SELL_SIGNAL
diff --git a/tests/test_daily_audit_summary.py b/tests/test_daily_audit_summary.py
new file mode 100644
index 0000000..d2baf19
--- /dev/null
+++ b/tests/test_daily_audit_summary.py
@@ -0,0 +1,82 @@
+from datetime import date
+
+import pandas as pd
+
+from src.daily_audit_summary import (
+    aggregate_execution_audit,
+    format_daily_audit_report,
+    load_execution_audit,
+    run_daily_audit_summary,
+)
+
+
+def _sample_audit_rows() -> pd.DataFrame:
+    return pd.DataFrame(
+        [
+            {
+                "timestamp": "2026-05-30T10:00:00+00:00",
+                "event_type": "SKIP_BUY",
+                "ticker": "AAPL",
+                "reason": "stale price data for AAPL",
+            },
+            {
+                "timestamp": "2026-05-30T10:05:00+00:00",
+                "event_type": "SKIP_EXIT",
+                "ticker": "MSFT",
+                "reason": "dry_run_only",
+            },
+            {
+                "timestamp": "2026-05-30T10:10:00+00:00",
+                "event_type": "BUY_ERROR",
+                "ticker": "GOOG",
+                "reason": "API rate limit",
+            },
+            {
+                "timestamp": "2026-05-30T10:15:00+00:00",
+                "event_type": "BUY_SUBMITTED",
+                "ticker": "NVDA",
+                "reason": "",
+            },
+        ]
+    )
+
+
+def test_aggregate_execution_audit_counts():
+    report = aggregate_execution_audit(_sample_audit_rows())
+    assert report["row_count"] == 4
+    assert report["skip_by_event"] == {"SKIP_BUY": 1, "SKIP_EXIT": 1}
+    assert report["skip_reason_counts"]["stale_price_data"] == 1
+    assert report["api_error_count"] == 1
+    assert report["stale_bar_count"] >= 1
+    assert report["orders_submitted_count"] == 1
+    assert "context_skip_counts" in report
+
+
+def test_format_daily_audit_report_includes_key_lines():
+    report = aggregate_execution_audit(_sample_audit_rows())
+    text = format_daily_audit_report(report)
+    assert "API errors: 1" in text
+    assert "stale_price_data" in text or "Stale bar" in text
+
+
+def test_load_execution_audit_filters_by_day(tmp_path):
+    path = tmp_path / "execution_audit.csv"
+    _sample_audit_rows().to_csv(path, index=False)
+    df = load_execution_audit(path, day=date(2026, 5, 30))
+    assert len(df) == 4
+    df_empty = load_execution_audit(path, day=date(2026, 1, 1))
+    assert df_empty.empty
+
+
+def test_run_daily_audit_summary_writes_artifacts(tmp_path):
+    audit = tmp_path / "audit.csv"
+    out = tmp_path / "daily"
+    _sample_audit_rows().to_csv(audit, index=False)
+    report = run_daily_audit_summary(
+        audit_path=audit,
+        output_dir=out,
+        day=date(2026, 5, 30),
+    )
+    assert report["row_count"] == 4
+    assert (out / "latest_summary.json").is_file()
+    assert list(out.glob("audit_*.json"))
diff --git a/tests/test_daily_audit_summary_schema.py b/tests/test_daily_audit_summary_schema.py
new file mode 100644
index 0000000..69024d0
--- /dev/null
+++ b/tests/test_daily_audit_summary_schema.py
@@ -0,0 +1,83 @@
+"""Schema regression for daily audit artifacts ([AGY])."""
+
+import json
+from datetime import date
+from pathlib import Path
+
+import pandas as pd
+import pytest
+
+from src.daily_audit_summary import (
+    DAILY_AUDIT_SUMMARY_KEYS,
+    SKIP_REASONS_CSV_COLUMNS,
+    aggregate_execution_audit,
+    run_daily_audit_summary,
+    validate_daily_audit_summary,
+    validate_skip_reasons_csv,
+    write_daily_audit_artifacts,
+)
+
+FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "audit_daily"
+GOLDEN_AUDIT_CSV = FIXTURE_DIR / "golden_execution_audit.csv"
+GOLDEN_SUMMARY_JSON = FIXTURE_DIR / "golden_latest_summary.json"
+
+
+@pytest.fixture(scope="module", autouse=True)
+def build_golden_summary_fixture():
+    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
+    df = pd.read_csv(GOLDEN_AUDIT_CSV)
+    report = aggregate_execution_audit(df)
+    report["generated_at"] = "2026-05-30T12:00:00Z"
+    validate_daily_audit_summary(report)
+    GOLDEN_SUMMARY_JSON.write_text(
+        json.dumps(report, indent=2, sort_keys=True),
+        encoding="utf-8",
+    )
+    write_daily_audit_artifacts(
+        report,
+        FIXTURE_DIR / "golden_output",
+        day=date(2026, 5, 30),
+    )
+    yield report
+
+
+def test_golden_execution_audit_context_skip_rates():
+    df = pd.read_csv(GOLDEN_AUDIT_CSV)
+    report = aggregate_execution_audit(df)
+    assert report["context_skip_counts"]["earnings"] == 1
+    assert report["context_skip_counts"]["macro_event"] == 1
+    assert report["context_skip_counts"]["stale"] == 1
+    assert report["context_skip_counts"]["other"] == 1
+    assert report["api_error_count"] == 1
+    assert sum(report["context_skip_rate_of_skips"].values()) == pytest.approx(1.0, abs=1e-3)
+
+
+def test_golden_latest_summary_schema():
+    report = json.loads(GOLDEN_SUMMARY_JSON.read_text(encoding="utf-8"))
+    validate_daily_audit_summary(report)
+    for key in DAILY_AUDIT_SUMMARY_KEYS:
+        assert key in report
+
+
+def test_golden_skip_reasons_csv_schema():
+    skip_csv = FIXTURE_DIR / "golden_output" / "skip_reasons_20260530.csv"
+    frame = validate_skip_reasons_csv(skip_csv)
+    assert list(frame.columns) == list(SKIP_REASONS_CSV_COLUMNS)
+
+
+def test_run_daily_audit_summary_matches_golden_counts(tmp_path):
+    out = tmp_path / "out"
+    report = run_daily_audit_summary(
+        audit_path=GOLDEN_AUDIT_CSV,
+        output_dir=out,
+        day=date(2026, 5, 30),
+    )
+    golden = json.loads(GOLDEN_SUMMARY_JSON.read_text(encoding="utf-8"))
+    for key in (
+        "row_count",
+        "api_error_count",
+        "stale_bar_count",
+        "context_skip_counts",
+        "skip_by_event",
+    ):
+        assert report[key] == golden[key]
diff --git a/tests/test_guard_impact_report.py b/tests/test_guard_impact_report.py
new file mode 100644
index 0000000..2f42813
--- /dev/null
+++ b/tests/test_guard_impact_report.py
@@ -0,0 +1,45 @@
+"""Guard impact report schema and delta helpers ([AGY])."""
+
+from types import SimpleNamespace
+
+from src.guard_impact_metrics import (
+    GUARD_IMPACT_REPORT_KEYS,
+    delta_metrics,
+    result_metrics,
+    validate_guard_impact_report,
+)
+
+
+def test_result_metrics_and_delta():
+    baseline = SimpleNamespace(
+        total_return=0.10,
+        max_drawdown=-0.08,
+        sharpe_ratio=1.1,
+        trades=20,
+        win_rate=0.55,
+    )
+    guarded = SimpleNamespace(
+        total_return=0.08,
+        max_drawdown=-0.07,
+        sharpe_ratio=1.0,
+        trades=17,
+        win_rate=0.52,
+    )
+    base = result_metrics(baseline)
+    guard = result_metrics(guarded)
+    delta = delta_metrics(base, guard)
+    assert delta["trade_count"] == -3
+    assert base["total_return_pct"] == 10.0
+
+
+def test_validate_guard_impact_report_keys():
+    report = {
+        "generated_at": "2026-05-30T00:00:00Z",
+        "baseline": {},
+        "with_crowding_guard": {},
+        "delta": {},
+        "crowding_guard_enabled_in_config": False,
+    }
+    validate_guard_impact_report(report)
+    for key in GUARD_IMPACT_REPORT_KEYS:
+        assert key in report
diff --git a/tests/test_leverage_stress_report.py b/tests/test_leverage_stress_report.py
new file mode 100644
index 0000000..6f81f4e
--- /dev/null
+++ b/tests/test_leverage_stress_report.py
@@ -0,0 +1,39 @@
+"""Leverage stress scenario math ([AGY])."""
+
+from pathlib import Path
+
+import pandas as pd
+import pytest
+
+from src.leverage_stress_report import (
+    LEVERAGE_STRESS_REPORT_KEYS,
+    build_leverage_stress_report,
+    load_equity_series,
+    validate_leverage_stress_report,
+)
+
+FIXTURE_EQUITY = (
+    Path(__file__).resolve().parent / "fixtures" / "portfolio_backtest" / "portfolio_equity.csv"
+)
+
+
+def test_load_equity_series_from_fixture():
+    series = load_equity_series(FIXTURE_EQUITY)
+    assert len(series) > 10
+    assert series.iloc[-1] > series.iloc[0]
+
+
+def test_leverage_stress_report_schema_and_worsens_under_gap():
+    equity = load_equity_series(FIXTURE_EQUITY)
+    report = build_leverage_stress_report(equity, leverage=2.0)
+    validate_leverage_stress_report(report)
+    for key in LEVERAGE_STRESS_REPORT_KEYS:
+        assert key in report
+    gap10 = next(row for row in report["scenarios"] if row["name"] == "gap_down_10pct")
+    assert gap10["max_drawdown_pct"] <= report["input"]["baseline_max_drawdown_pct"]
+
+
+def test_leverage_must_be_positive():
+    equity = pd.Series([100.0, 101.0, 99.0])
+    with pytest.raises(ValueError, match="leverage"):
+        build_leverage_stress_report(equity, leverage=0.0)
diff --git a/tests/test_llm_cache_report_schema.py b/tests/test_llm_cache_report_schema.py
new file mode 100644
index 0000000..3385e09
--- /dev/null
+++ b/tests/test_llm_cache_report_schema.py
@@ -0,0 +1,32 @@
+"""Schema regression for LLM cache monitoring ([AGY])."""
+
+import json
+from pathlib import Path
+
+import pytest
+
+from src.llm_cache_report import (
+    LLM_CACHE_REPORT_KEYS,
+    build_llm_cache_report,
+    validate_llm_cache_report,
+)
+
+FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "llm_monitoring"
+GOLDEN_CACHE = FIXTURE_DIR / "golden_llm_cache.json"
+
+
+def test_golden_llm_cache_report_schema():
+    report = build_llm_cache_report(GOLDEN_CACHE)
+    validate_llm_cache_report(report)
+    for key in LLM_CACHE_REPORT_KEYS:
+        assert key in report
+    assert report["entry_count"] == 3
+    assert report["unique_tickers"] == 2
+    assert report["approved_count"] == 2
+    assert report["rejected_count"] == 1
+
+
+def test_empty_cache_report():
+    report = build_llm_cache_report(FIXTURE_DIR / "missing_cache.json")
+    assert report["entry_count"] == 0
+    assert report["estimated_cache_hit_rate"] == 0.0
diff --git a/tests/test_ml_quality_report.py b/tests/test_ml_quality_report.py
new file mode 100644
index 0000000..428a8e5
--- /dev/null
+++ b/tests/test_ml_quality_report.py
@@ -0,0 +1,141 @@
+"""Unit tests for fold stability and calibration report generation."""
+
+import json
+from pathlib import Path
+
+import pandas as pd
+import pytest
+
+from src.ml_quality_report import (
+    FOLD_METRICS_COLUMNS,
+    build_calibration_report,
+    build_fold_stability_report,
+    evaluate_ml_quality_promotion_gates,
+    evaluate_walk_forward_oos_metrics,
+    normalize_fold_metrics_df,
+    regenerate_reports_from_fold_metrics_csv,
+    write_ml_quality_reports,
+)
+
+
+def _sample_metrics_df() -> pd.DataFrame:
+    metrics_df = pd.DataFrame(
+        [
+            {"regime": "BULL", "fold": 1, "roc_auc": 0.52, "brier_score": 0.22, "test_size": 100},
+            {"regime": "BULL", "fold": 2, "roc_auc": 0.53, "brier_score": 0.24, "test_size": 100},
+            {"regime": "BEAR", "fold": 1, "roc_auc": 0.51, "brier_score": 0.28, "test_size": 80},
+            {"regime": "BEAR", "fold": 2, "roc_auc": 0.52, "brier_score": 0.26, "test_size": 80},
+        ]
+    )
+    metrics_df.attrs["calibration_rows"] = [
+        {"regime": "BULL", "fold": 1, "y_true": 1, "y_prob": 0.7},
+        {"regime": "BULL", "fold": 1, "y_true": 0, "y_prob": 0.3},
+        {"regime": "BEAR", "fold": 1, "y_true": 1, "y_prob": 0.6},
+        {"regime": "BEAR", "fold": 1, "y_true": 0, "y_prob": 0.4},
+    ]
+    return metrics_df
+
+
+def test_normalize_fold_metrics_schema():
+    df = normalize_fold_metrics_df(pd.DataFrame([{"regime": "BULL", "fold": 1, "roc_auc": 0.5}]))
+    for col in ("regime", "fold", "roc_auc", "brier_score", "test_size"):
+        assert col in df.columns
+
+
+def test_fold_stability_report_flags_high_variance():
+    metrics_df = _sample_metrics_df()
+    report = build_fold_stability_report(metrics_df)
+    assert report["fold_count"] == 4
+    assert report["roc_auc"]["std"] is not None
+    assert "BULL" in report["by_regime"]
+    assert report["high_variance_warning"] is False
+
+
+def test_fold_stability_warns_on_wide_roc_auc_spread():
+    metrics_df = pd.DataFrame(
+        [
+            {"regime": "NEUTRAL", "fold": 1, "roc_auc": 0.40, "brier_score": 0.25, "test_size": 50},
+            {"regime": "NEUTRAL", "fold": 2, "roc_auc": 0.55, "brier_score": 0.25, "test_size": 50},
+        ]
+    )
+    report = build_fold_stability_report(metrics_df)
+    assert report["high_variance_warning"] is True
+
+
+def test_write_ml_quality_reports(tmp_path: Path):
+    paths = write_ml_quality_reports(tmp_path, _sample_metrics_df())
+    assert paths["fold_metrics"].is_file()
+    stability = json.loads(paths["fold_stability"].read_text(encoding="utf-8"))
+    assert stability["fold_count"] == 4
+    calibration = json.loads(paths["calibration_report"].read_text(encoding="utf-8"))
+    assert calibration["bin_count"] >= 1
+    written = pd.read_csv(paths["fold_metrics"])
+    assert list(written.columns[: len(FOLD_METRICS_COLUMNS)]) == list(FOLD_METRICS_COLUMNS)
+
+
+def test_regenerate_from_csv_round_trip(tmp_path: Path):
+    source = tmp_path / "fold_metrics.csv"
+    _sample_metrics_df().to_csv(source, index=False)
+    paths = regenerate_reports_from_fold_metrics_csv(source, tmp_path)
+    assert paths["fold_stability"].is_file()
+
+
+def test_calibration_report_empty_without_rows():
+    report, bins = build_calibration_report(pd.DataFrame())
+    assert report["bin_count"] == 0
+    assert bins.empty
+
+
+def test_ml_quality_promotion_gates_require_auc_brier_and_stability():
+    metadata = {"oos_metrics": {"avg_roc_auc": 0.55}}
+    stability = {"high_variance_warning": False, "roc_auc": {"std": 0.02}}
+    calibration = {"overall_avg_brier_score": 0.22}
+    result = evaluate_ml_quality_promotion_gates(metadata, stability, calibration)
+    assert result["passed"]
+
+    bad_auc = evaluate_ml_quality_promotion_gates(
+        {"oos_metrics": {"avg_roc_auc": 0.48}}, stability, calibration
+    )
+    assert not bad_auc["passed"]
+
+
+def test_build_promotion_dual_gate_integration():
+    xgboost = pytest.importorskip("xgboost")
+    del xgboost
+    from src.ml_model import build_promotion_report
+
+    stability = {"high_variance_warning": False, "roc_auc": {"std": 0.01}}
+    calibration = {"overall_avg_brier_score": 0.20, "bin_count": 1}
+    portfolio = {
+        "total_return": 0.10,
+        "benchmark_return": 0.08,
+        "max_drawdown": -0.10,
+        "sharpe_ratio": 1.0,
+    }
+    report = build_promotion_report(
+        {"oos_metrics": {"avg_roc_auc": 0.55}},
+        None,
+        challenger_portfolio=portfolio,
+        fold_stability_report=stability,
+        calibration_report=calibration,
+        require_portfolio_oos=True,
+    )
+    assert report["decision"] == "PROMOTE"
+    assert report["ml_quality_gate_passed"]
+    assert report["portfolio_gate_passed"]
+
+
+def test_evaluate_walk_forward_oos_metrics_empty_without_data():
+    class _StubModel:
+        models = {}
+        feature_columns = []
+        prediction_horizon = 20
+        target_return_threshold = 0.0
+
+    metrics_df = evaluate_walk_forward_oos_metrics(
+        _StubModel(),
+        {},
+        test_start=pd.Timestamp("2024-01-01"),
+        test_end=pd.Timestamp("2024-07-01"),
+    )
+    assert metrics_df.empty
diff --git a/tests/test_ml_quality_report_schema.py b/tests/test_ml_quality_report_schema.py
new file mode 100644
index 0000000..eded23e
--- /dev/null
+++ b/tests/test_ml_quality_report_schema.py
@@ -0,0 +1,59 @@
+"""Schema regression for ML quality artifacts ([AGY])."""
+
+import json
+from pathlib import Path
+
+import pandas as pd
+import pytest
+
+from src.ml_quality_report import (
+    CALIBRATION_BINS_COLUMNS,
+    CALIBRATION_REPORT_KEYS,
+    FOLD_METRICS_COLUMNS,
+    FOLD_STABILITY_REPORT_KEYS,
+    validate_calibration_artifacts,
+    validate_fold_metrics_csv,
+    write_ml_quality_reports,
+)
+from tests.test_ml_quality_report import _sample_metrics_df
+
+FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "ml_quality"
+
+
+@pytest.fixture(scope="module", autouse=True)
+def build_fixtures_once(tmp_path_factory):
+    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
+    paths = write_ml_quality_reports(FIXTURE_DIR, _sample_metrics_df(), file_prefix="golden")
+    yield paths
+
+
+def test_fold_metrics_csv_schema():
+    frame = validate_fold_metrics_csv(FIXTURE_DIR / "golden_fold_metrics.csv")
+    assert list(frame.columns[: len(FOLD_METRICS_COLUMNS)]) == list(FOLD_METRICS_COLUMNS)
+    assert frame["roc_auc"].between(0, 1).all()
+    assert frame["brier_score"].between(0, 1).all()
+
+
+def test_fold_stability_report_schema():
+    report = json.loads(
+        (FIXTURE_DIR / "golden_fold_stability_report.json").read_text(encoding="utf-8")
+    )
+    for key in FOLD_STABILITY_REPORT_KEYS:
+        assert key in report
+    assert "mean" in report["roc_auc"]
+
+
+def test_calibration_report_and_bins_schema():
+    report, bins_df = validate_calibration_artifacts(
+        FIXTURE_DIR / "golden_model_calibration_report.json",
+        FIXTURE_DIR / "golden_model_calibration_bins.csv",
+    )
+    for key in CALIBRATION_REPORT_KEYS:
+        assert key in report
+    assert list(bins_df.columns) == list(CALIBRATION_BINS_COLUMNS)
+    assert (bins_df["count"] > 0).any()
+
+
+def test_calibration_bins_required_columns_only():
+    bins_df = pd.read_csv(FIXTURE_DIR / "golden_model_calibration_bins.csv")
+    assert set(CALIBRATION_BINS_COLUMNS).issubset(bins_df.columns)
diff --git a/tests/test_model_governance.py b/tests/test_model_governance.py
index 37ff928..05cd9d1 100644
--- a/tests/test_model_governance.py
+++ b/tests/test_model_governance.py
@@ -10,10 +10,23 @@ from src.ml_model import (
     build_promotion_report,
     find_latest_archived_champion,
     load_model_metadata,
+    portfolio_oos_beats_champion,
     restore_archived_champion,
     save_model_bundle,
 )
-from src.train_ai_model import _evaluate_rollback_need
+from src.portfolio_backtest_validation import PortfolioBacktestThresholds
+from src.model_governance import evaluate_rollback_need as _evaluate_rollback_need
+
+
+def _good_ml_quality_reports() -> tuple[dict, dict]:
+    return (
+        {
+            "high_variance_warning": False,
+            "roc_auc": {"std": 0.01, "mean": 0.52},
+            "roc_auc_std_warn_threshold": 0.05,
+        },
+        {"overall_avg_brier_score": 0.20, "bin_count": 2, "regimes": {}},
+    )
 
 
 def _sample_training_data() -> dict[str, pd.DataFrame]:
@@ -53,10 +66,107 @@ class ModelGovernanceTest(unittest.TestCase):
         challenger_metadata = {"oos_metrics": {"avg_roc_auc": 0.63}}
         champion_metadata = {"oos_metrics": {"avg_roc_auc": 0.60}}
 
-        report = build_promotion_report(challenger_metadata, champion_metadata)
+        report = build_promotion_report(
+            challenger_metadata,
+            champion_metadata,
+            require_portfolio_oos=False,
+            require_ml_quality=False,
+        )
+
+        self.assertEqual(report["decision"], "PROMOTE")
+        self.assertTrue(report["auc_gate_passed"])
+
+    def test_build_promotion_report_requires_portfolio_gates(self) -> None:
+        challenger_metadata = {"oos_metrics": {"avg_roc_auc": 0.63}}
+        champion_metadata = {"oos_metrics": {"avg_roc_auc": 0.60}}
+        weak_portfolio = {
+            "total_return": 0.02,
+            "benchmark_return": 0.20,
+            "max_drawdown": -0.30,
+            "sharpe_ratio": -0.2,
+        }
+        strong_portfolio = {
+            "total_return": 0.15,
+            "benchmark_return": 0.10,
+            "max_drawdown": -0.08,
+            "sharpe_ratio": 1.1,
+        }
+
+        stability, calibration = _good_ml_quality_reports()
+        report = build_promotion_report(
+            challenger_metadata,
+            champion_metadata,
+            challenger_portfolio=weak_portfolio,
+            champion_portfolio=strong_portfolio,
+            portfolio_thresholds=PortfolioBacktestThresholds(max_drawdown_floor=-0.20),
+            fold_stability_report=stability,
+            calibration_report=calibration,
+        )
+
+        self.assertEqual(report["decision"], "RETAIN_CHAMPION")
+        self.assertTrue(report["auc_gate_passed"])
+        self.assertTrue(report["ml_quality_gate_passed"])
+        self.assertFalse(report["portfolio_gate_passed"])
+
+    def test_build_promotion_report_promotes_on_auc_and_portfolio(self) -> None:
+        challenger_metadata = {"oos_metrics": {"avg_roc_auc": 0.63}}
+        champion_metadata = {"oos_metrics": {"avg_roc_auc": 0.60}}
+        challenger_portfolio = {
+            "total_return": 0.12,
+            "benchmark_return": 0.10,
+            "max_drawdown": -0.08,
+            "sharpe_ratio": 1.2,
+        }
+        champion_portfolio = {
+            "total_return": 0.08,
+            "benchmark_return": 0.10,
+            "max_drawdown": -0.10,
+            "sharpe_ratio": 0.9,
+        }
+
+        stability, calibration = _good_ml_quality_reports()
+        report = build_promotion_report(
+            challenger_metadata,
+            champion_metadata,
+            challenger_portfolio=challenger_portfolio,
+            champion_portfolio=champion_portfolio,
+            fold_stability_report=stability,
+            calibration_report=calibration,
+        )
 
         self.assertEqual(report["decision"], "PROMOTE")
-        self.assertIn("challenger_avg_roc_auc", report["reason"])
+        self.assertTrue(report["ml_quality_gate_passed"])
+        self.assertTrue(report["portfolio_gate_passed"])
+        self.assertTrue(report["portfolio_vs_champion_passed"])
+        self.assertTrue(portfolio_oos_beats_champion(challenger_portfolio, champion_portfolio))
+
+    def test_build_promotion_report_rejects_poor_training_metrics(self) -> None:
+        challenger_metadata = {"oos_metrics": {"avg_roc_auc": 0.63}}
+        champion_metadata = {"oos_metrics": {"avg_roc_auc": 0.60}}
+        stability = {
+            "high_variance_warning": True,
+            "roc_auc": {"std": 0.12},
+            "roc_auc_std_warn_threshold": 0.05,
+        }
+        calibration = {"overall_avg_brier_score": 0.20, "bin_count": 1}
+        challenger_portfolio = {
+            "total_return": 0.12,
+            "benchmark_return": 0.10,
+            "max_drawdown": -0.08,
+            "sharpe_ratio": 1.2,
+        }
+
+        report = build_promotion_report(
+            challenger_metadata,
+            champion_metadata,
+            challenger_portfolio=challenger_portfolio,
+            fold_stability_report=stability,
+            calibration_report=calibration,
+            require_portfolio_oos=True,
+        )
+
+        self.assertEqual(report["decision"], "RETAIN_CHAMPION")
+        self.assertFalse(report["ml_quality_gate_passed"])
 
     def test_save_model_bundle_persists_metadata_json(self) -> None:
         bundle = {
diff --git a/tests/test_model_governance_rollback.py b/tests/test_model_governance_rollback.py
new file mode 100644
index 0000000..b8921c1
--- /dev/null
+++ b/tests/test_model_governance_rollback.py
@@ -0,0 +1,65 @@
+"""Rollback decision path tests without xgboost ([AGY])."""
+
+from pathlib import Path
+from unittest.mock import patch
+
+from src.model_governance import (
+    ROLLBACK_MAX_DRAWDOWN,
+    ROLLBACK_MIN_TOTAL_RETURN,
+    ROLLBACK_MIN_WIN_RATE,
+    evaluate_rollback_need,
+    resolve_rollback_decision,
+)
+
+
+def test_skip_rollback_after_promotion() -> None:
+    report = resolve_rollback_decision("PROMOTE", None, None, restore=False)
+    assert report["decision"] == "SKIP_ROLLBACK_AFTER_PROMOTION"
+
+
+def test_no_rollback_when_performance_ok() -> None:
+    report = resolve_rollback_decision(
+        "RETAIN_CHAMPION",
+        {"total_return": 0.10, "max_drawdown": -0.05, "win_rate": 0.55},
+        None,
+        restore=False,
+    )
+    assert report["decision"] == "NO_ROLLBACK_NEEDED"
+
+
+def test_rollback_restores_archived_champion() -> None:
+    archived = (Path("/tmp/model.joblib"), Path("/tmp/meta.json"))
+    with patch("src.model_governance._restore_archived_champion") as restore:
+        report = resolve_rollback_decision(
+            "RETAIN_CHAMPION",
+            {
+                "total_return": ROLLBACK_MIN_TOTAL_RETURN - 0.01,
+                "max_drawdown": -0.05,
+                "win_rate": 0.55,
+            },
+            archived,
+            restore=True,
+        )
+    assert report["decision"] == "ROLLBACK_TO_ARCHIVED_CHAMPION"
+    restore.assert_called_once()
+
+
+def test_no_rollback_available_without_archive() -> None:
+    report = resolve_rollback_decision(
+        "RETAIN_CHAMPION",
+        {
+            "total_return": -0.20,
+            "max_drawdown": ROLLBACK_MAX_DRAWDOWN - 0.01,
+            "win_rate": ROLLBACK_MIN_WIN_RATE - 0.01,
+        },
+        None,
+        restore=False,
+    )
+    assert report["decision"] == "NO_ROLLBACK_AVAILABLE"
+
+
+def test_evaluate_rollback_need_flags_breaches() -> None:
+    decision = evaluate_rollback_need(
+        {"total_return": -0.12, "max_drawdown": -0.25, "win_rate": 0.30}
+    )
+    assert decision["should_rollback"]
diff --git a/tests/test_portfolio_backtest_gate.py b/tests/test_portfolio_backtest_gate.py
new file mode 100644
index 0000000..3ad0db1
--- /dev/null
+++ b/tests/test_portfolio_backtest_gate.py
@@ -0,0 +1,135 @@
+"""Threshold gate tests for portfolio backtest outputs ([AGY])."""
+
+from pathlib import Path
+
+import pandas as pd
+import pytest
+
+from src.portfolio_backtest_validation import (
+    PortfolioBacktestThresholds,
+    check_portfolio_backtest_thresholds,
+    check_portfolio_summary_thresholds,
+)
+
+
+def _write_summary(path: Path, row: dict) -> None:
+    pd.DataFrame([row]).to_csv(path, index=False)
+
+
+def _write_minimal_bundle(dir_path: Path, summary_row: dict) -> None:
+    dir_path.mkdir(parents=True, exist_ok=True)
+    _write_summary(dir_path / "portfolio_summary.csv", summary_row)
+    pd.DataFrame(
+        [{"date": "2024-01-01", "equity": 10000.0, "cash": 10000.0, "positions_value": 0.0,
+          "positions_count": 0, "open_symbols": "", "daily_return": 0.0,
+          "running_max": 10000.0, "drawdown": 0.0, "benchmark_equity": 10000.0},
+         {"date": "2024-01-02", "equity": 10100.0, "cash": 5000.0, "positions_value": 5100.0,
+          "positions_count": 1, "open_symbols": "SPY", "daily_return": 0.01,
+          "running_max": 10100.0, "drawdown": 0.0, "benchmark_equity": 10050.0}]
+    ).to_csv(dir_path / "portfolio_equity.csv", index=False)
+    pd.DataFrame(
+        columns=[
+            "ticker", "entry_date", "exit_date", "entry_price", "exit_price",
+            "qty", "cost_basis", "exit_value", "return_pct", "exit_reason",
+        ]
+    ).to_csv(dir_path / "portfolio_trades.csv", index=False)
+
+
+def test_summary_thresholds_pass_in_memory():
+    summary = {
+        "total_return": 0.10,
+        "benchmark_return": 0.12,
+        "max_drawdown": -0.08,
+        "sharpe_ratio": 1.2,
+    }
+    result = check_portfolio_summary_thresholds(summary)
+    assert result.passed
+
+
+def test_thresholds_pass(tmp_path: Path):
+    _write_minimal_bundle(
+        tmp_path,
+        {
+            "initial_cash": 10000.0,
+            "final_equity": 11000.0,
+            "total_return": 0.10,
+            "benchmark_return": 0.12,
+            "max_drawdown": -0.08,
+            "sharpe_ratio": 1.2,
+            "trades": 0,
+            "win_rate": 0.0,
+        },
+    )
+    result = check_portfolio_backtest_thresholds(tmp_path)
+    assert result.passed
+    assert not result.failures
+
+
+def test_thresholds_fail_max_drawdown(tmp_path: Path):
+    _write_minimal_bundle(
+        tmp_path,
+        {
+            "initial_cash": 10000.0,
+            "final_equity": 9000.0,
+            "total_return": -0.10,
+            "benchmark_return": 0.05,
+            "max_drawdown": -0.35,
+            "sharpe_ratio": -0.5,
+            "trades": 0,
+            "win_rate": 0.0,
+        },
+    )
+    result = check_portfolio_backtest_thresholds(
+        tmp_path, PortfolioBacktestThresholds(max_drawdown_floor=-0.20)
+    )
+    assert not result.passed
+    assert any("max_drawdown" in f for f in result.failures)
+
+
+def test_thresholds_fail_benchmark_gap(tmp_path: Path):
+    _write_minimal_bundle(
+        tmp_path,
+        {
+            "initial_cash": 10000.0,
+            "final_equity": 9500.0,
+            "total_return": 0.05,
+            "benchmark_return": 0.30,
+            "max_drawdown": -0.10,
+            "sharpe_ratio": 0.5,
+            "trades": 0,
+            "win_rate": 0.0,
+        },
+    )
+    result = check_portfolio_backtest_thresholds(
+        tmp_path, PortfolioBacktestThresholds(min_return_vs_benchmark=-0.15)
+    )
+    assert not result.passed
+    assert any("benchmark" in f for f in result.failures)
+
+
+def test_cli_exit_codes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
+    import subprocess
+    import sys
+
+    _write_minimal_bundle(
+        tmp_path,
+        {
+            "initial_cash": 10000.0,
+            "final_equity": 11000.0,
+            "total_return": 0.10,
+            "benchmark_return": 0.12,
+            "max_drawdown": -0.08,
+            "sharpe_ratio": 1.2,
+            "trades": 0,
+            "win_rate": 0.0,
+        },
+    )
+    script = Path(__file__).resolve().parents[1] / "scripts" / "check_portfolio_backtest_gate.py"
+    env = {**dict(__import__("os").environ), "PYTHONPATH": "."}
+    ok = subprocess.run(
+        [sys.executable, str(script), "--dir", str(tmp_path)],
+        cwd=Path(__file__).resolve().parents[1],
+        env=env,
+        check=False,
+    )
+    assert ok.returncode == 0
diff --git a/tests/test_portfolio_backtest_golden.py b/tests/test_portfolio_backtest_golden.py
new file mode 100644
index 0000000..a24e641
--- /dev/null
+++ b/tests/test_portfolio_backtest_golden.py
@@ -0,0 +1,42 @@
+"""Golden regression for portfolio backtest CSV outputs ([AGY] slice)."""
+
+from pathlib import Path
+
+import pytest
+
+from src.portfolio_backtest_validation import (
+    load_summary_row,
+    validate_portfolio_backtest_dir,
+)
+
+FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "portfolio_backtest"
+
+
+@pytest.fixture
+def golden_summary() -> dict:
+    return load_summary_row(FIXTURE_DIR / "portfolio_summary.csv")
+
+
+def test_fixture_dir_passes_schema_and_trade_count():
+    result = validate_portfolio_backtest_dir(FIXTURE_DIR)
+    assert result["equity_rows"] >= 100
+    assert result["trades_rows"] == result["summary"]["trades"]
+
+
+def test_fixture_matches_golden_summary_metrics(golden_summary: dict):
+    validate_portfolio_backtest_dir(FIXTURE_DIR, golden_summary=golden_summary)
+
+
+def test_rejects_missing_summary_column(tmp_path: Path, golden_summary: dict):
+    import pandas as pd
+
+    bad = tmp_path / "portfolio_summary.csv"
+    pd.DataFrame([{"initial_cash": 10000.0}]).to_csv(bad, index=False)
+    (tmp_path / "portfolio_equity.csv").write_text(
+        (FIXTURE_DIR / "portfolio_equity.csv").read_text()
+    )
+    (tmp_path / "portfolio_trades.csv").write_text(
+        (FIXTURE_DIR / "portfolio_trades.csv").read_text()
+    )
+    with pytest.raises(ValueError, match="missing columns"):
+        validate_portfolio_backtest_dir(tmp_path, golden_summary=golden_summary)
diff --git a/tests/test_promotion_rollback_path.py b/tests/test_promotion_rollback_path.py
new file mode 100644
index 0000000..5c9bb26
--- /dev/null
+++ b/tests/test_promotion_rollback_path.py
@@ -0,0 +1,76 @@
+"""Promotion reject and rollback decision path tests ([AGY])."""
+
+from pathlib import Path
+from unittest.mock import patch
+
+import pytest
+
+from src.portfolio_backtest_validation import PortfolioBacktestThresholds
+
+pytest.importorskip("xgboost")
+from src.ml_model import build_promotion_report  # noqa: E402
+
+
+def _good_ml() -> tuple[dict, dict]:
+    return (
+        {"high_variance_warning": False, "roc_auc": {"std": 0.01}},
+        {"overall_avg_brier_score": 0.20, "bin_count": 1},
+    )
+
+
+def _good_portfolio() -> dict:
+    return {
+        "total_return": 0.12,
+        "benchmark_return": 0.10,
+        "max_drawdown": -0.08,
+        "sharpe_ratio": 1.1,
+    }
+
+
+class TestChallengerRejection:
+    def test_rejects_weaker_auc(self) -> None:
+        stability, calibration = _good_ml()
+        report = build_promotion_report(
+            {"oos_metrics": {"avg_roc_auc": 0.48}},
+            {"oos_metrics": {"avg_roc_auc": 0.55}},
+            challenger_portfolio=_good_portfolio(),
+            fold_stability_report=stability,
+            calibration_report=calibration,
+            require_portfolio_oos=True,
+        )
+        assert report["decision"] == "RETAIN_CHAMPION"
+        assert not report["auc_gate_passed"]
+
+    def test_rejects_failed_portfolio_gate(self) -> None:
+        stability, calibration = _good_ml()
+        report = build_promotion_report(
+            {"oos_metrics": {"avg_roc_auc": 0.60}},
+            {"oos_metrics": {"avg_roc_auc": 0.50}},
+            challenger_portfolio={
+                "total_return": -0.05,
+                "benchmark_return": 0.20,
+                "max_drawdown": -0.35,
+                "sharpe_ratio": -0.3,
+            },
+            fold_stability_report=stability,
+            calibration_report=calibration,
+            portfolio_thresholds=PortfolioBacktestThresholds(max_drawdown_floor=-0.20),
+        )
+        assert report["decision"] == "RETAIN_CHAMPION"
+        assert report["auc_gate_passed"]
+        assert not report["portfolio_gate_passed"]
+
+    def test_rejects_high_fold_variance(self) -> None:
+        report = build_promotion_report(
+            {"oos_metrics": {"avg_roc_auc": 0.60}},
+            None,
+            challenger_portfolio=_good_portfolio(),
+            fold_stability_report={
+                "high_variance_warning": True,
+                "roc_auc": {"std": 0.12},
+            },
+            calibration_report={"overall_avg_brier_score": 0.20},
+            require_ml_quality=True,
+        )
+        assert report["decision"] == "RETAIN_CHAMPION"
+        assert not report["ml_quality_gate_passed"]
diff --git a/tests/test_report_performance.py b/tests/test_report_performance.py
index 4e5fa68..f20bbe4 100644
--- a/tests/test_report_performance.py
+++ b/tests/test_report_performance.py
@@ -1,14 +1,19 @@
-import sys
-import os
-import pandas as pd
-from unittest.mock import patch
+import json
 from io import StringIO
+from pathlib import Path
+from unittest.mock import patch
+
+import pandas as pd
 import pytest
 
-# Add src to path to allow imports
-sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
+from src.report_performance import (
+    analyze_slippage,
+    compute_slippage_report,
+    format_slippage_report,
+    run_weekly_slippage_report,
+    write_slippage_artifacts,
+)
 
-from report_performance import analyze_slippage
 
 @pytest.fixture
 def create_log_files(tmp_path):
@@ -19,7 +24,7 @@ def create_log_files(tmp_path):
         "timestamp": ["2023-01-01T10:00:00Z", "2023-01-01T10:00:00Z"],
         "ticker": ["TICKER1", "TICKER2"],
         "close": [100.0, 200.0],
-        "volume": [1000, 500]
+        "volume": [1000, 500],
     }
     pd.DataFrame(signals_data).to_csv(signals_file, index=False)
 
@@ -34,30 +39,70 @@ def create_log_files(tmp_path):
         "filled_qty": [10, 5],
         "filled_avg_price": [101.0, 199.0],
         "reason": ["some_reason", "some_reason"],
-        "event": ["STATUS_CHECK", "STATUS_CHECK"]
+        "event": ["STATUS_CHECK", "STATUS_CHECK"],
     }
     pd.DataFrame(orders_data).to_csv(orders_file, index=False)
 
-    return str(signals_file), str(orders_file)
+    return signals_file, orders_file
 
-@patch('sys.stdout', new_callable=StringIO)
+
+@patch("sys.stdout", new_callable=StringIO)
 def test_analyze_slippage_with_usd_cost(mock_stdout, create_log_files):
     signals_path, orders_path = create_log_files
 
-    # Call analyze_slippage with the paths to the temporary log files
     analyze_slippage(signals_path=signals_path, orders_path=orders_path)
 
     output = mock_stdout.getvalue()
-    
-    # Check for TICKER1 (buy) slippage: (101 - 100) * 10 = 10
-    # Check for TICKER2 (sell) slippage: (200 - 199) * 5 = 5
-    # Total slippage: 10 + 5 = 15
-
     assert "Total Slippage Cost: $15.00" in output
     assert "TICKER1" in output
     assert "TICKER2" in output
-    # Check for the summary table values
-    # For TICKER1, total_slippage_usd is 10.0
-    # For TICKER2, total_slippage_usd is 5.0
     assert "10.0" in output
     assert "5.0" in output
+
+
+def test_compute_slippage_report(create_log_files):
+    signals_path, orders_path = create_log_files
+    report = compute_slippage_report(signals_path=signals_path, orders_path=orders_path)
+    assert report is not None
+    assert report.matched_trades == 2
+    assert report.total_slippage_usd == pytest.approx(15.0)
+    assert "TICKER1" in {row["ticker"] for row in report.by_ticker}
+
+
+def test_write_slippage_artifacts(create_log_files, tmp_path: Path):
+    signals_path, orders_path = create_log_files
+    report = compute_slippage_report(signals_path=signals_path, orders_path=orders_path)
+    assert report is not None
+    run_dir = write_slippage_artifacts(report, tmp_path, run_id="test_run")
+    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
+    assert summary["total_slippage_usd"] == pytest.approx(15.0)
+    assert (tmp_path / "latest_summary.json").is_file()
+
+
+def test_run_weekly_slippage_report_writes_no_data_summary(tmp_path: Path):
+    missing_signals = tmp_path / "signals.csv"
+    missing_orders = tmp_path / "orders.csv"
+    report = run_weekly_slippage_report(
+        lookback_days=7,
+        output_dir=tmp_path / "out",
+        signals_path=missing_signals,
+        orders_path=missing_orders,
+    )
+    assert report.status == "no_data"
+    latest = json.loads((tmp_path / "out" / "latest_summary.json").read_text(encoding="utf-8"))
+    assert latest["status"] == "no_data"
+    assert latest["matched_trades"] == 0
+
+
+@patch("sys.stdout", new_callable=StringIO)
+def test_run_weekly_slippage_report(mock_stdout, create_log_files, tmp_path: Path):
+    signals_path, orders_path = create_log_files
+    report = run_weekly_slippage_report(
+        lookback_days=9999,
+        output_dir=tmp_path,
+        signals_path=signals_path,
+        orders_path=orders_path,
+    )
+    assert report is not None
+    assert format_slippage_report(report)
+    assert list(tmp_path.glob("slippage_*"))
diff --git a/tests/test_retrain_holdout.py b/tests/test_retrain_holdout.py
new file mode 100644
index 0000000..7201992
--- /dev/null
+++ b/tests/test_retrain_holdout.py
@@ -0,0 +1,35 @@
+"""Holdout slicing for retrain portfolio promotion ([Cursor] slice)."""
+
+import pandas as pd
+
+from src.retrain_holdout import (
+    exclude_holdout_from_ticker_data,
+    portfolio_holdout_window,
+    slice_ticker_data_to_holdout,
+)
+
+
+def _frame(start: str, days: int) -> pd.DataFrame:
+    dates = pd.date_range(start, periods=days, freq="B")
+    return pd.DataFrame(
+        {
+            "date": dates,
+            "open": 1.0,
+            "high": 1.0,
+            "low": 1.0,
+            "close": 1.0,
+            "volume": 100.0,
+        }
+    )
+
+
+def test_holdout_window_and_slices_do_not_overlap():
+    ticker_data = {"AAPL": _frame("2024-01-01", 400)}
+    holdout_start, holdout_end = portfolio_holdout_window(ticker_data, months=6)
+    fit = exclude_holdout_from_ticker_data(ticker_data, holdout_start)
+    holdout = slice_ticker_data_to_holdout(ticker_data, holdout_start, holdout_end)
+
+    fit_max = pd.to_datetime(fit["AAPL"]["date"]).max()
+    holdout_min = pd.to_datetime(holdout["AAPL"]["date"]).min()
+    assert fit_max < holdout_min
+    assert holdout_end >= holdout_min
diff --git a/tests/test_retrain_notifications.py b/tests/test_retrain_notifications.py
new file mode 100644
index 0000000..a9a8c69
--- /dev/null
+++ b/tests/test_retrain_notifications.py
@@ -0,0 +1,65 @@
+"""Retrain failure and partial-success Telegram paths ([AGY])."""
+
+from pathlib import Path
+from unittest.mock import MagicMock
+
+import pytest
+
+from src import retrain_notifications as retrain
+
+
+def test_notify_champion_retained_sends_info(monkeypatch):
+    calls: list[tuple[str, str]] = []
+    monkeypatch.setattr(
+        retrain,
+        "notify_info",
+        lambda title, body: calls.append((title, body)) or True,
+    )
+    retrain.notify_champion_retained_if_needed(
+        {"decision": "RETAIN_CHAMPION"},
+        Path("logs/ml/model_promotion_report.json"),
+    )
+    assert len(calls) == 1
+    assert "champion retained" in calls[0][0].lower()
+
+
+def test_notify_champion_retained_skips_on_promote(monkeypatch):
+    monkeypatch.setattr(retrain, "notify_info", MagicMock())
+    retrain.notify_champion_retained_if_needed(
+        {"decision": "PROMOTE"},
+        Path("logs/ml/model_promotion_report.json"),
+    )
+    retrain.notify_info.assert_not_called()
+
+
+def test_notify_retrain_failure_logs_and_errors(monkeypatch):
+    log_calls: list[str] = []
+    error_calls: list[tuple[str, str]] = []
+    monkeypatch.setattr(
+        retrain,
+        "notify_error",
+        lambda title, err: error_calls.append((title, str(err))) or True,
+    )
+
+    def _append(status, metrics_df, elapsed):
+        log_calls.append(status)
+
+    retrain.notify_retrain_failure(
+        RuntimeError("data load failed"),
+        12.5,
+        append_retrain_log=_append,
+    )
+    assert log_calls == ["failure"]
+    assert error_calls[0][0] == "AI Retrain Failed"
+    assert "data load failed" in error_calls[0][1]
+
+
+def test_run_retrain_cli_exits_on_main_failure(monkeypatch):
+    monkeypatch.setattr(retrain, "notify_retrain_failure", MagicMock())
+    with pytest.raises(SystemExit) as exc:
+        retrain.run_retrain_cli(
+            lambda: (_ for _ in ()).throw(ValueError("train crash")),
+            lambda *a, **k: None,
+        )
+    assert exc.value.code == 1
+    retrain.notify_retrain_failure.assert_called_once()
```
