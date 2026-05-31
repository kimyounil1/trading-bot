The changed code imports a new module that is currently untracked and absent from the review packet, so the patch would break imports in core retraining and validation paths when applied.

Review comment:

- [P1] Include the new ML quality module in the patch — /home/kimyo/trading-bot/src/train_ai_model.py:29-34
  This import depends on `src.ml_quality_report`, but that file is not part of the tracked diff/review packet, so applying this patch as-is leaves `train_ai_model.py`, `walk_forward_validation.py`, and `build_promotion_report()` failing with `ModuleNotFoundError` as soon as they are imported or run. Please add the new module and its tests/artifacts to the committed changes, or avoid introducing the import.
