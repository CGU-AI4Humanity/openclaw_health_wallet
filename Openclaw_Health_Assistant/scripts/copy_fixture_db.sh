#!/usr/bin/env bash
# Copy a SQLite file for local testing (PHI — never commit). Brandon Medina
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${ROOT}/config/.env"
if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
fi

DEST="${OPENCLAW_HEALTH_DB_PATH:-${MYWELLWALLET_DB_PATH:-${HOME}/.openclaw-health-assistant/openclaw_health.db}}"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 /path/to/source.sqlite3" >&2
  echo "Copies a SQLite database to OPENCLAW_HEALTH_DB_PATH (see config/.env.example)." >&2
  exit 1
fi
SOURCE="$1"

if [[ ! -f "${SOURCE}" ]]; then
  echo "Source database not found: ${SOURCE}" >&2
  exit 1
fi

mkdir -p "$(dirname "${DEST}")"
cp "${SOURCE}" "${DEST}"
echo "Copied ${SOURCE} -> ${DEST}"
sqlite3 "${DEST}" "SELECT 'users', COUNT(*) FROM users UNION ALL SELECT 'fhir_patients', COUNT(*) FROM fhir_patients UNION ALL SELECT 'fhir_resources', COUNT(*) FROM fhir_resources;"
