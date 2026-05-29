#!/usr/bin/env bash
set -euo pipefail

# Cursor-first entry point. Delegates to the shared post-workflow collector.
export IMPLEMENTATION_AGENT="${IMPLEMENTATION_AGENT:-cursor}"
exec bash scripts/run_gemini_post_workflow.sh
