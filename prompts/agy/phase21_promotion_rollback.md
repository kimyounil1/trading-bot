# [AGY] Phase 21 — Promotion reject & rollback path mocks

## Scope
- `tests/test_promotion_rollback_path.py`
- `resolve_rollback_decision()` in `src/train_ai_model.py`

## Scenarios
- Challenger rejected: weak AUC, portfolio gate fail, high fold variance
- Rollback: skip after PROMOTE, NO_ROLLBACK_NEEDED, ROLLBACK_TO_ARCHIVED_CHAMPION, NO_ROLLBACK_AVAILABLE

## Run
```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/test_model_governance_rollback.py tests/test_promotion_rollback_path.py -q
```
