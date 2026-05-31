The documented required workflow references a new script that is not included in the tracked patch, so the main workflow introduced by the change would fail after merge.

Review comment:

- [P1] Add the pass-complete script before documenting it — /home/kimyo/trading-bot/CURSOR.md:77-77
  This workflow now makes `scripts/run_pass_complete.sh` the required pass-closure command, but the script is not part of the tracked diff/review packet (`git status` shows it as untracked). If this patch is committed as-is, users following the README/CURSOR instructions will hit `bash: scripts/run_pass_complete.sh: No such file or directory`, so the new required workflow is broken unless the script is added to the patch or the docs keep pointing at the existing tracked workflow.
