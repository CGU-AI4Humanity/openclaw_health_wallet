# Local SQLite MCP (planned)

FastMCP server exposing MyWellWallet-compatible SQLite operations to OpenClaw.

## Planned tools

- `sqlite_health` — verify DB path and schema version
- `list_users` / `get_current_user`
- `list_fhir_patients` / `get_fhir_patient_bundle`
- `search_fhir_resources` — by `patient_id`, `resource_type`
- `execute_read_query` — parameterized SELECT only (no writes via free SQL)
- `upsert_fhir_bundle` — used after remote FHIR fetch (controlled write path)

## Stack

- Python 3.11+
- `mcp[cli]` (FastMCP), same as retina-mcp in Zero_Claw
- Env: `MYWELLWALLET_DB_PATH` from [config/.env.example](../config/.env.example)

## Files to add

```text
sqlite-mcp/
├── requirements.txt
├── server.py
└── README.md
```

Reference: [Zero_Claw-Retina_Health-Assistant/retina-mcp/server.py](../../Zero_Claw-Retina_Health-Assistant/retina-mcp/server.py)
