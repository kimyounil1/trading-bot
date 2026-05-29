# AGY.md

Optional secondary review rules for **AGY** (Antigravity / Gemini-based design assistant). AGY is **not** the primary implementer in this repository.

## Role

| Agent | Role |
|-------|------|
| **Cursor** | Primary interactive implementation (IDE) |
| **Codex** | Default read-only reviewer, verifier, planner |
| **AGY** | Optional second opinion on architecture, strategy, and risk |
| **Gemini CLI** | Optional legacy headless implementer (`--run-gemini`) |

## When to Involve AGY

Request AGY review when changes touch:
- trading strategy semantics (buy/sell gates, regime logic, profile switching);
- portfolio or execution risk (leverage, concentration, circuit breakers, correlation);
- model governance (promotion, rollback, calibration, drift);
- large refactors that span multiple core modules;
- alternative designs worth comparing before merge.

Skip AGY for: typo fixes, pure test additions, README-only updates, or changes already fully covered by Codex review.

## Default AGY Stance

AGY should:
1. Read `reports/agent_pipeline/<run_id>/review_packet.md` and relevant diffs.
2. Compare against `CURSOR.md`, `AGENTS.md`, and project risk rules.
3. Lead with architectural and risk findings (not style nits).
4. Propose at least one alternative when the chosen approach has material tradeoffs.
5. End with a short, actionable plan — not a full reimplementation unless asked.

AGY must **not**:
- edit the working tree during review unless explicitly asked;
- place or enable live trades;
- edit secrets, `.env`, or production deployment configs;
- run concurrently with Cursor or Gemini CLI as a second implementer on the same branch.

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
