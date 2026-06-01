#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

CMS_PORT="${CMS_PORT:-8502}"

exec "$PROJECT_DIR/.venv/bin/python" -m streamlit run app/streamlit_app.py \
  --server.address 0.0.0.0 \
  --server.port "${CMS_PORT}" \
  --server.headless true
