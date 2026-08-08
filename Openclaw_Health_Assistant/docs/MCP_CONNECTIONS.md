# MCP connections (OpenClaw)

**Lead:** Leonard Bryant — MCP server connections for OpenClaw Health Assistant.

This document covers wiring **local** and **remote** MCP servers into OpenClaw. SQLite schema and DB testing are owned by **Brandon Medina** ([db/](../db/), [sqlite-mcp/](../sqlite-mcp/)). Apple Health and overall project management: **Mahesh Balan**.

## Local SQLite MCP (stdio)

After Brandon’s DB is initialized (`../scripts/init_db.sh`):

```bash
# Node 24+ required for OpenClaw CLI
export NVM_DIR="$HOME/.nvm" && source "$NVM_DIR/nvm.sh" && nvm use 24

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${ROOT}/sqlite-mcp/.venv/bin/python"
DB_PATH="${OPENCLAW_HEALTH_DB_PATH:-$HOME/.openclaw-health-assistant/openclaw_health.db}"

openclaw mcp add openclaw-health-sqlite \
  --command "${PY}" \
  --arg server.py \
  --cwd "${ROOT}/sqlite-mcp" \
  --env "OPENCLAW_HEALTH_DB_PATH=${DB_PATH}"

openclaw mcp doctor openclaw-health-sqlite --probe
```

Or run **`../scripts/wire_mcp_servers.sh`**, which registers both SQLite and FHIR MCP using `config/.env`.

Optional HTTP transport for debugging:

```bash
cd sqlite-mcp
MCP_TRANSPORT=streamable-http OPENCLAW_HEALTH_DB_PATH="${DB_PATH}" .venv/bin/python server.py
# curl probe on port 8010 — see Zero_Claw retina-mcp examples
```

## Remote FHIR MCP (streamable-http)

Hosted API: `https://mcp-fhir-server.com/mcp`, header `X-API-Key`. Server project: [github.com/maheshbalan/fhir-mcp-server](https://github.com/maheshbalan/fhir-mcp-server).

```bash
openclaw mcp add fhir-remote \
  --url https://mcp-fhir-server.com/mcp \
  --transport streamable-http \
  --header "X-API-Key=${FHIR_MCP_API_KEY}"

openclaw mcp doctor fhir-remote --probe
```

Store `FHIR_MCP_API_KEY` in `config/.env` (gitignored). Do not commit keys.

## Verify

```bash
openclaw mcp status --verbose
openclaw mcp doctor openclaw-health-sqlite --probe
openclaw mcp doctor fhir-remote --probe
```

After config changes, restart or reload the gateway if tools do not appear (`openclaw mcp reload` or daemon restart per [OpenClaw MCP docs](https://docs.openclaw.ai/tools/mcp)).

## Migration note

Older setups used MCP name **`mywellwallet-sqlite`** and env **`MYWELLWALLET_DB_PATH`**. Re-run **`wire_mcp_servers.sh`** to register **`openclaw-health-sqlite`**. The Python server still accepts **`MYWELLWALLET_DB_PATH`** as a deprecated alias for the database file path.

## Troubleshooting (Leonard’s checklist)

| Symptom | Check |
| --- | --- |
| SQLite MCP: DB not found | `OPENCLAW_HEALTH_DB_PATH` in `--env` matches the initialized file |
| SQLite MCP: probe fails | Run `../scripts/setup_sqlite_mcp_venv.sh`; use venv Python in `--command` |
| FHIR MCP: 401 / no tools | `X-API-Key` header; session initialize flow on server |
| Tools missing in chat | `openclaw mcp doctor --probe`; gateway env `OLLAMA_API_KEY=ollama-local` for model path |

See also [SETUP.md](./SETUP.md) for full stack install.
