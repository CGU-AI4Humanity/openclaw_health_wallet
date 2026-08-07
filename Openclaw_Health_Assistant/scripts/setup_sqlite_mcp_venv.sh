#!/usr/bin/env bash
# SQLite MCP venv — Brandon Medina (OpenClaw Health Assistant)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="${ROOT}/sqlite-mcp/.venv"

python3 -m venv "${VENV}"
"${VENV}/bin/pip" install -q -r "${ROOT}/sqlite-mcp/requirements.txt"
echo "SQLite MCP venv ready: ${VENV}/bin/python"
