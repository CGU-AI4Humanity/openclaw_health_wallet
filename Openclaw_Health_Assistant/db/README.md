# SQLite database setup & testing

**Lead:** Brandon Medina — local SQLite schema setup and validation for OpenClaw Health Assistant.

MCP registration and FHIR remote connection: **Leonard Bryant** ([MCP_CONNECTIONS.md](../docs/MCP_CONNECTIONS.md)). Apple Health bridge and project management: **Mahesh Balan**.

## Schema

- DDL: [../db/schema.sql](../db/schema.sql)
- Documentation: [../db/SQLITE_SCHEMA.md](../db/SQLITE_SCHEMA.md)

## Initialize empty database

```bash
cd Openclaw_Health_Assistant
cp config/.env.example config/.env   # optional: set OPENCLAW_HEALTH_DB_PATH
./scripts/init_db.sh
```

Default path: `~/.openclaw-health-assistant/openclaw_health.db`

## Load a test SQLite file (optional)

For engineering validation only — pass an explicit source path (PHI — never commit):

```bash
./scripts/copy_fixture_db.sh /path/to/test.sqlite3
```

Apple Health data for normal use comes from **Health Link** QR pairing, not from copying another app’s database.

## SQLite MCP server (Brandon — implementation & tool tests)

```bash
./scripts/setup_sqlite_mcp_venv.sh
```

Smoke test after Leonard registers the server in OpenClaw:

```bash
openclaw mcp doctor openclaw-health-sqlite --probe
```

Implemented tools in [server.py](../sqlite-mcp/server.py): `sqlite_health`, `list_fhir_patients`, `get_fhir_patient_bundle`, `search_fhir_resources`, `execute_read_query`, `upsert_fhir_patient`, `upsert_fhir_resource`, `health_metrics_summary`, `get_apple_health_sync_status`, `import_apple_health_json`.

## Validation queries (sqlite3 CLI)

```bash
DB=~/.openclaw-health-assistant/openclaw_health.db
sqlite3 "$DB" "SELECT COUNT(*) FROM fhir_patients;"
sqlite3 "$DB" "SELECT COUNT(*) FROM fhir_resources;"
sqlite3 "$DB" "SELECT COUNT(*) FROM health_steps;"
```

Reference: [Zero_Claw-Retina_Health-Assistant/retina-mcp](../../Zero_Claw-Retina_Health-Assistant/retina-mcp/) (MCP pattern only; SQLite logic is Brandon’s track).
