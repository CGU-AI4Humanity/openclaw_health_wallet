#!/usr/bin/env bash
# Full local stack: MedGemma → SQLite → MCP → FHIR → smoke test
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
"${ROOT}/scripts/setup_sqlite_mcp_venv.sh"

# shellcheck disable=SC1090
source "${ENV_FILE}"
DB="${OPENCLAW_HEALTH_DB_PATH:-${MYWELLWALLET_DB_PATH:-${HOME}/.openclaw-health-assistant/openclaw_health.db}}"

if [[ ! -f "${DB}" ]]; then
  "${ROOT}/scripts/init_db.sh"
elif [[ "${COPY_FIXTURE:-}" != "" ]]; then
  "${ROOT}/scripts/copy_fixture_db.sh" "${COPY_FIXTURE}"
fi

"${ROOT}/scripts/configure_medgemma.sh"
"${ROOT}/scripts/wire_mcp_servers.sh"
"${ROOT}/scripts/test_local_stack.sh"

echo ""
echo "Stack ready. Chat: openclaw tui  (or Control UI)"
echo "Apple Health: complete Setup Wizard QR pairing (Health Link iOS) or MCP import_apple_health_json for file-based import."
