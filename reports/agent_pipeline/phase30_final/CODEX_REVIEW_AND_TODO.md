The new config-apply path can persist invalid crowding settings because it uses only the shallow payload validator before writing `strategy_config.json`. That makes the patch unsafe even though the included tests pass.

Review comment:

- [P2] Validate merged crowding settings before writing strategy_config — /home/kimyo/trading-bot/src/crowding_paper_gate.py:177-180
  If `crowding_paper_proposal.json` contains an out-of-range crowding value (for example `crowding_max_positions: 0` or a negative threshold), this path still writes the merged JSON because `_validate_strategy_settings_payload()` only checks key names and a couple of types. The next `load_settings()` call will then fail on the stricter checks in `validate_settings()`, so a successful `--apply-config` run can leave `config/strategy_config.json` in a state that breaks later bot starts.
