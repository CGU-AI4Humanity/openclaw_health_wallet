#!/usr/bin/env bash
# Smoke tests: demo DB + health MCP tools (Brandon Medina)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${ROOT}/config/.env"
if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
fi

DB="${HEALTH_DB_PATH:-${HOME}/.openclaw-health-assistant/final_project.db}"
export HEALTH_DB_PATH="${DB}"
export HEALTH_ACTIVE_USER_ID="${HEALTH_ACTIVE_USER_ID:-PT0001}"

PY="${ROOT}/health-mcp/.venv/bin/python"

echo "=== Demo DB ==="
sqlite3 "${DB}" "SELECT COUNT(*) AS users FROM users;"
sqlite3 "${DB}" "SELECT COUNT(*) AS lab_rows FROM health_lab_results WHERE user_id='${HEALTH_ACTIVE_USER_ID}';"

echo "=== Health MCP tool smoke (in-process) ==="
cd "${ROOT}/health-mcp"
"${PY}" - <<'PY'
import json
import os
import sys

sys.path.insert(0, os.getcwd())
import config  # noqa: E402
from tools import patients, vitals, labs  # noqa: E402

print("db:", config.DB_PATH)
print(json.dumps(patients.get_patient().model_dump(), indent=2))
print(json.dumps(vitals.get_latest_blood_pressure().model_dump(), indent=2))
print("lab tests:", labs.list_lab_tests().model_dump()["tests"][:5])
PY

echo "OK"
