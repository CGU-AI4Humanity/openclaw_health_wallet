#!/usr/bin/env bash
# Full local stack: MedGemma → SQLite → MCP → FHIR → Apple Health smoke
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${ROOT}/config/.env"

export NVM_DIR="${NVM_DIR:-${HOME}/.nvm}"
# shellcheck disable=SC1091
[[ -s "${NVM_DIR}/nvm.sh" ]] && source "${NVM_DIR}/nvm.sh"
nvm use 24 >/dev/null 2>&1 || true

if [[ ! -f "${ENV_FILE}" ]]; then
  cp "${ROOT}/config/.env.example" "${ENV_FILE}"
  if [[ -f "${HOME}/myWellWallet/lib/config/app_config.dart" ]]; then
    KEY="$(grep "mcpApiKey" "${HOME}/myWellWallet/lib/config/app_config.dart" | sed -n "s/.*'\([^']*\)'.*/\1/p" | head -1)"
    if [[ -n "${KEY}" ]]; then
      echo "FHIR_MCP_API_KEY=${KEY}" >> "${ENV_FILE}"
    fi
  fi
fi

chmod +x "${ROOT}/scripts/"*.sh
"${ROOT}/scripts/setup_sqlite_mcp_venv.sh"

DB="${MYWELLWALLET_DB_PATH:-${HOME}/.openclaw-health-assistant/mywellwallet.db}"
if [[ ! -f "${DB}" ]] || [[ "$(sqlite3 "${DB}" "SELECT COUNT(*) FROM fhir_patients;" 2>/dev/null || echo 0)" == "0" ]]; then
  if [[ -f "${HOME}/myWellWallet/fixtures/test_database_export/mywellwallet_phone.sqlite3" ]]; then
    "${ROOT}/scripts/copy_fixture_db.sh"
  else
    "${ROOT}/scripts/init_db.sh"
  fi
fi

"${ROOT}/scripts/configure_medgemma.sh"
"${ROOT}/scripts/wire_mcp_servers.sh"
"${ROOT}/scripts/test_local_stack.sh"

echo ""
echo "Stack ready. Chat: openclaw tui  (or Control UI)"
echo "Apple Health MCP: sync_apple_health_from_phone_database | import_apple_health_json"
