#!/usr/bin/env bash
# Smoke tests: DB + SQLite MCP tools (Brandon Medina)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DB="${MYWELLWALLET_DB_PATH:-${HOME}/.openclaw-health-assistant/mywellwallet.db}"
export MYWELLWALLET_DB_PATH="${DB}"
export PYTHONPATH="${ROOT}/apple-health-bridge:${ROOT}/sqlite-mcp"

PY="${ROOT}/sqlite-mcp/.venv/bin/python"

echo "=== SQLite counts ==="
sqlite3 "${DB}" "SELECT 'fhir_patients', COUNT(*) FROM fhir_patients UNION ALL SELECT 'fhir_resources', COUNT(*) FROM fhir_resources UNION ALL SELECT 'health_steps', COUNT(*) FROM health_steps;"

echo "=== MCP tool smoke (in-process) ==="
cd "${ROOT}"
"${PY}" - <<'PY'
import json
import sys
sys.path.insert(0, "sqlite-mcp")
sys.path.insert(0, "apple-health-bridge")
import server

print(json.dumps(server.sqlite_health(), indent=2)[:800])
patients = server.list_fhir_patients(limit=5)
print("patients:", len(patients.get("patients", [])))
PY

echo "OK"
