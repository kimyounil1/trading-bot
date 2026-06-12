# Agent Review Harness

This harness defines how **Codex** (and optionally **AGY**) review, validate, and plan follow-up work after an implementation agent has changed this repository. It is not the trading runtime harness and it is not a "Codex implements everything" workflow.

**Default flow:** Cursor implements → **AGY adds `[AGY]` tests** → post-workflow → Codex reviews read-only → optional AGY for architecture/risk on large strategy diffs.

## Roles

| Artifact | Purpose |
|----------|---------|
| **Cursor IDE** | Primary interactive implementation environment |
| `CURSOR.md` | Working rules for Cursor when editing this repository |
| `AGENTS.md` | Shared repository rules; includes Codex review-only section |
| `AGY.md` | Optional second-review rules for AGY (architecture, strategy, risk) |
| `GEMINI.md` | Legacy / optional rules for Gemini CLI headless implementation |
| `codex_harness/agent_contract.json` | Machine-readable review contract (when present) |
| `codex_harness/evals/gemini_review_requests.jsonl` | Representative review requests (when present) |
| `reports/agent_pipeline/<run_id>/review_packet.md` | Deterministic handoff packet for reviewers |

## Multi-Agent Working Tree Rule

Only one implementation agent may edit the working tree at a time.

Default:
- **Cursor** edits.
- **Codex** reviews in read-only mode.
- **AGY** implements **`[AGY]` test/harness slices** when invoked; otherwise read-only/plan-only for strategy/risk.
- **Gemini CLI** (`--run-gemini`) is legacy, **docs/low-risk only** — not for tests (weaker default model than AGY).

Codex or AGY may implement fixes only when explicitly asked, and preferably on a separate branch.
Never let multiple agents edit the same branch concurrently.

### Cursor sub-agents (in-session, read-only)

Inside a Cursor chat, the main agent may spawn **read-only** sub-agents (`explore`, `ci-investigator`, `shell` with `readonly: true`) for parallel investigation. Details: `CURSOR.md` §7.

- Sub-agents **do not** edit the working tree and **do not** count as a second implementer.
- They **do not** replace **AGY** (`[AGY]` tests) or **Codex** (scoped pass review).
- Only the main Cursor session produces commits and `review_packet.md` handoff.

### Task labels (who implements what)

| Label | Implementer | Notes |
|-------|-------------|-------|
| `[Cursor]` | Cursor | `main.py`, orders, runtime flags |
| `[Research]` | AGY | Offline sweeps, `logs/ml/`, no champion swap |
| `[AGY-test]` / `[AGY]` | AGY | pytest after Cursor or Research |
| `[AGY-risk]` | AGY read-only | Strategy/risk memo; does not replace Codex `NEXT_TODO` |

Details: `CURSOR.md` Task Labels · `AGY.md` invocation modes · `TODO.md` §4–§5 examples.

## Default Codex Stance

When the user asks Codex to check implementation work, Codex should review first and avoid editing files unless explicitly asked to fix the issues.

Codex should:

1. Inspect `git status --short` (or `reports/agent_pipeline/<run_id>/git_status.txt`).
2. Inspect targeted diffs for changed files.
3. Compare against `AGENTS.md`, `CURSOR.md`, and project rules.
4. Choose focused verification commands.
5. Run safe checks or explain what should be run.
6. Report findings first, then a concrete next-step plan.

## Run Structural Harness Checks

```bash
bash scripts/run_gemini_review_harness.sh
```

Use this after changing `AGENTS.md`, `CURSOR.md`, `AGY.md`, `GEMINI.md`, review policy, guardrails, handoff rules, or eval catalogs. (Script name is legacy; behavior is agent-agnostic.)

For a local pre-final check:

```bash
bash scripts/codex_pre_final_check.sh
```

## Cursor → Post-Workflow → Codex Pipeline

After Cursor (or any single implementer) finishes work, run:

```bash
RUN_ID=cursor_001 bash scripts/run_cursor_post_workflow.sh
```

The script creates a local report directory under:

```text
reports/agent_pipeline/<run_id>/
```

It collects:

- `git_status.txt`
- `changed_files.txt`
- `git_diff_stat.txt`
- `git_diff.patch`
- `review_harness.log` (legacy alias: `gemini_review_harness.log`)
- `runtime_harness.log`
- `review_packet.md`
- `NEXT_TODO.md`
- `summary.json`

The intended loop is:

1. **Cursor** implements the change in the IDE (production paths).
2. **AGY** implements `[AGY]` pytest/harness work (sequential; one implementer at a time).
3. **`bash scripts/run_pass_complete.sh`** (required): pytest → post-workflow packet → **Codex** scoped review.
4. Read **`NEXT_TODO.codex.md`** — confirm no blocking findings; implement follow-ups in Cursor.
5. Repeat. Do **not** mark TODO `[x]` or start the next feature until step 3–4 succeed.
6. Use **Gemini CLI** only for explicit `[Gemini]` docs/mechanical tasks if AGY is unavailable.

Shortcut for packet-only (no Codex): `run_cursor_post_workflow.sh` — not sufficient for Definition of Done.

This repository does not automatically invoke Cursor from the orchestrator. Cursor is IDE-driven; the pipeline only collects diffs and runs checks.

## External Orchestrator

Local CLI orchestrator (Codex review + optional Gemini CLI):

```bash
# Review-only after Cursor edits (recommended default)
.venv/bin/python scripts/agent_orchestrator.py --run-codex-review --scoped-review

# Legacy: headless Gemini implement + review
.venv/bin/python scripts/agent_orchestrator.py --task-file prompts/task.md --run-gemini --run-codex-review
```

The orchestrator performs:

1. Optional **Gemini CLI** implementation pass with `gemini --prompt` (`--run-gemini` only).
2. `scripts/run_cursor_post_workflow.sh` to collect diffs, logs, review packet, draft `NEXT_TODO.md`.
3. Optional **Codex** review pass with `codex exec` in `read-only` sandbox mode.
4. `CODEX_REVIEW_AND_TODO.md` and, when Codex succeeds, `NEXT_TODO.codex.md`.

Safe defaults:

- Gemini does not run unless `--run-gemini` is provided.
- Codex does not run unless `--run-codex-review` is provided.
- Codex runs with `--sandbox read-only --ask-for-approval never`.
- Gemini `yolo` mode is refused by the orchestrator.
- Reports live under `reports/agent_pipeline/<run_id>/` (gitignored).

Dry-run example:

```bash
.venv/bin/python scripts/agent_orchestrator.py \
  --task "Review current changes and plan next steps" \
  --dry-run
```

### Workflow Examples

#### 1. Cursor + Codex (recommended)

```bash
# 1. Implement in Cursor, run tests
PYTHONPATH=. .venv/bin/python -m pytest

# 2. Collect review packet
RUN_ID=cursor_feature_x bash scripts/run_cursor_post_workflow.sh

# 3. Codex review only
.venv/bin/python scripts/agent_orchestrator.py --run-id cursor_feature_x --run-codex-review --scoped-review
```

#### 2. Review-Only Mode

Review existing (uncommitted) changes without launching Gemini:

```bash
.venv/bin/python scripts/agent_orchestrator.py --run-codex-review --scoped-review
```

#### 3. Legacy Bounded Loop (Gemini ↔ Codex)

```bash
.venv/bin/python scripts/agent_orchestrator.py \
  --task-file prompts/major_feature.md \
  --run-gemini \
  --run-codex-review \
  --max-iterations 3 \
  --max-changed-files 15
```

#### 4. Continue from Codex Plan

```bash
.venv/bin/python scripts/agent_orchestrator.py \
  --continue-from-codex-todo reports/agent_pipeline/RUN_ID/NEXT_TODO.codex.md \
  --run-gemini \
  --run-codex-review \
  --max-iterations 2
```

### Stop Conditions

The orchestrator stops the loop automatically if:

- **Max Iterations**: `--max-iterations` limit reached.
- **Repeated Failure**: Same harness exit codes twice in a row.
- **Large Diff**: More than `--max-changed-files` (default 10) files touched.
- **Mixed Artifacts**: Generated files (`.joblib`, logs) in diff alongside code.
- **Safety Violation**: Sensitive files (`.env`, secrets, `.git/`) touched.
- **Timeout**: Codex review exceeds `--codex-timeout-seconds`.

### Scoped Review Mode

`--scoped-review` (default) instructs Codex to prioritize `review_packet.md` instead of a full repository-wide uncommitted diff.

## Optional AGY Review

After Codex review, invoke AGY for **strategy/risk/architecture** when diffs are material. For **test gaps**, assign a follow-up `[AGY]` slice instead of Gemini CLI. AGY does not replace Codex for `NEXT_TODO` drafting.

## Review Output

A good Codex review should include:

- high-risk findings first, with file/line references when possible;
- tests run and actual results;
- tests not run and why;
- whether the implementer's claims were verified;
- a short next-step plan with stop conditions and `[Cursor]` / `[AGY]` labels where helpful;
- residual risk.

## Guardrails

Codex must not:

- modify implementation changes during review unless asked to fix;
- revert user or implementer changes unless explicitly requested;
- place or enable live trades;
- edit secrets, credentials, `.env` files, deployment settings, or production configs;
- commit, push, deploy, or publish without explicit approval;
- add avoidable production dependencies without approval.

## Eval Maintenance

Add a record to `codex_harness/evals/gemini_review_requests.jsonl` when a new failure pattern or recurring review request appears. Each record should describe expected Codex review behavior, not runtime trading behavior.
