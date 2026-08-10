# MCP — health demo stack (Brandon Medina)

Default registration: **`health`** stdio MCP only.

| Variable | Purpose |
|----------|---------|
| `HEALTH_DB_PATH` | Seeded `final_project.db` |
| `HEALTH_ACTIVE_USER_ID` | Single demo patient (default `PT0001`) |

```bash
./scripts/cleanup_mcp_servers.sh
openclaw mcp doctor health --probe
openclaw mcp status --verbose
```

Tool names exposed to OpenClaw: `health__ping`, `health__get_patient`, `health__get_latest_blood_pressure`, … (see [openclaw.health-tools.patch.json5](../config/openclaw.health-tools.patch.json5)).

Legacy **`openclaw-health-sqlite`** + **`fhir-remote`** are removed by cleanup; see git history for remote FHIR flow.
