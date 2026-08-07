# Local SQLite MCP

**Lead:** Brandon Medina — MyWellWallet-compatible SQLite MCP server for OpenClaw.

OpenClaw registration and probes: **Leonard Bryant** ([docs/MCP_CONNECTIONS.md](../docs/MCP_CONNECTIONS.md)).

## Tools

- `sqlite_health` — verify DB path and table counts
- `list_users` / `get_current_user`
- `list_fhir_patients` / `get_fhir_patient_bundle`
- `search_fhir_resources` — by `patient_id`, optional `resource_type`
- `execute_read_query` — read-only SELECT / WITH / safe PRAGMA
- `upsert_fhir_patient` / `upsert_fhir_resource` — controlled writes after FHIR fetch
- `health_metrics_summary` — row counts in `health_*` tables

## Stack

- Python 3.11+
- `mcp[cli]` (FastMCP)
- Env: `MYWELLWALLET_DB_PATH` ([config/.env.example](../config/.env.example))

## Setup

```bash
../scripts/setup_sqlite_mcp_venv.sh
../scripts/init_db.sh    # or ../scripts/copy_fixture_db.sh for fixture testing
```

## Files

```text
sqlite-mcp/
├── requirements.txt
├── db.py
├── server.py
└── README.md
```

Reference MCP pattern: [Zero_Claw-Retina_Health-Assistant/retina-mcp](../../Zero_Claw-Retina_Health-Assistant/retina-mcp/server.py)
