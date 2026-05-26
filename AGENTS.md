# AGENTS.md

## Project overview
- This repository is a Python trading bot.
- Work autonomously in build mode.
- Prefer coherent, end-to-end fixes over tiny step-by-step changes.
- Do not ask for confirmation before ordinary code inspection, edits, refactors, or tests.
- Avoid unrelated rewrites. Fix the requested problem and stop.

## Environment
- Use Python 3.11+.
- Prefer existing project tooling and dependencies.
- Do not add new production dependencies unless clearly necessary.
- Ask before adding production dependencies if there is a reasonable no-dependency alternative.

## Common commands
- Inspect files: `find . -maxdepth 3 -type f | head -100`
- Search code: `rg "<pattern>"`
- Run tests when available: `pytest`
- Run focused tests for small/local changes.
- Run broader tests when the change touches shared logic, trading logic, data schemas, or public behavior.
- For syntax sanity checks, use `python -m compileall <path>`.

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

## Context management
- Keep responses concise.
- Prefer diffs, function names, and short snippets.
- If context usage is high, summarize current state and continue with the most important next step instead of repeatedly asking the user.
