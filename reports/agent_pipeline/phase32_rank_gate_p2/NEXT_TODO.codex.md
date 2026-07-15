The patch introduces dust-position handling, but the live and cached buy flows still treat those symbols/counts as active in some guards. That can incorrectly suppress buys even after the code decides dust should be ignored or closed.

Full review comments:

- [P2] Remove dust symbols from the active-position sets before buy guards — /home/kimyo/trading-bot/src/main.py:682-685
  When a position is classified as dust, this branch removes it from `positions_by_symbol` and decrements `meaningful_positions_count`, but it leaves the symbol in `open_symbols`. The later buy pass still feeds `open_symbols` into sector/correlation/crowding/instrument guards, so a negligible position that is being closed in the same run can still block a replacement buy until the next run. This shows up whenever an account holds a <$5 stub in a constrained sector or leveraged ETF slot.

- [P2] Exclude dust positions from candidate-cache position counts — /home/kimyo/trading-bot/src/candidate_cache.py:501-506
  `effective_position()` correctly treats dust holdings as flat for the current ticker, but the new-position branch still passes the raw `positions_count` from Alpaca into `check_buy_allowed()`. If the account is only “full” because of one or more dust leftovers, the cache will mark otherwise valid buys as blocked by `max_total_positions`, which makes the cache disagree with the live path that now uses `meaningful_positions_count` for the same check.
