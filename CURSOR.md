# CURSOR.md

Behavioral guidelines to reduce common LLM coding mistakes and ensure the Trading Bot's reliability. These rules govern how **Cursor** (primary interactive implementation agent) operates in this workspace.

**Tradeoff:** These guidelines bias toward caution over speed. For trading applications, security and correctness are paramount.

## 1. Think Before Coding
**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First
**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior quant engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes
**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution & Harness Engineering
**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests in `tests/harness/` for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure all tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```
Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

## 5. Codex / AGY Review Handoff

After completing Cursor implementation work, leave enough evidence for separate reviewers.

Include:
- changed files and why each changed;
- tests or commands actually run;
- tests not run and why;
- known residual risks or assumptions;
- areas Codex should review carefully;
- areas AGY should review if architecture, strategy, or risk logic changed.

Codex reviews with `docs/agent_review_harness.md` and `AGENTS.md` (review-only section).

When **Cursor implementation + `[AGY]` tests** are complete, close the pass (do not skip Codex):

```bash
RUN_ID=cursor_$(date +%Y%m%dT%H%M%S) bash scripts/run_pass_complete.sh "summary of this pass"
```

This runs pytest → `review_packet.md` → Codex scoped review → writes `NEXT_TODO.codex.md`.

Read `reports/agent_pipeline/<run_id>/NEXT_TODO.codex.md` before starting the next feature.  
If Codex fails (credits/CLI), fix and re-run with `SKIP_PYTEST=1` after local pytest is already green.

Legacy (packet only, no Codex): `bash scripts/run_cursor_post_workflow.sh`

**Cursor automation:** apply project skill `.cursor/skills/pass-complete/SKILL.md` at the end of every implementation pass (replaces Gemini CLI auto-calling the orchestrator).

**Review-only (no headless implementer):**

```bash
.venv/bin/python scripts/agent_orchestrator.py --run-codex-review --scoped-review
```

**Optional legacy headless implementer (Gemini CLI):**

```bash
.venv/bin/python scripts/agent_orchestrator.py --task-file <task.md> --run-gemini --run-codex-review
```

## 6. Multi-Agent Working Tree Rule

Only one implementation agent may edit the working tree at a time.

Default:
- **Cursor** edits (primary).
- **Codex** reviews in read-only mode.
- **AGY** reviews in read-only or plan-only mode.
- **Gemini CLI** is optional legacy headless implementer; do not run it on the same branch while Cursor is editing.

Codex or AGY may implement fixes only when explicitly asked, and preferably on a separate branch.
Never let multiple agents edit the same branch concurrently.

### 7. Automatic Documentation Maintenance
**Keep the entry point (README.md) synchronized with code changes.**

- After completing a feature or changing a workflow, assess if `README.md` needs an update.
- If a new script, config, or command is added, include it in the relevant README section.
- Perform README updates in the same pass as the code changes whenever possible.
- Before committing, double-check if the README accurately reflects the new state of the repository.

---

## Environment & Runtime (Project-Specific Instructions)
- **Python Version**: This project **MUST** run on **Python 3.12**.
- **Virtual Environment**: Always use the virtual environment located at `.venv/`.
- **Execution Command**: Use `.venv/bin/python` for all shell commands instead of `python` or `python3`.
- **PYTHONPATH**: When running scripts from the root, prefix with `PYTHONPATH=.`.
  - Example: `PYTHONPATH=. .venv/bin/python src/main.py`
- **Linting/Formatting**: Use tools compatible with Python 3.12.
- **Dependency Management**: Update `requirements.txt` using `.venv/bin/pip`.

## Risk Management & Operations
- **Circuit Breaker**: Threshold is set in `config/strategy_config.json` via `max_portfolio_drawdown_pct`.
- **Correlation Guard**: Enabled via `correlation_guard_enabled` in config.
- **Performance Reporting**: Run `PYTHONPATH=. .venv/bin/python src/report_performance.py` for slippage and P&L analysis.
- **Fault Injection**: Any new risk logic or API interaction must be tested against `tests/harness/test_fault_injection.py`.

## Task Ownership Labels

When splitting work across agents, label tasks in `TODO.md` or task files:
- `[Cursor]` — main integration, `main.py`, orders, portfolio/risk guards, config wiring.
- `[AGY]` — **pytest**, `tests/harness/`, regression/fault-injection, calibration & backtest report scripts (no live order paths). Invoke AGY explicitly after Cursor lands the feature under test.
- `[Gemini]` — **deprecated for tests**; docs-only or mechanical non-trading edits via `--run-gemini` if no AGY session available.
- `[Either]` — README or non-risk utilities (still only one implementer at a time).

**Suggested split per feature:** Cursor implements → AGY test pass → Codex review → Cursor merge fixes.
