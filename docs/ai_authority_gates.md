# AI authority tiers (paper → production)

This document defines **what the bot may let AI control** at each stage.  
Rank AI and champion `ai_score` models are evaluated separately.

## Tier 0 — Champion filter / sizing overlay (current production default)

**Scope:** `use_ai_score` + `ai_score_buy_threshold`, conviction sizing, optional AI exit.

| Requirement | Gate |
|-------------|------|
| Promotion ML | avg ROC-AUC ≥ 0.51, Brier ≤ 0.25, fold ROC-AUC std < 0.05 |
| Promotion portfolio OOS | return gap vs equal-weight benchmark ≥ 0 pp, max DD ≥ −20%, Sharpe ≥ 1.0 |
| Operator summary | `logs/model_quality/latest_summary.json` → `keep_ai_as_filter_and_sizing_overlay` |

**Not allowed:** AI as sole buy/sell authority; rank model replacing champion without review.

See also: [`promotion_gates.md`](promotion_gates.md)

## Tier 1 — Cross-sectional rank buy/add gate (paper experiment, current)

**Scope:** New buys and add-ons only. **Sells unchanged** (stop / take profit / trailing / AI exit / strategy SELL).

| Setting | Default (paper config) |
|---------|-------------------------|
| `rank_ai_buy_gate_enabled` | `true` |
| Model | `logs/ml/rank_label_experiment_h20_top15_q85/rank_models.joblib` |
| Horizon / bucket | 20d, top 15% label, score quantile ≥ 0.85 |
| `rank_ai_buy_gate_fail_closed` | `true` (missing model/score → block buy) |

**Research OOS gate (passed for this candidate):**

| Metric | Result |
|--------|--------|
| OOS return | +24.14% |
| Equal-weight benchmark | +9.73% |
| Gap | +14.41 pp |
| Sharpe | 1.765 |
| Max drawdown | −11.2% |
| Turnover proxy | 1.00 |

**Paper validation before any live default:**

1. Accumulate `execution_audit` skips with `rank ai gate blocked` vs `BUY_SUBMITTED` with `rank ai gate passed`.
2. Compare `logs/candidate_cache/latest_buy.csv` pass/block counts over multiple runs.
3. Report: `bash scripts/run_rank_ai_gate_report.sh` → `logs/rank_ai_gate/latest_summary.json`
4. Require **≥ 2 weeks** of paper/dry-run with gate enabled and no regression vs baseline paper ops (returns, skip rate, API errors).

**Do not:** Promote rank model to `models/ai_score_model.joblib` without a separate retrain/promotion path.

## Tier 2 — Full AI buy authority (future, blocked)

All new buys/adds require rank (or promoted champion) approval; strategy signals become secondary.

| Requirement | Gate |
|-------------|------|
| Tier 1 paper | ≥ 2 weeks stable, documented in rank impact report |
| ML | avg ROC-AUC ≥ **0.55**, Brier ≤ **0.25**, fold std < **0.05** |
| Portfolio OOS | benchmark gap ≥ **0 pp**, Sharpe ≥ **1.0**, max DD ≥ **−20%** |
| Turnover | turnover proxy ≤ configured cap (default 1.2) |

## Tier 3 — Full AI buy + sell authority (future, blocked)

AI may trigger exits in addition to buys. Highest risk; requires Tier 2 plus sell-side OOS and drawdown review.

| Requirement | Gate |
|-------------|------|
| Tier 2 | Completed in paper |
| Sell OOS | Rank or champion exit model beats baseline exit policy on gap / DD / turnover |
| Governance | Explicit operator sign-off; never enable via config alone |

## Tier 4 — Tournament alpha model (sleeve-scoped, paper-only)

**Scope:** `tournament` sleeve via `tournament_alpha_model` adapter. Separate from champion promotion.

| Setting | Default |
|---------|---------|
| Sleeve | `tournament` (30% target weight when sleeves enabled) |
| Profile | `config/profiles/tournament_paper.json` |
| Model id | `tournament_alpha_model` |
| Live | **OFF** (`paper_only=true`) |

**Paper validation before live (future, blocked by default):**

1. ≥ **30 calendar days** paper with tournament sleeve enabled.
2. 21-day rolling return beats best of SPY / QQQ / MTUM / equal-weight universe.
3. Max drawdown within sleeve limit; turnover and slippage-adjusted edge documented.
4. Codex scoped review pass (`RUN_ID=phase36_sleeves` or successor).

**Do not:** Enable tournament sleeve on live profile; conflate with champion swap or Rank gate live expansion.

## Commands

```bash
# Rank gate paper impact
bash scripts/run_rank_ai_gate_report.sh
REFRESH_CANDIDATE_CACHE=1 bash scripts/run_rank_ai_gate_report.sh

# Model quality + rank experiment summary
bash scripts/run_model_quality_report.sh

# Full paper ops (includes rank report step)
bash scripts/run_paper_ops_bootstrap.sh
```

## Decision log

| Date | Decision |
|------|----------|
| 2026-06-02 | Rank label 20d/top15% passes OOS portfolio gate; wired as **paper-only** buy/add overlay. Champion unchanged. |
