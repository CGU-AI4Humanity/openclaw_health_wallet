# MCP connections (OpenClaw)

**Lead:** Leonard Bryant — MCP server connections for OpenClaw Health Assistant.

SQLite schema and DB testing: **Brandon Medina** ([db/](../db/), [sqlite-mcp/](../sqlite-mcp/)). Apple Health and PM: **Mahesh Balan**.

## Clean registration (recommended)

After `config/.env` is filled:

```bash
export NVM_DIR="$HOME/.nvm" && source "$NVM_DIR/nvm.sh" && nvm use 24
cd Openclaw_Health_Assistant
set -a && source config/.env && set +a
./scripts/cleanup_mcp_servers.sh
```

This script:

1. Removes legacy names (`mywellwallet-sqlite`, etc.) from the OpenClaw CLI **and** stale `mcp.servers.*` keys in `~/.openclaw/openclaw.json`.
2. Re-registers **`openclaw-health-sqlite`** and **`fhir-remote`** via `wire_mcp_servers.sh`.

### Expected `openclaw mcp status --verbose`

| Server | When |
| --- | --- |
| **openclaw-health-sqlite** | Always (local DB) |
| **fhir-remote** | When `FHIR_MCP_API_KEY` is set in `config/.env` |

You should **not** see **`mywellwallet-sqlite`** or two different SQLite MCP servers.

## Local SQLite MCP (stdio)

```bash
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

Prefer **`cleanup_mcp_servers.sh`** instead of manual `mcp add`.

## Remote FHIR MCP (streamable-http)

Hosted API: `https://mcp-fhir-server.com/mcp`, header `X-API-Key`. Project: [github.com/maheshbalan/fhir-mcp-server](https://github.com/maheshbalan/fhir-mcp-server).

```bash
openclaw mcp add fhir-remote \
  --url https://mcp-fhir-server.com/mcp \
  --transport streamable-http \
  --header "X-API-Key=${FHIR_MCP_API_KEY}"

openclaw mcp doctor fhir-remote --probe
```

Store `FHIR_MCP_API_KEY` in `config/.env` (gitignored).

## Verify

```bash
openclaw mcp status --verbose
openclaw mcp doctor openclaw-health-sqlite --probe
openclaw mcp doctor fhir-remote --probe
```

## LLM note (MCP tool calling)

MCP prompts require an Ollama model with **`tools`** capability (default in this repo: **`qwen3:4b`** via `./scripts/configure_qwen_tools.sh`). **`medgemma:4b`** does not accept tool payloads in Ollama.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| Duplicate SQLite MCP | `./scripts/cleanup_mcp_servers.sh` |
| SQLite MCP: DB not found | `OPENCLAW_HEALTH_DB_PATH` in `.env` matches initialized file |
| FHIR MCP: 401 | Valid `FHIR_MCP_API_KEY`; re-run cleanup script |
| Tools missing in chat | `openclaw chat` + Qwen default model; not MedGemma |

See also [SETUP.md](./SETUP.md) and [README.md](../README.md).
