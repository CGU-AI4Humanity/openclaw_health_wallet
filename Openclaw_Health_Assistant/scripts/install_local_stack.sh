#!/usr/bin/env bash
# Demo stack: seed DB → health MCP venv → Qwen 2.5 → wire health MCP
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${ROOT}/config/.env"

export NVM_DIR="${NVM_DIR:-${HOME}/.nvm}"
# shellcheck disable=SC1091
[[ -s "${NVM_DIR}/nvm.sh" ]] && source "${NVM_DIR}/nvm.sh"
nvm use 24 >/dev/null 2>&1 || true

if [[ ! -f "${ENV_FILE}" ]]; then
  cp "${ROOT}/config/.env.example" "${ENV_FILE}"
fi

chmod +x "${ROOT}/scripts/"*.sh
"${ROOT}/scripts/setup_health_mcp_venv.sh"
"${ROOT}/scripts/seed_demo_database.sh"
# shellcheck disable=SC1090
source "${ENV_FILE}"

"${ROOT}/scripts/configure_health_assistant.sh"
"${ROOT}/scripts/cleanup_mcp_servers.sh"
"${ROOT}/scripts/test_local_stack.sh"

echo ""
echo "Ready. Try: nvm use 24 && openclaw chat"
echo "Stuck on qwen3:4b in chat? ./scripts/reset_health_demo_setup.sh"
