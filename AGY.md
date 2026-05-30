# AGY.md

Rules for **AGY** (Antigravity / stronger Gemini-tier assistant). AGY is **not** the primary production implementer, but it **is** the preferred agent for **test and harness work** in this repo.

**Model note:** AGY sessions typically use a stronger model (e.g. Gemini Pro tier) than **Gemini CLI** headless defaults (often Flash-class). Prefer AGY over Gemini CLI for anything that must be correct on first try (tests, risk regressions, calibration reports).

## Role

| Agent | Role | Typical share (target) |
|-------|------|-------------------------|
| **Cursor** | Primary implementation: `main.py`, orders, integration, config wiring | ~60–70% |
| **Codex** | Read-only review, test verification, `NEXT_TODO` per pass | ~15–20% |
| **AGY** | **Tests & harness** (`[AGY]` slices); optional architecture/strategy/risk review | ~15–25% |
| **Gemini CLI** | Legacy, low-risk only (`--run-gemini`); avoid for tests | ~0–5% |

## When to Involve AGY (review)

Request AGY **review** when changes touch:
- trading strategy semantics (buy/sell gates, regime logic, profile switching);
- portfolio or execution risk (leverage, concentration, circuit breakers, correlation);
- model governance (promotion, rollback, calibration, drift);
- large refactors that span multiple core modules;
- alternative designs worth comparing before merge.

## When to Assign AGY (implement — `[AGY]`)

Route **implementation** to AGY (explicit invoke; separate branch or sequential pass; still only one implementer at a time) for:
- new or extended **pytest** for behavior Cursor just added (mock broker, mock LLM, fault injection);
- **regression tests** for partial exit / trim / trailing / earnings / macro skip combinations;
- **harness scripts** under `tests/harness/` and calibration/backtest **report generators** that do not touch live order paths;
- portfolio/walk-forward **validation scripts** and golden-file checks on `logs/` outputs;
- property-style tests on pure functions (`risk_manager`, `correlation_guard`, schema validators).

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

### AGY test implementation handoff

1. Cursor lands feature code + minimal smoke test if needed.
2. User invokes AGY with `[AGY]` task file (scope: tests only, files list, interfaces to mock).
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
