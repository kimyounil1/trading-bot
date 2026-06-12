# AGY.md

Rules for **AGY** (Antigravity / stronger Gemini-tier assistant). AGY is **not** the primary production implementer, but it **is** the preferred agent for **test and harness work** in this repo.

**Model note:** AGY sessions typically use a stronger model (e.g. Gemini Pro tier) than **Gemini CLI** headless defaults (often Flash-class). Prefer AGY over Gemini CLI for anything that must be correct on first try (tests, risk regressions, calibration reports).

## Role

| Agent | Role | Typical share (target) |
|-------|------|-------------------------|
| **Cursor** | Primary implementation: `main.py`, orders, integration, config wiring | ~60–70% |
| **Codex** | Read-only review, test verification, `NEXT_TODO` per pass | ~15–20% |
| **AGY** | **`[Research]`** offline experiments · **`[AGY-test]`** pytest · **`[AGY-risk]`** read-only review | ~20–30% (별도 AGY 계정·쿼터) |
| **Gemini CLI** | Legacy, low-risk only (`--run-gemini`); avoid for tests | ~0–5% |

## Invocation modes

| Label | AGY edits? | Use for |
|-------|------------|---------|
| **`[Research]`** | Yes (offline only) | Calibration sweeps, fold stability, parameter grids, `*_report.py` / experiment CLIs, `logs/ml/` artifacts. No `main.py`, orders, or champion swap. |
| **`[AGY-test]`** | Yes (tests only) | pytest, fixtures, `tests/harness/` after Cursor or `[Research]` lands code. Alias: **`[AGY]`**. |
| **`[AGY-risk]`** | **No** (read-only) | Strategy semantics, promotion/gates, portfolio risk on **material** diffs. Output: architecture/risk memo — not `NEXT_TODO` (Codex owns that). |

Still **one implementer at a time** on the branch: do not run `[Research]` and `[Cursor]` concurrently.

### Research handoff

1. User invokes AGY with `[Research]` task file (`prompts/agy/` or `reports/agent_pipeline/<run_id>/TASK.md`).
2. AGY runs experiments, writes reports under `logs/ml/`, adds pytest; commits `[agy]` / `[research]`.
3. **`[Cursor]`** wires runtime flags or config adopt paths if the slice requires it.
4. **`[AGY-test]`** on integration paths Cursor touched.
5. **`run_pass_complete.sh`** → Codex → Cursor reads `NEXT_TODO.codex.md`.

## When to Involve AGY (`[AGY-risk]` review)

Request **`[AGY-risk]`** when changes touch:
- trading strategy semantics (buy/sell gates, regime logic, profile switching);
- portfolio or execution risk (leverage, concentration, circuit breakers, correlation);
- model governance (promotion, rollback, calibration, drift);
- large refactors that span multiple core modules;
- alternative designs worth comparing before merge.

## When to Assign AGY (`[AGY-test]`)

Route **`[AGY-test]`** to AGY (explicit invoke; sequential pass) for:
- new or extended **pytest** for behavior Cursor just added (mock broker, mock LLM, fault injection);
- **regression tests** for partial exit / trim / trailing / earnings / macro skip combinations;
- property-style tests on pure functions (`risk_manager`, `correlation_guard`, schema validators).

## When to Assign AGY (`[Research]`)

Route **`[Research]`** to AGY for offline work (see `TODO.md` §4–§5):
- calibration / fold-stability / label experiments and report CLIs;
- parameter sweeps via `portfolio_backtester` / `research_promotion_gates.py`;
- harness scripts under `tests/harness/` tied to research outputs;
- golden-file checks on `logs/ml/` schemas.

**Cursor keeps:** runtime wiring, `main.py`, orders, champion promotion decisions, paper config adopt after gates pass.

**Cursor keeps:** `main.py` integration, Alpaca order paths, profile/regime wiring, and merging AGY test PRs after green pytest.

**Do not assign AGY:** live order submission changes, secrets, `.env`, or same-branch concurrent edits with Cursor.

Skip AGY entirely for: typo-only README, comment-only diffs already approved by Codex with no behavioral gap.

## Default AGY Stance

AGY should:
1. Read `reports/agent_pipeline/<run_id>/review_packet.md` and relevant diffs.
2. Compare against `CURSOR.md`, `AGENTS.md`, and project risk rules.
3. Lead with architectural and risk findings (not style nits).
4. Propose at least one alternative when the chosen approach has material tradeoffs.
5. End with a short, actionable plan — not a full reimplementation unless asked.

AGY must **not**:
- edit the working tree during **review** unless explicitly asked;
- place or enable live trades;
- edit secrets, `.env`, or production deployment configs;
- run concurrently with Cursor or Gemini CLI as a second implementer on the same branch;
- replace Codex for `NEXT_TODO` drafting (Codex stays the per-pass queue owner).

### AGY test implementation handoff (`[AGY-test]`)

1. Cursor (or `[Research]`) lands feature code + minimal smoke test if needed.
2. User invokes AGY with `[AGY-test]` task file (scope: tests only, files list, interfaces to mock).
3. AGY adds tests; runs `PYTHONPATH=. .venv/bin/python -m pytest <paths>`.
4. Cursor merges or rebases; runs full suite.
5. **패스 마감:** `RUN_ID=<pass> bash scripts/run_pass_complete.sh` → Codex 리뷰 → `NEXT_TODO.codex.md` 확인 (AGY 테스트만 끝내고 리뷰 생략 금지).

## Handoff Format

AGY reviews should include:
- **Architecture**: coupling, boundaries, missing abstractions;
- **Strategy / risk**: failure modes, silent fallbacks, order-path hazards;
- **Alternatives**: simpler or safer options with tradeoffs;
- **Residual risk**: what remains unverified after Codex review.

## Runtime vs CLI

- **Runtime LLM** (`src/llm_analyst.py`): use a fast/cheap model (e.g. Gemini Flash) for per-ticker news consensus.
- **AGY / design review**: may use a stronger model (e.g. Gemini 3.1 Pro) when the user invokes AGY explicitly.
- Do not conflate runtime API model choice with AGY review sessions.
