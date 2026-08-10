#!/usr/bin/env bash
# Remove legacy MCP registrations and re-wire: openclaw-health-sqlite + fhir-remote only.
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
)

echo "=== Prune ~/.openclaw/openclaw.json (legacy SQLite MCP keys) ==="
python3 "${ROOT}/scripts/prune_mcp_config.py"

echo "=== openclaw mcp remove (legacy CLI names) ==="
for name in "${LEGACY_NAMES[@]}"; do
  if openclaw mcp remove "${name}" 2>/dev/null; then
    echo "Removed CLI registration: ${name}"
  fi
done

python3 "${ROOT}/scripts/prune_mcp_config.py"

echo "=== Re-wire openclaw-health-sqlite + fhir-remote ==="
"${ROOT}/scripts/wire_mcp_servers.sh"

echo "=== Final prune (wire must not reintroduce mywellwallet-sqlite) ==="
python3 "${ROOT}/scripts/prune_mcp_config.py"

echo ""
echo "Expected: fhir-remote + openclaw-health-sqlite only."
openclaw mcp status --verbose 2>/dev/null || true
