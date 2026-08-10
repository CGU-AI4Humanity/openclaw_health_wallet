#!/usr/bin/env bash
# Build synthetic demo DB from demo/csv (Brandon Medina Final_Project fixture)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${ROOT}/config/.env"
if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
fi

DB="${HEALTH_DB_PATH:-${HOME}/.openclaw-health-assistant/final_project.db}"
mkdir -p "$(dirname "${DB}")"

python3 "${ROOT}/demo/seed_database.py" \
  --database "${DB}" \
  --csv-dir "${ROOT}/demo/csv"

echo "Demo database: ${DB}"
sqlite3 "${DB}" "SELECT id, name, date_of_birth FROM users WHERE id='${HEALTH_ACTIVE_USER_ID:-PT0001}';"
"${ROOT}/scripts/sync_demo_patient_from_env.sh" 2>/dev/null || true
