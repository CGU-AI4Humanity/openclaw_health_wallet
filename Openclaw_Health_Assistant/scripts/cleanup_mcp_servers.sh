#!/usr/bin/env bash
# Wire health MCP only (Brandon Medina typed tools + synthetic demo DB).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export NVM_DIR="${NVM_DIR:-${HOME}/.nvm}"
# shellcheck disable=SC1091
[[ -s "${NVM_DIR}/nvm.sh" ]] && source "${NVM_DIR}/nvm.sh"
nvm use 24 >/dev/null 2>&1 || true

LEGACY_NAMES=(
  mywellwallet-sqlite
  mywellwallet_sqlite
  openclaw_health_sqlite
  openclaw-health-sqlite
)

echo "=== Prune legacy MCP keys ==="
python3 "${ROOT}/scripts/prune_mcp_config.py"

echo "=== openclaw mcp remove (legacy) ==="
for name in "${LEGACY_NAMES[@]}"; do
  openclaw mcp remove "${name}" 2>/dev/null || true
done

python3 "${ROOT}/scripts/prune_mcp_config.py"

echo "=== Wire health MCP ==="
"${ROOT}/scripts/wire_mcp_servers.sh"

python3 "${ROOT}/scripts/prune_mcp_config.py"

echo ""
echo "Expected: health (+ fhir-remote when FHIR_MCP_API_KEY is set)."
openclaw mcp status --verbose 2>/dev/null || true
