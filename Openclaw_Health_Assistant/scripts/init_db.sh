#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${ROOT}/config/.env"

if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
fi

DB_PATH="${MYWELLWALLET_DB_PATH:-${HOME}/.openclaw-health-assistant/mywellwallet.db}"
mkdir -p "$(dirname "${DB_PATH}")"

if command -v sqlite3 >/dev/null 2>&1; then
  sqlite3 "${DB_PATH}" < "${ROOT}/db/schema.sql"
  echo "Initialized database at ${DB_PATH}"
else
  echo "sqlite3 CLI not found. Install Xcode CLT or: brew install sqlite" >&2
  exit 1
fi
