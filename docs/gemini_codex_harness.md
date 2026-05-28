# Gemini CLI Review Harness

This harness defines how Codex should review, validate, and plan follow-up work
after Gemini CLI has made changes in this repository. It is not the trading
runtime harness and it is not a "Codex implements everything" workflow.

## Roles

- `GEMINI.md`: working rules for Gemini CLI, the primary implementation agent.
- `AGENTS.md`: working rules for Codex in this repository.
- `codex_harness/agent_contract.json`: machine-readable review contract for the
  Gemini-to-Codex workflow.
- `codex_harness/evals/gemini_review_requests.jsonl`: representative review and
  planning requests with expected Codex behavior.
- `tests/harness/test_codex_agent_harness.py`: structural checks that keep the
  review contract, evals, and instructions aligned.

## Default Codex Stance

When the user asks Codex to check Gemini's work, Codex should review first and
avoid editing files unless explicitly asked to fix the issues.

Codex should:

1. Inspect `git status --short`.
2. Inspect targeted diffs for the files Gemini changed.
3. Compare the changes against `AGENTS.md`, `GEMINI.md`, and project rules.
4. Choose focused verification commands.
5. Run safe checks or explain what should be run.
6. Report findings first, then a concrete next-step plan.

## Run

```bash
bash scripts/run_gemini_review_harness.sh
```

Use this after changing `AGENTS.md`, `GEMINI.md`, review policy, guardrails,
handoff rules, or the Gemini review eval catalog.

For a local pre-final check:

```bash
bash scripts/codex_pre_final_check.sh
```

## Gemini -> Codex -> Gemini Pipeline

After Gemini CLI finishes implementation work, run:

```bash
bash scripts/run_gemini_post_workflow.sh
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
- `gemini_review_harness.log`
- `runtime_harness.log`
- `review_packet.md`
- `NEXT_TODO.md`
- `summary.json`

The intended loop is:

1. Gemini CLI implements the change.
2. `scripts/run_gemini_post_workflow.sh` runs review/runtime checks and creates a packet.
3. The user asks Codex to review `review_packet.md`.
4. Codex leads with findings and rewrites `NEXT_TODO.md` into a concrete Gemini-ready task list.
5. Gemini CLI works from `NEXT_TODO.md`.
6. Repeat the post-workflow script after Gemini finishes the next pass.

This repository does not automatically call Codex or Gemini by itself. Full
agent-to-agent automation requires an external CLI/API orchestrator. The local
pipeline provides deterministic artifacts that such an orchestrator can consume.

## External Orchestrator

This repository includes a local CLI orchestrator:

```bash
.venv/bin/python scripts/agent_orchestrator.py --task "..." --run-gemini --run-codex-review
```

The orchestrator performs:

1. Optional Gemini CLI implementation pass with `gemini --prompt`.
2. `scripts/run_gemini_post_workflow.sh` to collect diffs, logs, review packet,
   and a draft `NEXT_TODO.md`.
3. Optional Codex review pass with `codex exec` in `read-only` sandbox mode.
4. A generated `CODEX_REVIEW_AND_TODO.md` and, when Codex succeeds,
   `NEXT_TODO.codex.md`.

Safe defaults:

- Gemini does not run unless `--run-gemini` is provided.
- Codex does not run unless `--run-codex-review` is provided.
- Codex runs with `--sandbox read-only --ask-for-approval never`.
- Gemini `yolo` mode is refused by the orchestrator.
- Reports are written under `reports/agent_pipeline/<run_id>/`, which is ignored
  by Git.

Dry-run example:

```bash
.venv/bin/python scripts/agent_orchestrator.py \
  --task "Review current Gemini changes and plan next steps" \
  --dry-run
```

### Workflow Examples

#### 1. One-Shot Implementation & Review
Run Gemini once, generate a packet, and have Codex review it once.

```bash
.venv/bin/python scripts/agent_orchestrator.py \
  --task-file prompts/my_task.md \
  --run-gemini \
  --run-codex-review
```

#### 2. Review-Only Mode
Review existing (uncommitted) changes without launching Gemini.

```bash
.venv/bin/python scripts/agent_orchestrator.py \
  --run-codex-review \
  --scoped-review
```

#### 3. Bounded Automatic Loop (Gemini <-> Codex)
Run up to 3 iterations. Codex produces the next TODO for Gemini each time.

```bash
.venv/bin/python scripts/agent_orchestrator.py \
  --task-file prompts/major_feature.md \
  --run-gemini \
  --run-codex-review \
  --max-iterations 3 \
  --max-changed-files 15
```

#### 4. Continue from Codex Plan
If a previous loop stopped, you can resume using Codex's last suggested TODO.

```bash
.venv/bin/python scripts/agent_orchestrator.py \
  --continue-from-codex-todo reports/agent_pipeline/RUN_ID/NEXT_TODO.codex.md \
  --run-gemini \
  --run-codex-review \
  --max-iterations 2
```

### Stop Conditions

The orchestrator stops the loop automatically if:
- **Max Iterations**: The `--max-iterations` limit is reached.
- **Repeated Failure**: The same test/harness fails with the same exit codes twice in a row.
- **Large Diff**: More than `--max-changed-files` (default 10) are touched.
- **Mixed Artifacts**: Generated files (e.g., `.joblib`, logs) are detected in the diff alongside code.
- **Safety Violation**: Sensitive files (`.env`, secrets, `.git/`) are touched.
- **Timeout**: Codex review exceeds `--codex-timeout-seconds`.

### Scoped Review Mode

The `--scoped-review` flag (enabled by default) instructs Codex to prioritize the `review_packet.md` and specific diffs rather than a full repository-wide uncommitted diff. This reduces context noise and avoids reviewing large generated artifacts.

## Review Output

A good Codex review of Gemini work should include:

- high-risk findings first, with file/line references when possible;
- tests run and actual results;
- tests not run and why;
- whether Gemini's claims were verified;
- a short next-step plan with stop conditions;
- residual risk.

## Guardrails

Codex must not:

- modify Gemini's changes during review unless asked to fix;
- revert Gemini or user changes unless explicitly requested;
- place or enable live trades;
- edit secrets, credentials, `.env` files, deployment settings, or production configs;
- commit, push, deploy, or publish without explicit approval;
- add avoidable production dependencies without approval.

## Eval Maintenance

Add a record to `codex_harness/evals/gemini_review_requests.jsonl` when a new
Gemini failure pattern or recurring review request appears. Each record should
describe expected Codex review behavior, not runtime trading behavior.
