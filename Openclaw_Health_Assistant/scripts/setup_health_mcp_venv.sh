#!/usr/bin/env bash
# Brandon Medina — typed health MCP venv (mcp 1.x)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="${ROOT}/health-mcp/.venv"

python3 -m venv "${VENV}"
"${VENV}/bin/pip" install -q -U pip
"${VENV}/bin/pip" install -q -r "${ROOT}/health-mcp/requirements.txt"
echo "Health MCP venv ready: ${VENV}/bin/python"
