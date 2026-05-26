# AGENTS.md

## Project overview
- This repository is a Python trading bot.
- Prefer small, targeted edits over broad rewrites.
- Do not scan the whole repository unless explicitly asked.
- Before reading large files, list candidate files and ask or choose the smallest relevant set.

## Environment
- Use Python 3.11+.
- Prefer existing project tooling and dependencies.
- Do not add new production dependencies unless explicitly requested.

## Common commands
- Inspect files: `find . -maxdepth 3 -type f | head -100`
- Run tests when available: `pytest`
- Run a focused test instead of the full suite when changing a small area.

## Coding style
- Keep functions small and explicit.
- Preserve existing public function names unless the user asks for a refactor.
- Prefer pathlib for filesystem paths.
- Add clear error handling around file I/O and external API calls.
- Avoid silent fallback behavior in trading/data code.

## Data layout
- Raw price data should use: `data/raw/{ticker}/{period}.csv`
- Do not remove existing cache compatibility unless explicitly asked.
- When changing data schemas, update both read and write paths.

## Workflow rules
- First summarize the intended change.
- Then inspect only the relevant files.
- Default to the lightweight/standard model for routine edits, commands, and small debugging tasks.
- Recommend switching to a stronger model when the task involves high-risk trading logic, data leakage analysis, broad architecture changes, or complex backtest/strategy reasoning.
- After editing, show the changed files and the reason for each change.
- If tests are not run, explain why.
- Never claim tests passed unless they were actually executed.

## Context management
- Keep responses concise.
- Do not paste entire files unless necessary.
- Prefer diffs, function names, and short snippets.
- If context usage is high, summarize current state and suggest starting a new session.
