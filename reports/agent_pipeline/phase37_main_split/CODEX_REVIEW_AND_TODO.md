The patch changes an execution gate from enabled to disabled, which materially alters paper execution behavior and appears unrelated to the requested main.py pipeline split.

Review comment:

- [P1] Restore CMS paper execution lock state — /home/kimyo/trading-bot/config/execution_lock.json:2-2
  With this repository config committed, `is_cms_execution_enabled()` will now return `false` and the CMS paper execution path stays locked even when the previous checked-in state allowed paper execution. This change is unrelated to splitting `main.py` and will block normal paper execution workflows that rely on the committed lock being enabled.
