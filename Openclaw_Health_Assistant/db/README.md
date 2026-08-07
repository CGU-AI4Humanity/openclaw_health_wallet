# SQLite database setup & testing

**Lead:** Brandon Medina — MyWellWallet-compatible SQLite setup and validation for OpenClaw Health Assistant.

MCP registration and FHIR remote connection: **Leonard Bryant** ([MCP_CONNECTIONS.md](../docs/MCP_CONNECTIONS.md)). Apple Health bridge and project management: **Mahesh Balan**.

## Schema

- DDL: [../db/schema.sql](../db/schema.sql)
- Documentation: [../db/SQLITE_SCHEMA.md](../db/SQLITE_SCHEMA.md)

## Initialize empty database

```bash
cd Openclaw_Health_Assistant
cp config/.env.example config/.env   # optional: set MYWELLWALLET_DB_PATH
./scripts/init_db.sh
```

Default path: `~/.openclaw-health-assistant/mywellwallet.db`

## Load phone export fixture (testing)

Uses a local MyWellWallet export (PHI — never commit). Default source: `~/myWellWallet/fixtures/test_database_export/mywellwallet_phone.sqlite3`

```bash
./scripts/copy_fixture_db.sh
# or: ./scripts/copy_fixture_db.sh /path/to/mywellwallet.db
```

## SQLite MCP server (Brandon — implementation & tool tests)

```bash
./scripts/setup_sqlite_mcp_venv.sh
```

Smoke test after Leonard registers the server in OpenClaw:

```bash
openclaw mcp doctor mywellwallet-sqlite --probe
```

Implemented tools in [server.py](./server.py): `sqlite_health`, `list_fhir_patients`, `get_fhir_patient_bundle`, `search_fhir_resources`, `execute_read_query`, `upsert_fhir_patient`, `upsert_fhir_resource`, `health_metrics_summary`.

## Validation queries (sqlite3 CLI)

```bash
DB=~/.openclaw-health-assistant/mywellwallet.db
sqlite3 "$DB" "SELECT COUNT(*) FROM fhir_patients;"
sqlite3 "$DB" "SELECT COUNT(*) FROM fhir_resources;"
sqlite3 "$DB" "SELECT COUNT(*) FROM health_steps;"
```

Reference: [Zero_Claw-Retina_Health-Assistant/retina-mcp](../../Zero_Claw-Retina_Health-Assistant/retina-mcp/) (MCP pattern only; SQLite logic is Brandon’s track).
