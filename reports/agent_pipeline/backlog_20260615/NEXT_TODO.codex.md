The patch adds the requested report and retry behavior, but the tournament buy path can now exceed its own max position limit within one run because submitted tournament orders are not counted against the cap.

Review comment:

- [P2] Count submitted tournament buys toward the position cap — /home/kimyo/trading-bot/src/trading/tournament_buy_pipeline.py:134-139
  When the tournament sleeve already has fewer than `max_total_positions`, this check can still allow more than the remaining slots in a single run because `_tournament_open_position_count(ctx)` only reads the starting `positions_by_symbol` and is not incremented after each submitted/filled tournament buy. For example, with 11 existing tournament positions and `max_total_positions=12`, two or more BUY candidates can be submitted before the next broker position snapshot, exceeding the sleeve cap.
