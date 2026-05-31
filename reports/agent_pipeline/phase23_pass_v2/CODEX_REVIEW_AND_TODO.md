The balanced pass wrapper now invokes the AGY pytest slice before calling the orchestrator, while the orchestrator's --balanced-pass mode invokes it again. This breaks the wrapper's skip behavior and duplicates a pass step.

Review comment:

- [P2] Avoid running the AGY slice twice — /home/kimyo/trading-bot/scripts/run_balanced_pass.sh:36-36
  When `scripts/run_balanced_pass.sh` is used normally, it already runs `scripts/run_agy_slice.sh` above, then passes `--balanced-pass` to `agent_orchestrator.py`, whose new `args.balanced_pass` branch runs the same AGY slice again. This also makes `SKIP_AGY=1` ineffective for the wrapper because the orchestrator still runs the slice, so pass completion can be unnecessarily slow or fail after an explicitly skipped AGY step.
