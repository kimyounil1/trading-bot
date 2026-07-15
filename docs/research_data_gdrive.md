# Research data on Google Drive

Git tracks **decision summaries** only. Bulk research artifacts live in Drive.

**Drive folder:** `trading-bot-research/` (remote default: `gdrive:trading-bot-research`)

## What gets synced

See `config/research_gdrive_sync.json`:

| Path | Contents |
|------|----------|
| `data/` | raw prices, news_history, earnings, research, runtime state |
| `models/` | champion + challengers (`*.joblib`, metadata) |
| `reports/` | IC screens, enhancement suite (excludes `agent_pipeline/`) |
| `logs/ml/` | **full** experiment tree (except huge `model_calibration_rows.csv`) |
| `logs/benchmark_gap/`, `paper_validation/`, … | Operational research summaries |

**Security — secrets are NOT synced.** `.env` (Gemini/Alpaca/Toss live keys) is intentionally excluded from Drive: rclone stores files unencrypted and a folder mis-share would leak trading credentials. Back up credentials offline, or via an `rclone crypt` remote — never plaintext. `config/research_gdrive_sync.json` `private_files` is empty for this reason.

## How incremental sync works

`rclone copy` (what the script uses) on each run:

- **Skips** files already on Drive with the same size and modification time
- **Uploads** new files and files you changed locally
- **Does not delete** remote files removed locally (archive-safe)

Re-running is cheap: a 1,700-line `llm_retro_scores.jsonl` re-uploads only when the file changes (e.g. after more retro scoring).

Rate limits: script sets `--tpslimit 8` to reduce Drive 403 bursts.

## Schedule (recommended)

```bash
bash scripts/install_research_gdrive_sync_timer.sh
systemctl --user enable --now trading-bot-research-gdrive-sync.timer
```

Default: **every 4 hours** (`config/research_gdrive_sync_config.json`). Edit `on_calendar` to change.

Optional: sync after each LLM retro milestone (500, 1000, …):

```bash
RESEARCH_GDRIVE_SYNC_ON_CHECKPOINT=1 bash scripts/watch_llm_retro_batch.sh
```

Log: `logs/ml/gdrive_sync.log`

## One-time setup (rclone)

```bash
sudo apt install rclone   # or: https://rclone.org/install/

rclone config
# n) New remote
# name: gdrive
# Storage: drive (Google Drive)
# scope: 1 (full access) or 2 (read-only for download-only)
# auto config in browser, or paste token on headless WSL
```

Create the folder on first sync (rclone creates it automatically):

```bash
bash scripts/sync_research_to_gdrive.sh --dry-run
bash scripts/sync_research_to_gdrive.sh
```

Custom folder name:

```bash
RESEARCH_GDRIVE_REMOTE="gdrive:MySharedDrive/trading-bot-research" \
  bash scripts/sync_research_to_gdrive.sh
```

## Restore on another machine

```bash
rclone copy gdrive:trading-bot-research/data data
rclone copy gdrive:trading-bot-research/models models
rclone copy gdrive:trading-bot-research/reports reports
# .env is NOT on Drive — restore credentials from your offline/encrypted backup.
```

## Manifest

Each sync writes `_sync_manifest.json` on Drive with timestamp, git commit, and `llm_retro_scores` line count.
