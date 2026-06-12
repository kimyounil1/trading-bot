# AGENTS.md

## Project overview
- This repository is a Python trading bot.
- Work autonomously in build mode.
- Prefer coherent, end-to-end fixes over tiny step-by-step changes.
- Do not ask for confirmation before ordinary code inspection, edits, refactors, or tests.
- Avoid unrelated rewrites. Fix the requested problem and stop.

## Environment
- Use Python 3.11+.
- Prefer the repository virtual environment at `.venv/` for all Python commands.
- When `.venv` exists, use `.venv/bin/python`, `.venv/bin/pip`, and tools invoked via `.venv/bin/...` by default instead of system Python.
- Prefer existing project tooling and dependencies.
- Do not add new production dependencies unless clearly necessary.
- Ask before adding production dependencies if there is a reasonable no-dependency alternative.

## Common commands
- Inspect files: `find . -maxdepth 3 -type f | head -100`
- Search code: `rg "<pattern>"`
- Run tests when available: `.venv/bin/python -m pytest`
- Run focused tests for small/local changes.
- Run broader tests when the change touches shared logic, trading logic, data schemas, or public behavior.
- For syntax sanity checks, use `.venv/bin/python -m compileall <path>`.
- Run the Gemini CLI Review Harness after changing agent instructions, workflow docs, skills, or guardrails: `bash scripts/run_gemini_review_harness.sh`.

## Coding style
- Keep functions small and explicit.
- Preserve existing public function names unless the user asks for a refactor.
- Prefer pathlib for filesystem paths.
- Add clear error handling around file I/O and external API calls.
- Avoid silent fallback behavior in trading/data code.
- When changing data schemas, update both read and write paths.
- Be careful with ticker casing. Normalize instruments consistently, usually with `str(...).upper()`.

## Data layout
- Raw price data should use: `data/raw/{ticker}/{period}.csv`
- Do not remove existing cache compatibility unless explicitly asked or clearly obsolete.

## Autonomy rules
- In build mode, proceed without asking for ordinary implementation choices.
- Make reasonable assumptions and continue.
- Batch related edits into coherent changes.
- Do not ask "Should I continue?" after each small step.
- Do not ask about minor naming, formatting, file organization, or implementation details.
- If multiple reasonable approaches exist, choose the simplest safe approach and mention the assumption afterward.

## Patch discipline
- Do not rewrite or paste an entire long function unless explicitly requested.
- Prefer small, surgical edits using exact surrounding anchors.
- If a function is long, patch only the changed blocks.
- Do not include full before/after copies of long functions in the response.
- Never attempt a full-function replacement when the replacement may exceed the output limit.
- Use targeted patches or small scripts for mechanical edits instead of generating huge code blocks.
- After a failed edit due to length, switch to smaller patches immediately.
- Do not repeat the same failed patch strategy.

## Loop prevention and stopping rules
- Do not run the same command more than twice with the same arguments.
- Do not inspect the same file repeatedly unless it changed.
- Do not repeatedly edit the same section without new evidence.
- If two fix attempts fail, stop and explain the blocker.
- After making a fix, run the most relevant test once.
- If the same test fails twice for the same reason, stop and summarize the failure.
- When the requested task is complete, stop immediately and provide a final summary.
- Do not continue searching for unrelated improvements after completing the requested task.
- Prefer one focused completion pass over open-ended exploration.

## Ask before high-risk actions
Ask the user only before:
- deleting large files or directories
- changing public APIs or major product behavior in a way that may break users
- modifying secrets, credentials, `.env` files, deployment settings, or production configs
- running migrations against production data
- committing, pushing, deploying, publishing, or trading with real money
- installing new production dependencies when avoidable
- making broad architecture changes unrelated to the requested task

## Workflow rules
- For simple tasks, inspect, edit, test, and summarize without asking first.
- For broad tasks, make a brief internal plan and execute it.
- Inspect the files needed to complete the task; avoid unnecessary full-repo reading, but do not block on confirmation just to inspect relevant files.
- Do not paste entire files unless necessary.
- Prefer diffs, function names, and short snippets.
- After editing, show the changed files and the reason for each change.
- If tests are not run, explain why.
- Never claim tests passed unless they were actually executed.

## Cursor / Codex / AGY Review Harness
- **Cursor IDE** is the primary interactive implementation environment. Follow `CURSOR.md` when implementing in Cursor.
- **Codex** is the default reviewer, verifier, and planning agent unless the user explicitly asks Codex to implement fixes.
- **AGY** owns **`[AGY]` test and harness slices** (preferred over Gemini CLI); optional reviewer for architecture, strategy, and risk (`AGY.md`).
- **Gemini CLI** is legacy headless (`--run-gemini`), **docs/low-risk only** — weaker default model than AGY; do not use for pytest or trading paths.
- The review harness lives in `docs/agent_review_harness.md` and `codex_harness/agent_contract.json` (when present).
- After Cursor + `[AGY]` tests, run **`bash scripts/run_pass_complete.sh`** (preferred) or follow project skill `.cursor/skills/pass-complete/SKILL.md`.
- **Codex budget:** follow [`docs/codex_review_policy.md`](docs/codex_review_policy.md) — use `SKIP_CODEX=1` or `run_pass_light.sh` for follow-ups/docs/tests; **one Codex review per Phase slice**, not per fix iteration.
- Legacy packet-only: `bash scripts/run_cursor_post_workflow.sh` or `SKIP_CODEX=1` pass (no Codex credits).
- For **review-only** without the wrapper: `.venv/bin/python scripts/agent_orchestrator.py --run-id <id> --run-codex-review --scoped-review --ignore-artifacts`.
- For legacy headless implement + review: `.venv/bin/python scripts/agent_orchestrator.py --task "..." --run-gemini --run-codex-review`.
- When changing `AGENTS.md`, `CURSOR.md`, `AGY.md`, `GEMINI.md`, workflow docs, guardrails, handoff rules, or eval cases, run `bash scripts/run_gemini_review_harness.sh` (legacy script name).
- **README Maintenance**: During review, verify if `README.md` needs updates. If missing, flag and include required text in the next plan.
- Before final reporting on broad agent-harness work, prefer `bash scripts/codex_pre_final_check.sh` when available.

### Multi-agent working tree rule
Only one implementation agent may edit the working tree at a time. Default: Cursor edits production code; **AGY edits tests when assigned `[AGY]`**; Codex reviews read-only. AGY or Codex may touch non-test code only when explicitly asked, preferably on a separate branch.

**Cursor sub-agents** (in-session `explore` / `ci-investigator` / read-only `shell`) may run in parallel for investigation only; they must not edit files. See `CURSOR.md` §7.

**Task labels:** `[Cursor]` runtime · `[Research]` (AGY offline) · `[AGY-test]` pytest · `[AGY-risk]` read-only strategy review. See `CURSOR.md` Task Labels and `AGY.md` invocation modes.

### Codex (review-only)
When reviewing implementation work:
1. Read `reports/agent_pipeline/<run_id>/review_packet.md` when available.
2. Lead with high-risk findings (orders, positions, risk guards, data schemas).
3. Verify test claims; run focused safe checks when appropriate.
4. Do not edit files during review unless explicitly asked to fix.
5. End with `# NEXT_TODO` (or `# NEXT_TODO for Cursor`) suitable for the next implementer.

## Context management
- Keep responses concise.
- Prefer diffs, function names, and short snippets.
- If context usage is high, summarize current state and continue with the most important next step instead of repeatedly asking the user.
