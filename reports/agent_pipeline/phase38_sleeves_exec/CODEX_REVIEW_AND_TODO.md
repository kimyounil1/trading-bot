The phase38 generated artifacts are mostly report updates, but the patch also corrupts historical phase30 review artifacts by removing their changed-file and diff contents. That provenance loss should be fixed before accepting the patch.

Review comment:

- [P2] Restore the phase30 review packet diff — /home/kimyo/trading-bot/reports/agent_pipeline/phase30/review_packet.md:9-15
  When this historical phase30 packet is used for audit or follow-up review, the `Changed Files` and `Git Diff Summary` sections are now empty, and the corresponding patch file was also emptied. Since this phase38 report update should not rewrite prior phase review evidence, this loses the exact implementation context reviewers need to verify what phase30 changed.
