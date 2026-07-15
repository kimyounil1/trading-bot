The patch introduces a runtime failure in the main trading path by dropping required rank AI imports, and the new sleeve budget cap can be exceeded within a single run with multiple buy candidates. These affect core execution behavior and should be fixed before considering the patch correct.

Full review comments:

- [P1] Restore the rank AI gate imports — /home/kimyo/trading-bot/src/main.py:65-72
  With this import replacement, `build_rank_ai_gate_scores` and `apply_rank_ai_buy_gate` are no longer defined even though `main()` still calls them unconditionally. In the normal startup path this raises `NameError` at the rank-score build step, and because `rank_ai_buy_gate_fail_closed` defaults to fail-closed the bot aborts before processing candidates.

- [P1] Track sleeve budget consumed by earlier buys — /home/kimyo/trading-bot/src/main.py:1375-1380
  When sleeves are enabled and several BUY candidates pass in one run, each candidate recomputes `order_budget_for()` from the original account/open-order snapshot, so submitted orders earlier in the loop do not reduce the budget for later candidates. This lets multiple orders each consume up to the full core sleeve budget before the broker's open orders are visible in a later run, violating the new sleeve cap under multi-buy runs.
