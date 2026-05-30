---
name: pass-complete
description: >-
  Close a Cursor+AGY development pass: run pytest, invoke the agent orchestrator
  for Codex scoped review, read NEXT_TODO.codex.md, and loop on fixes. Use when
  finishing implementation, after [AGY] tests, before marking TODO [x], or when
  the user says pass complete, Codex review, or run_pass_complete.
---
# Pass complete (Cursor-first)

Replace the legacy pattern where **Gemini CLI** called `agent_orchestrator.py --run-gemini`.
In this repo **Cursor** implements, **AGY** owns `[AGY]` tests, **Codex** reviews via the orchestrator.

## When to apply

- After Cursor feature work **and** `[AGY]` pytest/harness work are done on the branch.
- AGY tasks live under `prompts/agy/*.md` — run in a **separate AGY account session**, then return here.
- Before checking `[x]` on any `TODO.md` item (Definition of Done §4).
- When the user asks to close a pass, run Codex review, or check `NEXT_TODO`.

## Do not

- Run `--run-gemini` unless the user explicitly requests legacy headless mode.
- Skip Codex because credits failed once — report failure and retry with `SKIP_PYTEST=1`.
- Mark TODO complete without reading `NEXT_TODO.codex.md` when Codex succeeded.

## Steps (execute in the shell)

1. Choose `RUN_ID` (e.g. `phase20_ci`, `cursor_$(date +%Y%m%dT%H%M%S)`).

2. Run pass closure:

```bash
cd <repo-root>
RUN_ID=<run_id> bash scripts/run_pass_complete.sh "<one-line summary of this pass>"
```

Use `SKIP_PYTEST=1` only if pytest already passed in this session.  
Use `FULL_PYTEST=1` only when the full ML stack (e.g. xgboost) is installed.

3. Read outputs:
   - `reports/agent_pipeline/<run_id>/NEXT_TODO.codex.md` — **primary queue**
   - `reports/agent_pipeline/<run_id>/CODEX_REVIEW_AND_TODO.md` — full review if needed
   - `reports/agent_pipeline/<run_id>/review_packet.md` — handoff context

4. If Codex reports blocking issues (P0/P1 or test failures):
   - Fix in Cursor (or delegate `[AGY]` items to an AGY session).
   - Re-run step 2 with the same or new `RUN_ID` until clean or user stops.

5. Record workload (optional):

```bash
PYTHONPATH=. .venv/bin/python scripts/agent_workload_report.py --record
```

6. Tag commits: `[cursor]` for production code, `[agy]` for test-only commits.

## AGY is not invoked by the orchestrator

The orchestrator **does not** open AGY. Before step 2, for **multi-account token balancing** (preferred):
- User runs a **separate AGY session** for `[AGY]` tests after Cursor commits (do not duplicate tests in Cursor).
- Cursor may write tests only when AGY quota is exhausted for the week or the change is trivial (≤2 test files, no `main.py`).

Check balance: `PYTHONPATH=. .venv/bin/python scripts/agent_workload_report.py`

## Phase report to user

When all items in a Phase section are `[x]` and Codex is clean, summarize for the user:
- what shipped, test commands run, `RUN_ID`(s), and residual risks from Codex.

## Reference

- `scripts/run_pass_complete.sh` — pytest + `agent_orchestrator.py --run-codex-review --scoped-review --ignore-artifacts`
- `docs/agent_review_harness.md`, `CURSOR.md`, `AGY.md`
