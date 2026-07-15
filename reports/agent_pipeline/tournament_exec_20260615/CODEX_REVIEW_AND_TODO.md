The tournament buy path can violate its own max position limit when multiple buys are submitted in one run near the cap. Other changes appear generally consistent with the stated task.

Review comment:

- [P2] Count pending tournament buys against the position cap — /home/kimyo/trading-bot/src/trading/tournament_buy_pipeline.py:134-135
  When the sleeve is one slot below `max_total_positions` and more than one tournament candidate is buyable in the same run, this check keeps seeing only the pre-run positions because `ctx.positions_by_symbol` is not updated after submissions. With the default `max_orders_per_run` allowing multiple orders, the loop can submit several new tournament buys and exceed the newly raised tournament cap; track accepted/submitted tournament orders in this run or include them in the count before allowing the next candidate.
