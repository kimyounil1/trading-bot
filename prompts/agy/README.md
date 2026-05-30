# AGY session prompts

Copy a task file into Antigravity/AGY after **Cursor** commits `[cursor]` implementation.

**Do not** implement `src/main.py` or order paths in AGY. Commit results with `[agy]` tag.

After AGY pytest is green:

```bash
RUN_ID=<same_pass_id> bash scripts/run_pass_complete.sh
```

Then read `reports/agent_pipeline/<run_id>/NEXT_TODO.codex.md` in Cursor.
