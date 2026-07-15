The patch leaves an operationally important artifact in a self-contradictory state: the crowding gate report claims the proposal was applied, but the tracked strategy config still has the guard disabled. That inconsistency is actionable and can mislead later paper-trading runs.

Review comment:

- [P2] Correct the crowding gate report's claimed config application — /home/kimyo/trading-bot/logs/crowding_paper/go_no_go_checklist.json:24-30
  When someone relies on this committed `GO_PAPER` artifact to decide whether paper trading is now guarded, the report is misleading: it says the proposal was applied (`"applied": true` with `crowding_guard_enabled: true`), but `config/strategy_config.json` in this patch still has `crowding_guard_enabled` set to `false`. That means downstream runs will continue using the unguarded config even though the checklist claims the guard was enabled.
