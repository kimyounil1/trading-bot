# AGY session prompts

Copy a task file into Antigravity/AGY. Label the task header with one mode:

| Mode | When | Commit tag |
|------|------|------------|
| **`[Research]`** | Offline sweeps, calibration, `logs/ml/` reports (`TODO.md` §4–§5) | `[agy]` or `[research]` |
| **`[AGY-test]`** | pytest/fixtures after Cursor or Research lands code | `[agy]` |
| **`[AGY-risk]`** | Read-only strategy/risk review on a diff | (no commit unless asked) |

**`[Research]` / `[AGY-test]`:** do not edit `src/main.py` or order paths.

**`[Research]` handoff:** AGY experiments → Cursor runtime wiring (if needed) → `[AGY-test]` → pass close.

After `[AGY-test]` pytest is green:

```bash
RUN_ID=<same_pass_id> bash scripts/run_pass_complete.sh
```

Then read `reports/agent_pipeline/<run_id>/NEXT_TODO.codex.md` in Cursor.
