#!/usr/bin/env bash
# stop5_trail10 paper trial tracker. --start records trial start state.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH=.
.venv/bin/python -m src.stop_trail_trial_report "$@"
