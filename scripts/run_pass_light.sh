#!/usr/bin/env bash
# Light pass: pytest + review packet only (no Codex). Saves review credits.
#
# Usage:
#   RUN_ID=phase26_fix SKIP_CODEX=1 bash scripts/run_pass_complete.sh
#   RUN_ID=phase26_fix bash scripts/run_pass_light.sh
set -euo pipefail
export SKIP_CODEX=1
exec bash "$(dirname "$0")/run_pass_complete.sh" "$@"
