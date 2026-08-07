#!/usr/bin/env bash
# Copy phone export fixture for DB testing — Brandon Medina
# Source is NOT committed to openclaw_health_wallet (PHI). Default: sibling myWellWallet fixture.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${ROOT}/config/.env"
if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
fi

DEST="${MYWELLWALLET_DB_PATH:-${HOME}/.openclaw-health-assistant/mywellwallet.db}"
SOURCE="${1:-${HOME}/myWellWallet/fixtures/test_database_export/mywellwallet_phone.sqlite3}"

if [[ ! -f "${SOURCE}" ]]; then
  echo "Source database not found: ${SOURCE}" >&2
  echo "Export from iPhone or pass path: $0 /path/to/mywellwallet.db" >&2
  exit 1
fi

mkdir -p "$(dirname "${DEST}")"
cp "${SOURCE}" "${DEST}"
echo "Copied ${SOURCE} -> ${DEST}"
sqlite3 "${DEST}" "SELECT 'users', COUNT(*) FROM users UNION ALL SELECT 'fhir_patients', COUNT(*) FROM fhir_patients UNION ALL SELECT 'fhir_resources', COUNT(*) FROM fhir_resources;"
