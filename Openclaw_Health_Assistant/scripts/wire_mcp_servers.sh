#!/usr/bin/env bash
# Register Brandon health MCP (stdio) — replaces generic SQLite + remote FHIR for demo stack.
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

python3 "${ROOT}/scripts/prune_mcp_config.py" 2>/dev/null || true

PY="${ROOT}/health-mcp/.venv/bin/python"
if [[ ! -x "${PY}" ]]; then
  echo "Run ./scripts/setup_health_mcp_venv.sh first." >&2
  exit 1
fi

DB_PATH="${HEALTH_DB_PATH:-${HOME}/.openclaw-health-assistant/final_project.db}"
ACTIVE="${HEALTH_ACTIVE_USER_ID:-PT0001}"

LEGACY=(
  mywellwallet-sqlite
  mywellwallet_sqlite
  openclaw_health_sqlite
  openclaw-health-sqlite
  health-mcp
)

add_or_replace() {
  local name="$1"
  shift
  openclaw mcp remove "${name}" 2>/dev/null || true
  openclaw mcp add "${name}" "$@"
}

for legacy in "${LEGACY[@]}"; do
  openclaw mcp remove "${legacy}" 2>/dev/null || true
done

add_or_replace health \
  --command "${PY}" \
  --arg server.py \
  --cwd "${ROOT}/health-mcp" \
  --env "HEALTH_DB_PATH=${DB_PATH}" \
  --env "HEALTH_ACTIVE_USER_ID=${ACTIVE}"

openclaw mcp doctor health --probe

if [[ -n "${FHIR_MCP_API_KEY:-}" ]]; then
  add_or_replace fhir-remote \
    --url "${FHIR_MCP_BASE_URL:-https://mcp-fhir-server.com}/mcp" \
    --transport streamable-http \
    --header "X-API-Key=${FHIR_MCP_API_KEY}" \
    --timeout 300
  openclaw mcp doctor fhir-remote --probe
  echo "FHIR MCP registered for demo connectivity (chat still uses health__* tools only)."
else
  echo "Tip: set FHIR_MCP_API_KEY in config/.env to register fhir-remote for demo probes."
fi

python3 "${ROOT}/scripts/prune_mcp_config.py" 2>/dev/null || true

openclaw mcp status --verbose
