#!/usr/bin/env bash
# OpenClaw MCP wiring — Leonard Bryant
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${ROOT}/config/.env"
export NVM_DIR="${NVM_DIR:-${HOME}/.nvm}"
# shellcheck disable=SC1091
[[ -s "${NVM_DIR}/nvm.sh" ]] && source "${NVM_DIR}/nvm.sh"
nvm use 24 >/dev/null 2>&1 || true

[[ -f "${ENV_FILE}" ]] || cp "${ROOT}/config/.env.example" "${ENV_FILE}"
# shellcheck disable=SC1090
source "${ENV_FILE}"

PY="${ROOT}/sqlite-mcp/.venv/bin/python"
DB_PATH="${OPENCLAW_HEALTH_DB_PATH:-${MYWELLWALLET_DB_PATH:-${HOME}/.openclaw-health-assistant/openclaw_health.db}}"

add_or_replace() {
  local name="$1"
  shift
  openclaw mcp remove "${name}" 2>/dev/null || true
  openclaw mcp add "${name}" "$@"
}

add_or_replace openclaw-health-sqlite \
  --command "${PY}" \
  --arg server.py \
  --cwd "${ROOT}/sqlite-mcp" \
  --env "OPENCLAW_HEALTH_DB_PATH=${DB_PATH}"

openclaw mcp remove mywellwallet-sqlite 2>/dev/null || true

openclaw mcp doctor openclaw-health-sqlite --probe

if [[ -n "${FHIR_MCP_API_KEY:-}" ]]; then
  add_or_replace fhir-remote \
    --url "${FHIR_MCP_BASE_URL:-https://mcp-fhir-server.com}/mcp" \
    --transport streamable-http \
    --header "X-API-Key=${FHIR_MCP_API_KEY}" \
    --timeout 120
  openclaw mcp doctor fhir-remote --probe
else
  echo "Set FHIR_MCP_API_KEY in config/.env to register fhir-remote." >&2
fi

openclaw mcp status --verbose
