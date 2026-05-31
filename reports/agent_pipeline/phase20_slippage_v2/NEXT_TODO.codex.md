The patch references new helper and operational script files that are not included in the submitted diff, causing clean-checkout failures in the retrain path and documented weekly slippage workflow.

Full review comments:

- [P1] Include the new holdout helper module — /home/kimyo/trading-bot/src/train_ai_model.py:29-33
  This import depends on `src/retrain_holdout.py`, but that file is not part of the submitted patch/review packet. In a clean checkout of this change, importing or running `src.train_ai_model` will fail with `ModuleNotFoundError`, so the retrain promotion path is currently broken unless the helper module is added to the patch.

- [P2] Include the referenced slippage scripts — /home/kimyo/trading-bot/docs/runbook.md:60-63
  The runbook now tells operators to run `scripts/run_weekly_slippage_report.sh` and install `scripts/install_slippage_report_timer.sh`, but those scripts are not included in the patch/review packet. On a clean checkout, these documented commands will fail with “No such file or directory”; add the scripts to the change or avoid documenting them here.
